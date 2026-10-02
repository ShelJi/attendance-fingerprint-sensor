import time
import board
import busio
import digitalio
import wifi
import socketpool
import ssl
import adafruit_requests
import adafruit_fingerprint


# ============================================================
# ALL USER CONFIGURATION
# ============================================================

# ---------------- NETWORK ----------------
WIFI_SSID = "iot kids"
WIFI_PASSWORD = "bright kidoos"
BACKEND_URL = "http://10.102.15.236"
DEVICE_ID = "attendance-01"

# ---------------- API URLS ----------------
ATTENDANCE_URL = BACKEND_URL + "/api/attendance/scan/"
STATUS_URL = BACKEND_URL + "/api/device/status/"
COMMAND_URL = (
    BACKEND_URL
    + "/api/device/command/"
)
COMMAND_RESULT_URL = (
    BACKEND_URL
    + "/api/device/command/result/"
)

# ---------------- FINGERPRINT ----------------
UART_BAUDRATE = 57600
FINGERPRINT_MIN_ID = 1
FINGERPRINT_MAX_ID = 127
FINGERPRINT_SCAN_DELAY = 0.05
FINGERPRINT_REMOVAL_DELAY = 0.05
FINGERPRINT_RETRY_DELAY = 2
FINGERPRINT_SECOND_SCAN_DELAY = 0.5

# ---------------- HEARTBEAT ----------------
HEARTBEAT_INTERVAL = 30

# ---------------- COMMAND POLLING ----------------
COMMAND_POLLING_TIMEOUT = 100
COMMAND_POLLING_INTERVAL = 1

# ---------------- ATTENDANCE RESPONSE ----------------
RESPONSE_DISPLAY_TIME = 5
RESPONSE_SCAN_INTERVAL = 0.05

# ---------------- TIMEOUTS ----------------
HTTP_TIMEOUT = 10
FINGER_WAIT_TIMEOUT = 15
FINGER_REMOVAL_TIMEOUT = 5
WIFI_RECONNECT_INTERVAL = 10

# ---------------- SENSOR ----------------
SENSOR_READ_DELAY = 0.05

# ---------------- OLED ----------------
OLED_SPI_BAUDRATE = 4000000
OLED_WIDTH = 128
OLED_HEIGHT = 64

# ---------------- DISPLAY RESET ----------------
DISPLAY_RESET_INTERVAL = 60

# ---------------- STARTUP ----------------
STARTUP_MESSAGE = "SHELJ\nATTENDANCE\nREADY"
WIFI_CONNECT_MESSAGE = "Connecting\nWiFi..."
WIFI_CONNECTED_MESSAGE = "WiFi\nCONNECTED"
WIFI_ERROR_MESSAGE = "WiFi ERROR"
WIFI_RECONNECT_MESSAGE = "WiFi LOST\nRECONNECTING"
FINGERPRINT_ERROR_MESSAGE = "Fingerprint\nERROR"
SYSTEM_ERROR_MESSAGE = "SYSTEM\nERROR"
SENSOR_ERROR_MESSAGE = "SENSOR\nERROR"
READING_MESSAGE = "READING..."
NO_MATCH_MESSAGE = "NO MATCH\nTRY AGAIN"
TRY_AGAIN_MESSAGE = "BAD SCAN\nTRY AGAIN"
SERVER_ERROR_MESSAGE = "SERVER\nERROR"
NETWORK_ERROR_MESSAGE = "NETWORK\nERROR"


# ============================================================
# OLED SSD1309
# ============================================================

