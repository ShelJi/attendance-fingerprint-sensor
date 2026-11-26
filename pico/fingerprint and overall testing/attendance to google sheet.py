"""
AS608 + Raspberry Pi Pico 2 W
Wi-Fi Attendance System

AS608:
    VCC -> 3V3
    GND -> GND
    TX  -> GP1 (Pico RX)
    RX  -> GP0 (Pico TX)

Flow:
    Fingerprint
        |
        v
    AS608
        |
        v
    Pico 2 W
        |
        | HTTPS POST
        v
    Google Apps Script (script.google.com web app)
        |
        v
    Google Sheet

Your deployed Apps Script must define a doPost(e) function (this
script always sends POST, never GET). Visiting ATTENDANCE_URL
directly in a browser will show "Script function not found: doGet" --
that is expected and harmless; it just means the web app has no GET
handler. It says nothing about whether doPost works.

Default behaviour:
    Boots straight into AUTOMATIC ATTENDANCE MODE.
    Typing anything on the serial console (and pressing Enter) breaks
    out of automatic mode and drops into the interactive menu. Typing
    "q" in the menu returns to automatic mode.
    Ctrl+C is NOT used to switch modes -- it behaves like normal
    CircuitPython Ctrl+C and stops the script, returning you to the
    ">>>" REPL, so your editor's Stop/interrupt button works normally.

Required CircuitPython libraries (copy to /lib):
    adafruit_fingerprint
    adafruit_requests
    adafruit_connection_manager
    adafruit_ntp

Required settings.toml keys:
    CIRCUITPY_WIFI_SSID
    CIRCUITPY_WIFI_PASSWORD
    ATTENDANCE_URL
    DEVICE_ID
    NTP_TZ_OFFSET     (optional, integer hours, default 0)

Optional file on the CIRCUITPY drive:
    /ca_cert.pem      Root CA certificate (PEM) for ATTENDANCE_URL's host.
                       For a Google Apps Script backend this is usually
                       NOT needed -- CircuitPython's built-in cert
                       bundle already trusts Google's roots. Only add
                       this file if uploads fail with:
                           x509-crt-bundle:Failed to verify certificate
                           HTTP upload error: (-12288, 'MBEDTLS_ERR_X509_FATAL_ERROR')
                       See the load_custom_ca() docstring below for how
                       to obtain this file correctly.
"""
import os
import time
import board
import busio
import wifi
import rtc
import supervisor
import adafruit_connection_manager
import adafruit_requests
import adafruit_fingerprint
import adafruit_ntp

# ============================================================
# CONFIGURATION
# ============================================================
UART_BAUDRATE = 57600
WIFI_SSID = os.getenv("CIRCUITPY_WIFI_SSID")
WIFI_PASSWORD = os.getenv("CIRCUITPY_WIFI_PASSWORD")
ATTENDANCE_URL = os.getenv("ATTENDANCE_URL")
DEVICE_ID = os.getenv("DEVICE_ID", "PICO2W-01")
NTP_TZ_OFFSET = int(os.getenv("NTP_TZ_OFFSET", "0"))
CA_CERT_PATH = "/ca_cert.pem"

# Minimum time between two attendance uploads.
# This prevents repeated uploads when a finger remains on the sensor.
ATTENDANCE_COOLDOWN = 5

# Time to wait between Wi-Fi connection attempts.
WIFI_RETRY_DELAY = 5

# Small delay used inside busy-wait polling loops so the CPU isn't
# spinning at 100% while waiting for a finger / finger removal / input.
POLL_DELAY = 0.05

# ============================================================
# VALIDATE SETTINGS
# ============================================================
if not WIFI_SSID:
    raise RuntimeError("CIRCUITPY_WIFI_SSID missing from settings.toml")
if not WIFI_PASSWORD:
    raise RuntimeError("CIRCUITPY_WIFI_PASSWORD missing from settings.toml")
