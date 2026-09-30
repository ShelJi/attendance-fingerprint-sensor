"""Production Pico 2 W attendance firmware — Wi-Fi + MQTT + AS608 sensor.

Connects to Wi-Fi, syncs real time over NTP, connects to the backend's MQTT
broker, and publishes an attendance-scan event every time a known finger is
detected, plus a periodic heartbeat. This device never decides login vs.
logout — it only reports "fingerprint slot N was scanned"; the Django MQTT
consumer (backend/mqtt/handlers.py -> apps.attendance.services.
record_fingerprint_scan()) resolves that from the employee's attendance
state for the day. See context/architecture.md's "IoT Fingerprint System".

Setup
-----
1. Flash CircuitPython, as in pico/code.py.
2. Install the official libraries via circup:
       circup install adafruit_fingerprint adafruit_minimqtt adafruit_ntp
3. Copy pico/settings.toml.example to CIRCUITPY/settings.toml and fill in
   your real Wi-Fi SSID/password, MQTT broker host/port, and device ID.
4. Register that same device ID as a Device via the /devices admin page —
   events from an unregistered device are rejected by the backend.
5. Associate each employee's fingerprint slot number (enrolled via
   pico/code.py) to their profile using the admin's "Update Fingerprint"
   action.
6. Copy this file to CIRCUITPY/code.py (replacing pico/code.py's test menu —
   that file is still useful standalone at a desk for enrolling fingers).

Wiring (AS608 -> Pico 2 W)
---------------------------
    VCC -> 3V3(OUT)
    GND -> GND
    TX  -> GP1 (UART0 RX)
    RX  -> GP0 (UART0 TX)
"""

import json
import os
import time

import board
import busio
import rtc
import socketpool
import wifi

import adafruit_fingerprint
import adafruit_ntp
import adafruit_minimqtt.adafruit_minimqtt as MQTT

UART_BAUDRATE = 57600
HEARTBEAT_INTERVAL_SECONDS = 60

WIFI_SSID = os.getenv("WIFI_SSID")
WIFI_PASSWORD = os.getenv("WIFI_PASSWORD")
MQTT_BROKER_HOST = os.getenv("MQTT_BROKER_HOST")
MQTT_BROKER_PORT = int(os.getenv("MQTT_BROKER_PORT", "1883"))
MQTT_USERNAME = os.getenv("MQTT_USERNAME") or None
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD") or None
DEVICE_ID = os.getenv("DEVICE_ID")

if not WIFI_SSID or not WIFI_PASSWORD or not MQTT_BROKER_HOST or not DEVICE_ID:
    raise RuntimeError(
        "Missing settings.toml values — copy settings.toml.example to "
        "CIRCUITPY/settings.toml and fill in WIFI_SSID, WIFI_PASSWORD, "
        "MQTT_BROKER_HOST, and DEVICE_ID."
    )

# Matches backend/mqtt/topics.py exactly — devices never publish to
# arbitrary topics (code-standards.md's "MQTT Topics").
ATTENDANCE_TOPIC = "professional-admin/devices/{}/attendance".format(DEVICE_ID)
HEARTBEAT_TOPIC = "professional-admin/devices/{}/heartbeat".format(DEVICE_ID)


def connect_wifi():
    print("Connecting to Wi-Fi '{}'...".format(WIFI_SSID))
    while not wifi.radio.connected:
        try:
            wifi.radio.connect(WIFI_SSID, WIFI_PASSWORD)
        except ConnectionError as error:
            print("Wi-Fi connect failed: {}, retrying in 5s".format(error))
            time.sleep(5)
    print("Wi-Fi connected, IP: {}".format(wifi.radio.ipv4_address))


def sync_time(pool):
    ntp = adafruit_ntp.NTP(pool, tz_offset=0)
    rtc.RTC().datetime = ntp.datetime
    print("Time synced:", current_timestamp())


def current_timestamp():
    """UTC timestamp in the exact ISO 8601 shape the backend expects
    (architecture.md's "MQTT Event Contract")."""
    t = time.localtime()
    return "{:04d}-{:02d}-{:02d}T{:02d}:{:02d}:{:02d}Z".format(
        t.tm_year, t.tm_mon, t.tm_mday, t.tm_hour, t.tm_min, t.tm_sec
    )


def new_event_id():
    """Unique per scan so a redelivered/retried publish is a safe no-op at
    the backend (architecture.md's "Idempotency")."""
    return "{}-{}-{}".format(DEVICE_ID, int(time.time()), os.urandom(4).hex())


def connect_mqtt(pool):
    client = MQTT.MQTT(
        broker=MQTT_BROKER_HOST,
        port=MQTT_BROKER_PORT,
        username=MQTT_USERNAME,
        password=MQTT_PASSWORD,
        client_id=DEVICE_ID,
        socket_pool=pool,
        is_ssl=False,
    )
    while True:
        try:
            print(
                "Connecting to MQTT broker {}:{}...".format(
                    MQTT_BROKER_HOST, MQTT_BROKER_PORT
                )
            )
            client.connect()
            print("MQTT connected")
            return client
        except (OSError, RuntimeError) as error:
            print("MQTT connect failed: {}, retrying in 5s".format(error))
            time.sleep(5)


def publish_scan(client, fingerprint_id):
    payload = json.dumps(
        {
            "event_id": new_event_id(),
            "device_id": DEVICE_ID,
            "fingerprint_id": str(fingerprint_id),
            "timestamp": current_timestamp(),
        }
    )
    client.publish(ATTENDANCE_TOPIC, payload)
    print("Published scan:", payload)


def publish_heartbeat(client):
    client.publish(HEARTBEAT_TOPIC, "{}")


def connect_sensor():
    uart = busio.UART(board.GP0, board.GP1, baudrate=UART_BAUDRATE)
    try:
        return adafruit_fingerprint.Adafruit_Fingerprint(uart)
    except RuntimeError:
        print("Could not find the fingerprint sensor. Check wiring.")
        raise


def main():
    connect_wifi()
    pool = socketpool.SocketPool(wifi.radio)
    sync_time(pool)
    finger = connect_sensor()
    client = connect_mqtt(pool)
    last_heartbeat = time.monotonic()

    print("Ready. Waiting for fingerprint scans...")
    while True:
        try:
            if finger.get_image() == adafruit_fingerprint.OK:
                if finger.image_2_tz(1) == adafruit_fingerprint.OK:
                    if finger.finger_fast_search() == adafruit_fingerprint.OK:
                        publish_scan(client, finger.finger_id)
                    else:
                        print("Fingerprint not recognized locally")

            if time.monotonic() - last_heartbeat >= HEARTBEAT_INTERVAL_SECONDS:
                publish_heartbeat(client)
                last_heartbeat = time.monotonic()

            client.loop(timeout=1)
        except (OSError, RuntimeError) as error:
            print("MQTT connection problem: {}, reconnecting...".format(error))
            try:
                client.reconnect()
            except (OSError, RuntimeError) as reconnect_error:
                print("Reconnect failed: {}, retrying in 5s".format(reconnect_error))
                time.sleep(5)


main()