class SSD1309:
    WIDTH = OLED_WIDTH
    HEIGHT = OLED_HEIGHT

    FONT = {
        "A": ["01110","10001","10001","11111","10001","10001","10001"],
        "B": ["11110","10001","10001","11110","10001","10001","11110"],
        "C": ["01111","10000","10000","10000","10000","10000","01111"],
        "D": ["11110","10001","10001","10001","10001","10001","11110"],
        "E": ["11111","10000","10000","11110","10000","10000","11111"],
        "F": ["11111","10000","10000","11110","10000","10000","10000"],
        "G": ["01111","10000","10000","10111","10001","10001","01111"],
        "H": ["10001","10001","10001","11111","10001","10001","10001"],
        "I": ["11111","00100","00100","00100","00100","00100","11111"],
        "J": ["00111","00010","00010","00010","10010","10010","01100"],
        "K": ["10001","10010","10100","11000","10100","10010","10001"],
        "L": ["10000","10000","10000","10000","10000","10000","11111"],
        "M": ["10001","11011","10101","10101","10001","10001","10001"],
        "N": ["10001","11001","10101","10011","10001","10001","10001"],
        "O": ["01110","10001","10001","10001","10001","10001","01110"],
        "P": ["11110","10001","10001","11110","10000","10000","10000"],
        "Q": ["01110","10001","10001","10001","10101","10010","01101"],
        "R": ["11110","10001","10001","11110","10100","10010","10001"],
        "S": ["01111","10000","10000","01110","00001","00001","11110"],
        "T": ["11111","00100","00100","00100","00100","00100","00100"],
        "U": ["10001","10001","10001","10001","10001","10001","01110"],
        "V": ["10001","10001","10001","10001","10001","01010","00100"],
        "W": ["10001","10001","10001","10101","10101","11011","10001"],
        "X": ["10001","10001","01010","00100","01010","10001","10001"],
        "Y": ["10001","10001","01010","00100","00100","00100","00100"],
        "Z": ["11111","00001","00010","00100","01000","10000","11111"],
        "0": ["01110","10001","10011","10101","11001","10001","01110"],
        "1": ["00100","01100","00100","00100","00100","00100","01110"],
        "2": ["01110","10001","00001","00010","00100","01000","11111"],
        "3": ["11110","00001","00001","01110","00001","00001","11110"],
        "4": ["00010","00110","01010","10010","11111","00010","00010"],
        "5": ["11111","10000","10000","11110","00001","00001","11110"],
        "6": ["01110","10000","10000","11110","10001","10001","01110"],
        "7": ["11111","00001","00010","00100","01000","01000","01000"],
        "8": ["01110","10001","10001","01110","10001","10001","01110"],
        "9": ["01110","10001","10001","01111","00001","00001","01110"],
        " ": ["00000"] * 7,
        ".": ["00000","00000","00000","00000","00000","00110","00110"],
        "!": ["00100","00100","00100","00100","00100","00000","00100"],
        "?": ["01110","10001","00001","00010","00100","00000","00100"],
        "-": ["00000","00000","00000","11111","00000","00000","00000"],
        ":": ["00000","00110","00110","00000","00110","00110","00000"],
        "/": ["00001","00010","00100","01000","10000","00000","00000"],
        "_": ["00000","00000","00000","00000","00000","00000","11111"],
    }

    def __init__(self, spi, cs, dc, rst):
        self.spi = spi
        self.cs = cs
        self.dc = dc
        self.rst = rst
        self.buffer = bytearray(1024)
        self._init_display()

    def _command(self, value):
        while not self.spi.try_lock():
            pass
        try:
            self.spi.configure(
                baudrate=OLED_SPI_BAUDRATE,
                polarity=0,
                phase=0
            )
            self.dc.value = False
            self.cs.value = False
            self.spi.write(
                bytes([value])
            )
            self.cs.value = True
        finally:
            self.spi.unlock()

    def _data(self, data):
        while not self.spi.try_lock():
            pass
        try:
            self.spi.configure(
                baudrate=OLED_SPI_BAUDRATE,
                polarity=0,
                phase=0
            )
            self.dc.value = True
            self.cs.value = False
            self.spi.write(data)
            self.cs.value = True
        finally:
            self.spi.unlock()

    def _init_display(self):
        self.rst.value = False
        time.sleep(0.1)
        self.rst.value = True
        time.sleep(0.1)
        commands = [
            (0xAE,),
            (0xD5, 0x80),
            (0xA8, 0x3F),
            (0xD3, 0x00),
            (0x40,),
            (0x8D, 0x14),
            (0x20, 0x00),
            (0xA1,),
            (0xC8,),
            (0xDA, 0x12),
            (0x81, 0xCF),
            (0xD9, 0xF1),
            (0xDB, 0x40),
            (0xA4,),
            (0xA6,),
            (0xAF,)
        ]
        for command in commands:
            for value in command:
                self._command(value)

    def clear(self):
        for i in range(1024):
            self.buffer[i] = 0

    def pixel(self, x, y):
        if (
            0 <= x < self.WIDTH
            and
            0 <= y < self.HEIGHT
        ):
            index = (
                x
                +
                (y // 8) * self.WIDTH
            )
            self.buffer[index] |= (
                1 << (y % 8)
            )

    def text(
        self,
        message,
        x=0,
        y=0
    ):
        cursor_x = x
        cursor_y = y
        for character in message:
            if character == "\n":
                cursor_x = x
                cursor_y += 8
                continue
            character = character.upper()
            if character not in self.FONT:
                continue
            if cursor_x + 6 > self.WIDTH:
                cursor_x = x
                cursor_y += 8
            if cursor_y + 7 > self.HEIGHT:
                break
            bitmap = self.FONT[
                character
            ]
            for row in range(7):
                for col in range(5):
                    if bitmap[row][col] == "1":
                        self.pixel(
                            cursor_x + col,
                            cursor_y + row
                        )
            cursor_x += 6

    def show(self):
        self._command(0x21)
        self._command(0x00)
        self._command(0x7F)
        self._command(0x22)
        self._command(0x00)
        self._command(0x07)
        self._data(
            self.buffer
        )


# ============================================================
# OLED SETUP
# ============================================================

spi = busio.SPI(
    clock=board.GP10,
    MOSI=board.GP11
)

cs = digitalio.DigitalInOut(
    board.GP9
)

dc = digitalio.DigitalInOut(
    board.GP8
)

rst = digitalio.DigitalInOut(
    board.GP12
)

cs.direction = (
    digitalio.Direction.OUTPUT
)

dc.direction = (
    digitalio.Direction.OUTPUT
)

rst.direction = (
    digitalio.Direction.OUTPUT
)

cs.value = True

oled = SSD1309(
    spi,
    cs,
    dc,
    rst
)


# ============================================================
# DISPLAY MANAGEMENT
# ============================================================

last_display_update = 0
current_display_is_startup = True


def display(message):
    global last_display_update
    global current_display_is_startup

    print(message)
    oled.clear()
    oled.text(
        str(message)
    )
    oled.show()

    last_display_update = time.monotonic()

    current_display_is_startup = (
        message == STARTUP_MESSAGE
    )


def check_display_reset():
    """Reset display to STARTUP_MESSAGE after
    DISPLAY_RESET_INTERVAL seconds of inactivity."""

    global current_display_is_startup

    if current_display_is_startup:
        return

    now = time.monotonic()

    if (
        now - last_display_update
        >= DISPLAY_RESET_INTERVAL
    ):
        display(STARTUP_MESSAGE)


# ============================================================
# FINGERPRINT SENSOR
# ============================================================

uart = busio.UART(
    board.GP0,
    board.GP1,
    baudrate=UART_BAUDRATE
)

try:
    finger = (
        adafruit_fingerprint
        .Adafruit_Fingerprint(
            uart
        )
    )
    print(
        "Fingerprint sensor OK"
    )
except RuntimeError:
    display(
        FINGERPRINT_ERROR_MESSAGE
    )
    raise


# ============================================================
# WIFI
# ============================================================

def connect_wifi():
    display(WIFI_CONNECT_MESSAGE)
    try:
        if wifi.radio.connected:
            print("WiFi already connected")
            display(WIFI_CONNECTED_MESSAGE)
            time.sleep(1)
            return True

        wifi.radio.connect(
            WIFI_SSID,
            WIFI_PASSWORD
        )

        print("WiFi connected")
        print(
            "IP:",
            wifi.radio.ipv4_address
        )

        display(WIFI_CONNECTED_MESSAGE)
        time.sleep(1)

        return True

    except Exception as e:
        print("WiFi error:", e)
        display(WIFI_ERROR_MESSAGE)
        time.sleep(2)
        display(STARTUP_MESSAGE)
        return False


while not connect_wifi():
    time.sleep(WIFI_RECONNECT_INTERVAL)


# ============================================================
# HTTP WITH SSL SUPPORT
# ============================================================

pool = socketpool.SocketPool(
    wifi.radio
)

ssl_context = ssl.create_default_context()

requests = (
    adafruit_requests.Session(
        pool,
        ssl_context
    )
)


# ============================================================
# TIMERS
# ============================================================

last_heartbeat = 0
last_wifi_retry = 0


# ============================================================
# WIFI RECONNECTION
# ============================================================

def ensure_wifi():
    """Check WiFi and reconnect if needed.
    Returns True if connected."""

    global last_wifi_retry

    if wifi.radio.connected:
        return True

    now = time.monotonic()

    if (
        now - last_wifi_retry
        < WIFI_RECONNECT_INTERVAL
    ):
        return False

    last_wifi_retry = now

    display(WIFI_RECONNECT_MESSAGE)

    try:
        wifi.radio.connect(
            WIFI_SSID,
            WIFI_PASSWORD
        )

        print("WiFi reconnected")
        display(WIFI_CONNECTED_MESSAGE)
        time.sleep(1)
        display(STARTUP_MESSAGE)

        return True

    except Exception as e:
        print("WiFi reconnect error:", e)
        display(WIFI_ERROR_MESSAGE)
        time.sleep(2)
        display(STARTUP_MESSAGE)
        return False


# ============================================================
# DEVICE STATUS
# ============================================================

def send_device_status():
    if not wifi.radio.connected:
        return False

    data = {
        "device_id": DEVICE_ID
    }

    try:
        response = requests.post(
            STATUS_URL,
            json=data,
            timeout=HTTP_TIMEOUT
        )

        print(
            "Device status:",
            response.status_code
        )

        response.close()
        return True

    except Exception as e:
        print(
            "Device status error:",
            e
        )
        return False


def heartbeat():
    global last_heartbeat

    now = time.monotonic()

    if not ensure_wifi():
        return

    if now - last_heartbeat >= HEARTBEAT_INTERVAL:
        send_device_status()
        last_heartbeat = now


# ============================================================
# COMMAND API
# ============================================================

def check_command():
    url = (
        COMMAND_URL
        + "?device_id="
        + DEVICE_ID
    )

    try:
        response = requests.get(
            url,
            timeout=HTTP_TIMEOUT
        )

        if response.status_code != 200:
            print(
                "Command HTTP error:",
                response.status_code
            )
            response.close()
            return None

        data = response.json()
        response.close()
        return data

    except Exception as e:
        print(
            "Command error:",
            e
        )
        return None


def send_command_result(
    command_id,
    success,
    result
):
    data = {
        "device_id": DEVICE_ID,
        "command_id": command_id,
        "success": success,
        "result": result
    }

    try:
        response = requests.post(
            COMMAND_RESULT_URL,
            json=data,
            timeout=HTTP_TIMEOUT
        )

        print(
            "Command result:",
            response.status_code
        )

        response.close()
        return True

    except Exception as e:
        print(
            "Command result error:",
            e
        )
        return False


# ============================================================
# FINGERPRINT DATABASE
# ============================================================

def list_fingerprint_ids():
    ids = []
    for fingerprint_id in range(
        FINGERPRINT_MIN_ID,
        FINGERPRINT_MAX_ID + 1
    ):
        try:
            result = finger.load_model(
                fingerprint_id
            )
            if (
                result
                == adafruit_fingerprint.OK
            ):
                ids.append(
                    fingerprint_id
                )
        except Exception as e:
            print(
                "ID check error:",
                fingerprint_id,
                e
            )
    return ids


def find_available_fingerprint_id():
    for fingerprint_id in range(
        FINGERPRINT_MIN_ID,
        FINGERPRINT_MAX_ID + 1
    ):
        try:
            result = finger.load_model(
                fingerprint_id
            )
            if (
                result
                != adafruit_fingerprint.OK
            ):
                return fingerprint_id
        except Exception:
            return fingerprint_id
    return None


# ============================================================
# FINGERPRINT HELPERS
# ============================================================

def wait_for_finger():
    start_time = time.monotonic()

    while True:
        result = finger.get_image()

        if result == adafruit_fingerprint.OK:
            return True

        if result != adafruit_fingerprint.NOFINGER:
            print("Fingerprint sensor error:", result)
            display(SENSOR_ERROR_MESSAGE)
            return False

        if time.monotonic() - start_time >= FINGER_WAIT_TIMEOUT:
            print("Fingerprint wait timeout")
            display("TIMEOUT\nTRY AGAIN")
            return False

        heartbeat()

        time.sleep(
            FINGERPRINT_SCAN_DELAY
        )


def wait_for_finger_removal():
    start_time = time.monotonic()

    while True:
        result = finger.get_image()

        if result == adafruit_fingerprint.NOFINGER:
            return True

        if result != adafruit_fingerprint.OK:
            print("Fingerprint removal sensor error:", result)
            return False

        if time.monotonic() - start_time >= FINGER_REMOVAL_TIMEOUT:
            print("Fingerprint removal timeout")
            return False

        heartbeat()
        command_polling()

        time.sleep(
            FINGERPRINT_REMOVAL_DELAY
        )


# ============================================================
# ENROLL
# ============================================================

def enroll_fingerprint(
    fingerprint_id
):
    print(
        "Starting enrollment:",
        fingerprint_id
    )

    display(
        "ENROLL ID "
        + str(fingerprint_id)
        + "\nPLACE FINGER"
    )

    if not wait_for_finger():
        display("ENROLL\nFAILED")
        return (
            False,
            "Fingerprint sensor error"
        )

    if (
        finger.image_2_tz(1)
        != adafruit_fingerprint.OK
    ):
        display("BAD READ\nTRY AGAIN")
        return (
            False,
            "Failed to read fingerprint"
        )

    display(
        "REMOVE\nFINGER"
    )

    wait_for_finger_removal()

    time.sleep(
        FINGERPRINT_SECOND_SCAN_DELAY
    )

    display(
        "PLACE AGAIN"
    )

    if not wait_for_finger():
        display("ENROLL\nFAILED")
        return (
            False,
            "Fingerprint sensor error"
        )

    if (
        finger.image_2_tz(2)
        != adafruit_fingerprint.OK
    ):
        display("BAD READ\nTRY AGAIN")
        return (
            False,
            "Failed to read second fingerprint"
        )

    if (
        finger.create_model()
        != adafruit_fingerprint.OK
    ):
        display("NO MATCH\nTRY AGAIN")
        return (
            False,
            "Fingerprints did not match"
        )

    if (
        finger.store_model(
            fingerprint_id
        )
        != adafruit_fingerprint.OK
    ):
        display("STORE\nFAILED")
        return (
            False,
            "Failed to store fingerprint"
        )

    display(
        "ENROLLED\nID "
        + str(fingerprint_id)
    )

    return (
        True,
        {
            "fingerprint_id":
                fingerprint_id,
            "message":
                "Fingerprint enrolled successfully"
        }
    )


def enroll_auto():
    display("FINDING\nFREE ID")

    fingerprint_id = (
        find_available_fingerprint_id()
    )

    if fingerprint_id is None:
        display("DATABASE\nFULL")
        return (
            False,
            "Fingerprint database is full"
        )

    return enroll_fingerprint(
        fingerprint_id
    )


# ============================================================
# DELETE
# ============================================================

def delete_fingerprint(
    fingerprint_id
):
    print(
        "Deleting fingerprint:",
        fingerprint_id
    )

    display(
        "DELETING\nID "
        + str(fingerprint_id)
    )

    result = finger.delete_model(
        fingerprint_id
    )

    if (
        result
        != adafruit_fingerprint.OK
    ):
        display(
            "DELETE\nFAILED"
        )
        return (
            False,
            {
                "fingerprint_id":
                    fingerprint_id,
                "message":
                    "Failed to delete fingerprint"
            }
        )

    display(
        "DELETED\nID "
        + str(fingerprint_id)
    )

    return (
        True,
        {
            "fingerprint_id":
                fingerprint_id,
            "message":
                "Fingerprint deleted successfully"
        }
    )


# ============================================================
# REPLACE
# ============================================================

def replace_fingerprint(
    fingerprint_id
):
    print(
        "Replacing fingerprint:",
        fingerprint_id
    )

    display(
        "REPLACING\nID "
        + str(fingerprint_id)
    )

    result = finger.delete_model(
        fingerprint_id
    )

    if (
        result
        != adafruit_fingerprint.OK
    ):
        display(
            "DELETE OLD\nFAILED"
        )
        return (
            False,
            {
                "fingerprint_id":
                    fingerprint_id,
                "message":
                    "Existing fingerprint could not be deleted"
            }
        )

    return enroll_fingerprint(
        fingerprint_id
    )


# ============================================================
# VERIFY
# ============================================================

def verify_fingerprint():
    display(
        "VERIFY\nPLACE FINGER"
    )

    if not wait_for_finger():
        display("VERIFY\nFAILED")
        return (
            False,
            "Sensor error"
        )

    if (
        finger.image_2_tz(1)
        != adafruit_fingerprint.OK
    ):
        display("BAD READ\nTRY AGAIN")
        return (
            False,
            "Could not read fingerprint"
        )

    if (
        finger.finger_fast_search()
        != adafruit_fingerprint.OK
    ):
        display(
            NO_MATCH_MESSAGE
        )

        wait_for_finger_removal()

        return (
            False,
            {
                "message":
                    "Fingerprint not found"
            }
        )

    fingerprint_id = (
        finger.finger_id
    )

    confidence = (
        finger.confidence
    )

    display(
        "VERIFIED\nID "
        + str(fingerprint_id)
    )

    wait_for_finger_removal()

    return (
        True,
        {
            "fingerprint_id":
                fingerprint_id,
            "confidence":
                confidence,
            "message":
                "Fingerprint verified"
        }
    )


# ============================================================
# SUMMARY
# ============================================================

def fingerprint_summary():
    display("READING\nDATABASE")

    ids = list_fingerprint_ids()

    total = len(ids)
    available = FINGERPRINT_MAX_ID - total

    display(
        "TOTAL " + str(total)
        + "\nFREE " + str(available)
    )

    return (
        True,
        {
            "total": total,
            "capacity":
                FINGERPRINT_MAX_ID,
            "available": available,
            "ids": ids
        }
    )


# ============================================================
# SENSOR INFORMATION
# ============================================================

def fingerprint_info():
    display("READING\nSENSOR")

    try:
        result = (
            finger.read_sysparam()
        )

        if (
            result
            != adafruit_fingerprint.OK
        ):
            display("SENSOR\nREAD FAIL")
            return (
                False,
                {
                    "message":
                        "Unable to read sensor information"
                }
            )

        display(
            "SENSOR OK\n"
            + "CAP "
            + str(finger.capacity)
        )

        return (
            True,
            {
                "capacity":
                    finger.capacity,
                "security_level":
                    finger.security_level,
                "device_address":
                    finger.device_address,
                "packet_len":
                    finger.packet_len,
                "baudrate":
                    finger.baudrate
            }
        )

    except Exception as e:
        display("SENSOR\nERROR")
        return (
            False,
            {
                "message": str(e)
            }
        )


# ============================================================
# COMMAND EXECUTION
# ============================================================

def execute_command(
    command
):
    command_id = command["id"]
    command_type = command["type"]
    fingerprint_id = command.get(
        "fingerprint_id"
    )

    print(
        "Executing:",
        command_type,
        "ID:",
        command_id
    )

    display(
        "CMD\n" + command_type
    )

    try:
        if command_type == "LIST_IDS":
            display(
                "READING\nIDS"
            )

            ids = (
                list_fingerprint_ids()
            )

            total = len(ids)

            display(
                "FOUND\n"
                + str(total)
                + " IDS"
            )

            success = True
            result = {
                "ids": ids,
                "total": total,
                "message":
                    "Fingerprint IDs loaded"
            }

        elif command_type == "ENROLL":
            success, result = (
                enroll_fingerprint(
                    fingerprint_id
                )
            )

        elif command_type == "ENROLL_AUTO":
            success, result = (
                enroll_auto()
            )

        elif command_type == "DELETE":
            success, result = (
                delete_fingerprint(
                    fingerprint_id
                )
            )

        elif command_type == "REPLACE":
            success, result = (
                replace_fingerprint(
                    fingerprint_id
                )
            )

        elif command_type == "VERIFY":
            success, result = (
                verify_fingerprint()
            )

        elif command_type == "SUMMARY":
            success, result = (
                fingerprint_summary()
            )

        elif command_type == "INFO":
            success, result = (
                fingerprint_info()
            )

        else:
            display("UNKNOWN\nCOMMAND")
            success = False
            result = {
                "message":
                    "Unknown command"
            }

        send_command_result(
            command_id,
            success,
            result
        )

        if success:
            display("CMD DONE\nSUCCESS")
        else:
            display("CMD DONE\nFAILED")

        return True

    except Exception as e:
        print(
            "Command execution error:",
            e
        )

        display("CMD\nERROR")

        send_command_result(
            command_id,
            False,
            {
                "message":
                    str(e)
            }
        )

        return False


# ============================================================
# ATTENDANCE
# ============================================================

def send_attendance(
    fingerprint_id
):
    if not ensure_wifi():
        display(NETWORK_ERROR_MESSAGE)
        return None, None

    data = {
        "fingerprint_id":
            str(fingerprint_id),
        "device_id":
            DEVICE_ID
    }

    try:
        print(
            "Sending attendance:",
            data
        )

        response = requests.post(
            ATTENDANCE_URL,
            json=data,
            timeout=HTTP_TIMEOUT
        )

        status_code = (
            response.status_code
        )

        print(
            "Attendance status:",
            status_code
        )

        try:
            result = response.json()
        except Exception:
            result = {}

        print(
            "Response:",
            result
        )

        response.close()

        return (
            status_code,
            result
        )

    except Exception as e:
        print(
            "Attendance error:",
            e
        )

        display(NETWORK_ERROR_MESSAGE)

        return (
            None,
            None
        )


# ============================================================
# RESPONSE MESSAGE
# ============================================================

def get_response_message(
    status_code,
    result
):
    if status_code is None:
        return NETWORK_ERROR_MESSAGE

    if isinstance(
        result,
        dict
    ):
        # Check for message field
        message = result.get(
            "message"
        )

        if message:
            return str(
                message
            )

        # Check for action field
        action = result.get("action")
        employee = result.get("employee", "")

        if action == "login":
            if employee:
                return (
                    str(employee)
                    + "\nLOGIN OK"
                )
            return "LOGIN\nRECORDED"

        if action == "logout":
            if employee:
                return (
                    str(employee)
                    + "\nLOGOUT OK"
                )
            return "LOGOUT\nRECORDED"

        # Check for error field
        if result.get(
            "success"
        ) is False:
            error = result.get(
                "error"
            )
            if error:
                return str(
                    error
                )

    if status_code in (
        200,
        201
    ):
        return (
            "ATTENDANCE\n"
            "RECORDED"
        )

    if status_code == 400:
        return (
            "INVALID\n"
            "REQUEST"
        )

    if status_code == 404:
        return (
            "USER NOT\n"
            "FOUND"
        )

    if status_code == 409:
        return (
            "ALREADY\n"
            "LOGGED IN"
        )

    return (
        "SERVER\n"
        "ERROR"
    )


# ============================================================
# ATTENDANCE SCAN
# ============================================================

def process_fingerprint():
    display(
        READING_MESSAGE
    )

    if (
        finger.image_2_tz(1)
        != adafruit_fingerprint.OK
    ):
        display(
            TRY_AGAIN_MESSAGE
        )
        time.sleep(
            FINGERPRINT_RETRY_DELAY
        )
        return

    if (
        finger.finger_fast_search()
        != adafruit_fingerprint.OK
    ):
        display(
            NO_MATCH_MESSAGE
        )
        time.sleep(
            FINGERPRINT_RETRY_DELAY
        )
        wait_for_finger_removal()
        return

    fingerprint_id = (
        finger.finger_id
    )

    confidence = (
        finger.confidence
    )

    print(
        "Fingerprint:",
        fingerprint_id
    )

    print(
        "Confidence:",
        confidence
    )

    display(
        "ID " + str(fingerprint_id)
        + "\nSENDING..."
    )

    status_code, result = (
        send_attendance(
            fingerprint_id
        )
    )

    message = (
        get_response_message(
            status_code,
            result
        )
    )

    display(
        message
    )

    response_start = time.monotonic()

    while time.monotonic() - response_start < RESPONSE_DISPLAY_TIME:
        heartbeat()
        command_polling()
        time.sleep(
            RESPONSE_SCAN_INTERVAL
        )


# ============================================================
# STARTUP
# ============================================================

print(
    "--------------------------------"
)
print(
    "Attendance Device"
)
print(
    "--------------------------------"
)
print(
    "Device ID:",
    DEVICE_ID
)
print(
    "IP:",
    wifi.radio.ipv4_address
)
print(
    "Backend:",
    BACKEND_URL
)
print(
    "SSL: Enabled"
)
print(
    "--------------------------------"
)

send_device_status()

last_heartbeat = time.monotonic()
last_wifi_retry = time.monotonic()

display(
    STARTUP_MESSAGE
)


# ============================================================
# COMMAND POLLING SESSION
# ============================================================

command_polling_active = False
command_polling_start = 0
last_command_poll = 0


def start_command_polling():
    global command_polling_active
    global command_polling_start
    global last_command_poll

    command_polling_active = True
    command_polling_start = time.monotonic()

    # First poll happens immediately
    last_command_poll = 0

    print(
        "Command polling STARTED for",
        COMMAND_POLLING_TIMEOUT,
        "seconds"
    )


def stop_command_polling():
    global command_polling_active

    if command_polling_active:
        command_polling_active = False
        print("Command polling EXPIRED")


def command_polling():
    global last_command_poll

    if not command_polling_active:
        return

    now = time.monotonic()

    # --------------------------------------------------------
    # Timeout
    # --------------------------------------------------------

    if (
        now - command_polling_start
        >= COMMAND_POLLING_TIMEOUT
    ):
        stop_command_polling()
        return

    # --------------------------------------------------------
    # Poll interval
    # --------------------------------------------------------

    if (
        last_command_poll != 0
        and now - last_command_poll
        < COMMAND_POLLING_INTERVAL
    ):
        return

    last_command_poll = now

    command_data = check_command()

    if command_data is None:
        return

    command = command_data.get("command")

    if command is not None:
        execute_command(command)

        # Command execution may take time.
        # Do not restart the polling timer.
        display(STARTUP_MESSAGE)


# ============================================================
# MAIN LOOP
# ============================================================

while True:
    try:
        heartbeat()

        # Display auto-reset to startup
        check_display_reset()

        # ----------------------------------------------------
        # Finger detection
        # ----------------------------------------------------

        result = finger.get_image()

        if result == adafruit_fingerprint.OK:

            # A real fingerprint image was captured.
            # Start/restart the command polling session.
            start_command_polling()

            process_fingerprint()

            wait_for_finger_removal()

            display(STARTUP_MESSAGE)

            continue

        # ----------------------------------------------------
        # Fingerprint sensor error
        # ----------------------------------------------------

        elif result != adafruit_fingerprint.NOFINGER:

            print(
                "Fingerprint sensor error:",
                result
            )

            display(
                SENSOR_ERROR_MESSAGE
            )

            time.sleep(
                FINGERPRINT_RETRY_DELAY
            )

            continue

        # ----------------------------------------------------
        # Command polling
        # ----------------------------------------------------

        command_polling()

        time.sleep(
            SENSOR_READ_DELAY
        )

    except Exception as e:

        print(
            "Main loop error:",
            e
        )

        display(
            SYSTEM_ERROR_MESSAGE
        )

        time.sleep(
            FINGERPRINT_RETRY_DELAY
        )

        display(
            STARTUP_MESSAGE
        )