if not ATTENDANCE_URL:
    raise RuntimeError("ATTENDANCE_URL missing from settings.toml")

# ============================================================
# UART / FINGERPRINT SENSOR
# ============================================================
uart = busio.UART(
    board.GP0,
    board.GP1,
    baudrate=UART_BAUDRATE,
    timeout=1,
)

try:
    finger = adafruit_fingerprint.Adafruit_Fingerprint(uart)
except RuntimeError:
    print("ERROR: Could not find fingerprint sensor.")
    print("Check:")
    print("  AS608 VCC -> Pico 3V3")
    print("  AS608 GND -> Pico GND")
    print("  AS608 TX  -> Pico GP1")
    print("  AS608 RX  -> Pico GP0")
    print("  UART baud rate =", UART_BAUDRATE)
    raise

# ============================================================
# WIFI / HTTP
# ============================================================
pool = adafruit_connection_manager.get_radio_socketpool(wifi.radio)
ssl_context = adafruit_connection_manager.get_radio_ssl_context(
    wifi.radio
)


def file_exists(path):
    """
    CircuitPython's ``os`` module doesn't include ``os.path`` (that's
    why 'module' object has no attribute 'path' happened). This is the
    substitute for os.path.exists().
    """
    try:
        with open(path):
            return True
    except OSError:
        return False


def load_custom_ca():
    """
    CircuitPython ships with a compact, hard-coded bundle of root CA
    certificates (to save flash). For most well-known hosts -- and
    script.google.com is about as well-known as it gets -- that
    built-in bundle already has the right root, so /ca_cert.pem is
    usually NOT needed at all for a Google Apps Script backend. Try
    deleting /ca_cert.pem (if you added one) and testing again before
    doing anything below.

    Only add a custom root if the BUILT-IN bundle fails, i.e. you see:

        x509-crt-bundle:Failed to verify certificate
        HTTP upload error: (-12288, 'MBEDTLS_ERR_X509_FATAL_ERROR')

    If instead you see MBEDTLS_ERR_X509_CERT_VERIFY_FAILED (-9984)
    *after* adding /ca_cert.pem, that means the file you loaded does
    not actually match ATTENDANCE_URL's certificate chain -- most
    commonly because the wrong site was open in the browser when it
    was exported (e.g. google.com's certificate instead of the
    specific script.google.com certificate), or because Google's
    rotating intermediate CA was exported instead of the actual root.

    How to get the right one, if you really need it:
      1. Paste ATTENDANCE_URL itself into the address bar and load it.
      2. Click the padlock icon -> "Connection is secure" -> the
         certificate/"i" icon -> "Certificate is valid" (Chrome) or
         View certificate.
      3. Open the "Certification path" / "Details" tab and select the
         TOP-most entry (the root CA, not the leaf/server cert, and
         not an intermediate like "WE2"/"WR2" -- Google rotates those).
      4. Export it as Base-64 encoded X.509 (.CER) -- this is a PEM
         file starting with "-----BEGIN CERTIFICATE-----".
      5. Rename it ca_cert.pem and copy it to the top level of the
         CIRCUITPY drive.
    This function loads it automatically if present. If the file is
    missing, CircuitPython just falls back to its built-in bundle.
    """
    try:
        with open(CA_CERT_PATH, "r") as ca_file:
            cadata = ca_file.read()
        ssl_context.load_verify_locations(cadata=cadata)
        print("Loaded custom root CA from", CA_CERT_PATH)
        return True
    except OSError:
        # File doesn't exist -- use the built-in cert bundle.
        return False
    except Exception as error:
        print("Failed to load custom CA cert:", error)
        return False


load_custom_ca()

requests = adafruit_requests.Session(
    pool,
    ssl_context
)

_time_synced = False


