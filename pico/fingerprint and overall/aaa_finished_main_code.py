import time
import board
import busio
import digitalio
import wifi
import socketpool
import adafruit_requests
import adafruit_fingerprint


# ============================================================
# CONFIGURATION
# ============================================================

WIFI_SSID = "YOUR_WIFI_NAME"
WIFI_PASSWORD = "YOUR_WIFI_PASSWORD"

# IMPORTANT:
# Do NOT use 127.0.0.1 here.
# Use the IP address of the PC running Django.
BACKEND_URL = "http://192.168.1.100:8000"

DEVICE_ID = "attendance-01"

ATTENDANCE_URL = BACKEND_URL + "/api/attendance/scan/"
STATUS_URL = BACKEND_URL + "/api/device/status/"

UART_BAUDRATE = 57600

# Send device heartbeat every 30 seconds
HEARTBEAT_INTERVAL = 30


# ============================================================
# OLED SSD1309
# ============================================================

class SSD1309:

    WIDTH = 128
    HEIGHT = 64

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

        self.spi.configure(
            baudrate=4000000,
            polarity=0,
            phase=0
        )

        self.dc.value = False
        self.cs.value = False

        self.spi.write(bytes([value]))

        self.cs.value = True
        self.spi.unlock()

    def _data(self, data):

        while not self.spi.try_lock():
            pass

        self.spi.configure(
            baudrate=4000000,
            polarity=0,
            phase=0
        )

        self.dc.value = True
        self.cs.value = False

        self.spi.write(data)

        self.cs.value = True
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

        if 0 <= x < 128 and 0 <= y < 64:

            index = x + (y // 8) * 128

            self.buffer[index] |= 1 << (y % 8)

    def text(self, message, x=0, y=0):

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

            if cursor_x + 6 > 128:

                cursor_x = x
                cursor_y += 8

            if cursor_y + 7 > 64:
                break

            bitmap = self.FONT[character]

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

        self._data(self.buffer)


# ============================================================
# OLED SETUP
# ============================================================

spi = busio.SPI(
    clock=board.GP10,
    MOSI=board.GP11
)

cs = digitalio.DigitalInOut(board.GP9)
dc = digitalio.DigitalInOut(board.GP8)
rst = digitalio.DigitalInOut(board.GP12)

cs.direction = digitalio.Direction.OUTPUT
dc.direction = digitalio.Direction.OUTPUT
rst.direction = digitalio.Direction.OUTPUT

cs.value = True

oled = SSD1309(
    spi,
    cs,
    dc,
    rst
)


def display(message):

    print(message)

    oled.clear()
    oled.text(message)
    oled.show()


# ============================================================
# FINGERPRINT SENSOR
# ============================================================

uart = busio.UART(
    board.GP0,
    board.GP1,
    baudrate=UART_BAUDRATE
)

try:

    finger = adafruit_fingerprint.Adafruit_Fingerprint(uart)

    print("Fingerprint sensor OK")

except RuntimeError:

    display("Fingerprint\nERROR")

    raise


# ============================================================
# WIFI
# ============================================================

display("Connecting\nWiFi...")

try:

    wifi.radio.connect(
        WIFI_SSID,
        WIFI_PASSWORD
    )

    print("WiFi connected")
    print("IP:", wifi.radio.ipv4_address)

except Exception as e:

    display("WiFi ERROR")

    print("WiFi error:", e)

    raise


# ============================================================
# HTTP CLIENT
# ============================================================

pool = socketpool.SocketPool(wifi.radio)

requests = adafruit_requests.Session(pool)


# ============================================================
# DEVICE STATUS
# ============================================================

def send_device_status():

    data = {
        "device_id": DEVICE_ID
    }

    try:

        response = requests.post(
            STATUS_URL,
            json=data
        )

        print(
            "Device status:",
            response.status_code
        )

        print(response.text)

        response.close()

        return True

    except Exception as e:

        print(
            "Device status error:",
            e
        )

        return False


# ============================================================
# SEND ATTENDANCE
# ============================================================

def send_attendance(fingerprint_id):

    data = {
        "fingerprint_id": str(fingerprint_id),
        "device_id": DEVICE_ID
    }

    try:

        print("Sending attendance:")
        print(data)

        response = requests.post(
            ATTENDANCE_URL,
            json=data
        )

        print(
            "Attendance status:",
            response.status_code
        )

        print(
            "Response:",
            response.text
        )

        status_code = response.status_code

        try:
            result = response.json()
        except Exception:
            result = {}

        response.close()

        return status_code, result

    except Exception as e:

        print(
            "Attendance error:",
            e
        )

        return None, None


# ============================================================
# FINGERPRINT SCAN
# ============================================================

def scan_fingerprint():

    display("Place finger")

    # Wait for finger
    while True:

        result = finger.get_image()

        if result == adafruit_fingerprint.OK:
            break

        if result == adafruit_fingerprint.NOFINGER:
            continue

        print(
            "Fingerprint image error:",
            result
        )

        display("Scan error")

        time.sleep(2)

        return


    # Convert image to template
    if finger.image_2_tz(1) != adafruit_fingerprint.OK:

        display("Try again")

        time.sleep(2)

        return


    # Search stored fingerprints
    if finger.finger_fast_search() != adafruit_fingerprint.OK:

        display("No match")

        print("No fingerprint match")

        time.sleep(2)

        return


    fingerprint_id = finger.finger_id
    confidence = finger.confidence

    print(
        "Fingerprint matched:",
        fingerprint_id,
        "confidence:",
        confidence
    )


    # Show ID
    display(
        "ID: " + str(fingerprint_id)
    )

    time.sleep(0.5)


    # Send to Django
    status_code, result = send_attendance(
        fingerprint_id
    )


    # ========================================================
    # SERVER RESPONSE
    # ========================================================

    if status_code == 200:

        display("Attendance\nRecorded")

        time.sleep(2)

    elif status_code == 201:

        display("Attendance\nRecorded")

        time.sleep(2)

    elif status_code == 400:

        display("Invalid\nRequest")

        time.sleep(2)

    elif status_code == 404:

        display("User not\nfound")

        time.sleep(2)

    else:

        display("Server\nError")

        time.sleep(2)


# ============================================================
# STARTUP
# ============================================================

display("Attendance\nSystem")

time.sleep(1)

print("--------------------------------")
print("Attendance Device")
print("--------------------------------")
print("Device ID:", DEVICE_ID)
print("IP:", wifi.radio.ipv4_address)
print("Backend:", BACKEND_URL)
print("--------------------------------")


# Register / announce device
send_device_status()

last_heartbeat = time.monotonic()


# ============================================================
# MAIN LOOP
# ============================================================

while True:

    try:

        # ----------------------------------------------------
        # HEARTBEAT
        # ----------------------------------------------------

        now = time.monotonic()

        if now - last_heartbeat >= HEARTBEAT_INTERVAL:

            send_device_status()

            last_heartbeat = now


        # ----------------------------------------------------
        # FINGERPRINT
        # ----------------------------------------------------

        scan_fingerprint()


        # Small delay
        time.sleep(0.5)


    except Exception as e:

        print(
            "Main loop error:",
            e
        )

        display("System\nError")

        time.sleep(3)