def connect_wifi():
    """Connect Pico 2 W to Wi-Fi."""
    if wifi.radio.connected:
        return True
    print()
    print("Connecting to Wi-Fi...")
    print("SSID:", WIFI_SSID)
    while not wifi.radio.connected:
        try:
            wifi.radio.connect(WIFI_SSID, WIFI_PASSWORD)
            print("Wi-Fi connected.")
            print("IP address:", wifi.radio.ipv4_address)
            if wifi.radio.ap_info:
                print("Signal:", wifi.radio.ap_info.rssi, "dBm")
            return True
        except Exception as error:
            print("Wi-Fi connection failed:", error)
            print("Retrying in", WIFI_RETRY_DELAY, "seconds...")
            time.sleep(WIFI_RETRY_DELAY)
    return True


def sync_time(force=False):
    """
    Sync the Pico's clock over NTP. The Pico 2 W has no battery-backed
    RTC, so it boots with the clock reset to a default. mbedTLS checks
    the server certificate's valid-from/valid-until dates against the
    board's clock during the TLS handshake, so a wrong clock can also
    cause certificate verification failures.
    """
    global _time_synced
    if _time_synced and not force:
        return True
    try:
        ntp = adafruit_ntp.NTP(pool, tz_offset=NTP_TZ_OFFSET)
        rtc.RTC().datetime = ntp.datetime
        print("Time synced:", time.localtime())
        _time_synced = True
        return True
    except Exception as error:
        print("NTP time sync failed:", error)
        return False


# ============================================================
# MENU-SWITCH DETECTION
# ============================================================
class SwitchToMenu(Exception):
    """Raised internally when serial input is detected during
    automatic attendance mode, so the main loop can drop into the
    interactive menu."""
    pass


def menu_requested():
    """True if the user has typed something on the serial console
    that hasn't been read yet."""
    return supervisor.runtime.serial_bytes_available > 0


def sleep_with_menu_check(seconds):
    """Like time.sleep(), but bails out early (raising SwitchToMenu)
    if the user starts typing."""
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        if menu_requested():
            raise SwitchToMenu()
        time.sleep(POLL_DELAY)


# ============================================================
# SEND ATTENDANCE
# ============================================================
def send_attendance(fingerprint_id, confidence):
    """
    Send fingerprint match to Power Automate.
    Power Automate will add the actual date/time to Excel.
    """
    if not wifi.radio.connected:
        connect_wifi()

    payload = {
        "fingerprint_id": fingerprint_id,
        "confidence": confidence,
        "device": DEVICE_ID,
    }

    print()
    print("Uploading attendance...")
    print("Fingerprint ID:", fingerprint_id)
    print("Confidence:", confidence)

    for attempt in (1, 2):
        try:
            with requests.post(
                ATTENDANCE_URL,
                json=payload,
                timeout=15,
            ) as response:
                status = response.status_code
                print("HTTP status:", status)

                if status < 200 or status >= 300:
                    print("Attendance upload failed.")
                    print("Server response:", response.text)
                    return False

                # A Google Apps Script web app almost always answers
                # with HTTP 200 even when it caught an internal error
                # (see the try/except in doPost), or when the request
                # never reached your code at all -- e.g. a Google
                # sign-in page if the deployment isn't public. So a
                # 2xx status alone doesn't mean attendance was actually
                # recorded; the JSON body's "success" field is what
                # doPost() in the Apps Script actually reports.
                try:
                    result = response.json()
                except Exception:
                    print("Server did not return valid JSON. Raw response:")
                    print(response.text)
                    print(
                        "This usually means the request never reached "
                        "doPost() -- check the Apps Script deployment is "
                        "set to 'Execute as: Me' and 'Who has access: "
                        "Anyone', and that ATTENDANCE_URL is the /exec "
                        "URL of the CURRENT deployment (redeploy -- "
                        "'Manage deployments' -> edit -> new version -- "
                        "after every script.google.com code change)."
                    )
                    return False

                if result.get("success"):
                    print("Attendance uploaded:", result.get("message", ""))
                    return True

                print(
                    "Apps Script reported failure:",
                    result.get("message", "unknown error"),
                )
                return False
        except Exception as error:
            print("HTTP upload error:", error)
            is_cert_error = (
                "X509" in str(error)
                or "-12288" in str(error)
                or "-9984" in str(error)
            )
            if attempt == 1 and is_cert_error:
                if not file_exists(CA_CERT_PATH):
                    print(
                        "No /ca_cert.pem found. This can be a clock issue "
                        "-- retrying after an NTP resync..."
                    )
                    sync_time(force=True)
                    continue
                print(
                    "/ca_cert.pem is present but verification still "
                    "failed. This almost always means the exported "
                    "certificate doesn't belong to ATTENDANCE_URL's host "
                    "-- double check you opened ATTENDANCE_URL itself "
                    "(not another site) in the browser before exporting, "
                    "and that you exported the top (root) entry in the "
                    "certificate hierarchy."
                )
            return False
    return False


# ============================================================
# HELPERS
# ============================================================
def wait_for_finger_removal():
    print("Remove finger...")
    while finger.get_image() != adafruit_fingerprint.NOFINGER:
        if menu_requested():
            raise SwitchToMenu()
        time.sleep(POLL_DELAY)
    print("Finger removed.")


# ============================================================
# SEARCH FINGERPRINT (single attempt, used by menu + auto mode)
# ============================================================
def search_fingerprint():
    """
    Wait for a finger, identify it, then upload attendance.
    Raises SwitchToMenu if the user types something while waiting.
    """
    print()
    print("Place finger on sensor...")

    while True:
        if menu_requested():
            raise SwitchToMenu()
        try:
            result = finger.get_image()
        except RuntimeError as error:
            print("Sensor read error:", error)
            time.sleep(POLL_DELAY)
            continue
        if result == adafruit_fingerprint.OK:
            break
        if result == adafruit_fingerprint.NOFINGER:
            time.sleep(POLL_DELAY)
            continue
        print("Fingerprint image error:", result)
        return

    if finger.image_2_tz(1) != adafruit_fingerprint.OK:
        print("Could not process fingerprint image.")
        return

    if finger.finger_fast_search() != adafruit_fingerprint.OK:
        print("No matching fingerprint found.")
        wait_for_finger_removal()
        return

    fingerprint_id = finger.finger_id
    confidence = finger.confidence
    print()
    print("==============================")
    print("Fingerprint MATCH")
    print("ID:", fingerprint_id)
    print("Confidence:", confidence)
    print("==============================")

    success = send_attendance(fingerprint_id, confidence)
    print("ATTENDANCE RECORDED" if success else "ATTENDANCE NOT RECORDED")

    wait_for_finger_removal()
    sleep_with_menu_check(ATTENDANCE_COOLDOWN)


# ============================================================
# ENROLL FINGERPRINT
# ============================================================
def enroll_fingerprint(location):
    """Enroll a new fingerprint into the sensor."""
    print()
    print("Enrolling fingerprint at slot:", location)
    for scan in (1, 2):
        print()
        print("Place finger on sensor...")
        print("Scan", scan, "of 2")
        while finger.get_image() != adafruit_fingerprint.OK:
            time.sleep(POLL_DELAY)
        if finger.image_2_tz(scan) != adafruit_fingerprint.OK:
            print("Could not process fingerprint.")
            print("Enrollment cancelled.")
            return
        if scan == 1:
            print("Remove finger...")
            while finger.get_image() != adafruit_fingerprint.NOFINGER:
                time.sleep(POLL_DELAY)
            time.sleep(1)

    if finger.create_model() != adafruit_fingerprint.OK:
        print("The two scans did not match.")
        print("Enrollment cancelled.")
        return
    if finger.store_model(location) != adafruit_fingerprint.OK:
        print("Could not store fingerprint.")
        print("Enrollment cancelled.")
        return

    print()
    print("Fingerprint enrolled successfully.")
    print("Fingerprint ID:", location)


# ============================================================
# DELETE FINGERPRINT
# ============================================================
def delete_fingerprint(location):
    if finger.delete_model(location) == adafruit_fingerprint.OK:
        print("Deleted fingerprint slot:", location)
    else:
        print("Could not delete fingerprint slot:", location)


# ============================================================
# SHOW STORED FINGERPRINTS
# ============================================================
def show_templates():
    if finger.read_templates() != adafruit_fingerprint.OK:
        print("Could not read fingerprint template list.")
        return
    print()
    print("Stored fingerprint slots:")
    print(finger.templates)


# ============================================================
# SLOT INPUT
# ============================================================
def prompt_slot_number():
    while True:
        try:
            value = int(input("Slot number (1-127): "))
            if 1 <= value <= 127:
                return value
            print("Enter a number from 1 to 127.")
        except ValueError:
            print("Enter a valid number.")


# ============================================================
# TEST WIFI
# ============================================================
def wifi_status():
    if wifi.radio.connected:
        print()
        print("Wi-Fi connected")
        print("IP:", wifi.radio.ipv4_address)
        if wifi.radio.ap_info:
            print("SSID:", wifi.radio.ap_info.ssid)
            print("RSSI:", wifi.radio.ap_info.rssi)
        print("Time synced:", _time_synced)
    else:
        print("Wi-Fi is not connected.")
        
        
def test_https():
    print()
    print("========== HTTPS TEST ==========")
    print("Testing https://script.google.com ...")

    try:
        with requests.get("https://script.google.com") as response:
            print("HTTPS connection successful")
            print("Status:", response.status_code)

    except Exception as error:
        print("HTTPS TEST FAILED")
        print("Error:", error)

    print("================================")

# ============================================================
# SERIAL MENU
# ============================================================
def run_menu():
    print()
    print("====================================")
    print("Interactive menu")
    print("====================================")
    print("  e = enroll fingerprint")
    print("  f = manual fingerprint search")
    print("  d = delete fingerprint")
    print("  s = show fingerprint slots")
    print("  w = Wi-Fi status")
    print("  a = automatic attendance mode")
    print("  q = quit menu (back to automatic mode)")
    print()
    while True:
        choice = input("> ").strip().lower()
        try:
            if choice == "e":
                enroll_fingerprint(prompt_slot_number())
            elif choice == "f":
                search_fingerprint()
            elif choice == "d":
                delete_fingerprint(prompt_slot_number())
            elif choice == "s":
                show_templates()
            elif choice == "w":
                wifi_status()
            elif choice == "a":
                print("Leaving menu.")
                return
            elif choice == "q":
                print("Leaving menu.")
                return
            else:
                print("Unknown option.")
        except SwitchToMenu:
            # Already in the menu -- ignore.
            pass


# ============================================================
# AUTOMATIC ATTENDANCE MODE
# ============================================================
def automatic_attendance_mode():
    print()
    print("====================================")
    print("AUTOMATIC ATTENDANCE MODE")
    print("====================================")
    print("Place finger on the sensor.")
    print("Type any command + Enter to open the menu instead.")
    print()
    while True:
        try:
            search_fingerprint()
            print("Ready for next person.")
            print()
        except SwitchToMenu:
            print()
            print("Input detected, opening menu...")
            return
        except Exception as error:
            print("Attendance loop error:", error)
            time.sleep(1)


# ============================================================
# START
# ============================================================
def main():
    print()
    print("====================================")
    print("AS608 + Pico 2 W Attendance System")
    print("====================================")
    print("Fingerprint sensor connected.")
    connect_wifi()
    sync_time()
    test_https()
    show_templates()
    print()
    print("Booting straight into automatic attendance mode.")
    print("Type any command + Enter at any time to open the menu.")
    while True:
        automatic_attendance_mode()
        run_menu()


main()
