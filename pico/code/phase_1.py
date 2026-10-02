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

WIFI_SSID = "iot kids"
WIFI_PASSWORD = "bright kidoos"

BACKEND_URL = "http://10.102.15.236:8000"

DEVICE_ID = "attendance-01"

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

UART_BAUDRATE = 57600

HEARTBEAT_INTERVAL = 30
RESPONSE_DISPLAY_TIME = 30

BOOT_MESSAGE = "SHELJ\nATTENDANCE\nREADY"



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
                baudrate=4000000,
                polarity=0,
                phase=0
            )

            self.dc.value = False
            self.cs.value = False

            self.spi.write(bytes([value]))

            self.cs.value = True

        finally:

            self.spi.unlock()

    def _data(self, data):

        while not self.spi.try_lock():
            pass

        try:

            self.spi.configure(
                baudrate=4000000,
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
# OLED
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

    oled.text(
        str(message)
    )

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

    finger = adafruit_fingerprint.Adafruit_Fingerprint(
        uart
    )

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
    print(
        "IP:",
        wifi.radio.ipv4_address
    )

except Exception as e:

    display("WiFi ERROR")

    print(
        "WiFi error:",
        e
    )

    raise


# ============================================================
# HTTP
# ============================================================

pool = socketpool.SocketPool(
    wifi.radio
)

requests = adafruit_requests.Session(
    pool
)


# ============================================================
# HEARTBEAT
# ============================================================

last_heartbeat = 0


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

        response.close()

        return True

    except Exception as e:

        print(
            "Device status error:",
            e
        )

        return False


def send_command_result(
    command_id,
    success,
    result,
):

    data = {
        "device_id": DEVICE_ID,
        "command_id": command_id,
        "success": success,
        "result": result,
    }

    try:

        print(
            "Sending command result:",
            data
        )

        response = requests.post(
            COMMAND_RESULT_URL,
            json=data,
        )

        print(
            "Command result status:",
            response.status_code,
        )

        try:
            print(
                "Command result response:",
                response.json(),
            )
        except Exception:
            pass

        response.close()

        return True

    except Exception as e:

        print(
            "Command result error:",
            e
        )

        return False


def list_fingerprint_ids():

    ids = []

    for fingerprint_id in range(1, 128):

        try:

            result = finger.load_model(
                fingerprint_id
            )

            if result == adafruit_fingerprint.OK:
                ids.append(fingerprint_id)

        except Exception as e:

            print(
                "ID check error:",
                fingerprint_id,
                e
            )

    return ids

def enroll_fingerprint(fingerprint_id):

    print(
        "Starting enrollment:",
        fingerprint_id
    )

    display(
        "PLACE\nFINGER"
    )

    while True:

        result = finger.get_image()

        if result == adafruit_fingerprint.OK:
            break

        if result != adafruit_fingerprint.NOFINGER:
            return False, "Fingerprint sensor error"

        time.sleep(0.1)

    if finger.image_2_tz(1) != adafruit_fingerprint.OK:

        return False, "Failed to read fingerprint"

    display(
        "REMOVE\nFINGER"
    )

    wait_for_finger_removal()

    display(
        "PLACE AGAIN"
    )

    while True:

        result = finger.get_image()

        if result == adafruit_fingerprint.OK:
            break

        if result != adafruit_fingerprint.NOFINGER:
            return False, "Fingerprint sensor error"

        time.sleep(0.1)

    if finger.image_2_tz(2) != adafruit_fingerprint.OK:

        return False, "Failed to read second fingerprint"

    if finger.create_model() != adafruit_fingerprint.OK:

        return False, "Fingerprints did not match"

    if finger.store_model(fingerprint_id) != adafruit_fingerprint.OK:

        return False, "Failed to store fingerprint"

    display(
        "ENROLL\nSUCCESS"
    )

    return True, {
        "fingerprint_id": fingerprint_id,
        "message": "Fingerprint enrolled successfully",
    }
    

def find_available_fingerprint_id():

    for fingerprint_id in range(1, 128):

        try:

            result = finger.load_model(
                fingerprint_id
            )

            if result != adafruit_fingerprint.OK:
                return fingerprint_id

        except Exception:

            return fingerprint_id

    return None


def enroll_auto():

    fingerprint_id = find_available_fingerprint_id()

    if fingerprint_id is None:

        return False, "Fingerprint database is full"

    return enroll_fingerprint(
        fingerprint_id
    )
    
    
def delete_fingerprint(fingerprint_id):

    print(
        "Deleting fingerprint:",
        fingerprint_id
    )

    result = finger.delete_model(
        fingerprint_id
    )

    if result != adafruit_fingerprint.OK:

        return False, {
            "fingerprint_id": fingerprint_id,
            "message": "Failed to delete fingerprint",
        }

    display(
        "DELETE\nSUCCESS"
    )

    return True, {
        "fingerprint_id": fingerprint_id,
        "message": "Fingerprint deleted successfully",
    }
    
    
    
def replace_fingerprint(fingerprint_id):

    print(
        "Replacing fingerprint:",
        fingerprint_id
    )

    result = finger.delete_model(
        fingerprint_id
    )

    if result != adafruit_fingerprint.OK:

        return False, {
            "fingerprint_id": fingerprint_id,
            "message": "Existing fingerprint could not be deleted",
        }

    return enroll_fingerprint(
        fingerprint_id
    )

def verify_fingerprint():

    display(
        "PLACE\nFINGER"
    )

    while True:

        result = finger.get_image()

        if result == adafruit_fingerprint.OK:
            break

        if result != adafruit_fingerprint.NOFINGER:
            return False, "Sensor error"

        time.sleep(0.1)

    if finger.image_2_tz(1) != adafruit_fingerprint.OK:

        return False, "Could not read fingerprint"

    if finger.finger_fast_search() != adafruit_fingerprint.OK:

        display(
            "NO MATCH"
        )

        wait_for_finger_removal()

        return False, {
            "message": "Fingerprint not found"
        }

    fingerprint_id = finger.finger_id
    confidence = finger.confidence

    display(
        "MATCH\nID " + str(fingerprint_id)
    )

    wait_for_finger_removal()

    return True, {
        "fingerprint_id": fingerprint_id,
        "confidence": confidence,
        "message": "Fingerprint verified",
    }
    
def fingerprint_summary():

    ids = list_fingerprint_ids()

    return True, {
        "total": len(ids),
        "capacity": 127,
        "available": 127 - len(ids),
        "ids": ids,
    }
    
def fingerprint_info():

    try:

        result = finger.read_sysparam()

        if result != adafruit_fingerprint.OK:

            return False, {
                "message": "Unable to read sensor information"
            }

        return True, {
            "capacity": finger.capacity,
            "security_level": finger.security_level,
            "device_address": finger.device_address,
            "packet_len": finger.packet_len,
            "baudrate": finger.baudrate,
        }

    except Exception as e:

        return False, {
            "message": str(e)
        }
        
        
def execute_command(command):

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

    try:

        if command_type == "LIST_IDS":

            display(
                "READING\nIDS"
            )

            ids = list_fingerprint_ids()

            success = True

            result = {
                "ids": ids,
                "total": len(ids),
                "message": "Fingerprint IDs loaded",
            }


        elif command_type == "ENROLL":

            success, result = enroll_fingerprint(
                fingerprint_id
            )


        elif command_type == "ENROLL_AUTO":

            success, result = enroll_auto()


        elif command_type == "DELETE":

            success, result = delete_fingerprint(
                fingerprint_id
            )


        elif command_type == "REPLACE":

            success, result = replace_fingerprint(
                fingerprint_id
            )


        elif command_type == "VERIFY":

            success, result = verify_fingerprint()


        elif command_type == "SUMMARY":

            success, result = fingerprint_summary()


        elif command_type == "INFO":

            success, result = fingerprint_info()


        else:

            success = False

            result = {
                "message": "Unknown command"
            }


        send_command_result(
            command_id,
            success,
            result,
        )

        return True


    except Exception as e:

        print(
            "Command execution error:",
            e
        )

        send_command_result(
            command_id,
            False,
            {
                "message": str(e)
            },
        )

        return False
    
    
    
def check_command():

    url = (
        COMMAND_URL
        + "?device_id="
        + DEVICE_ID
    )

    try:

        response = requests.get(
            url
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
    
    
    
def heartbeat():

    global last_heartbeat

    now = time.monotonic()

    if (
        now - last_heartbeat
        >= HEARTBEAT_INTERVAL
    ):

        send_device_status()

        last_heartbeat = now


# ============================================================
# ATTENDANCE
# ============================================================

def send_attendance(
    fingerprint_id
):

    data = {
        "fingerprint_id": str(
            fingerprint_id
        ),
        "device_id": DEVICE_ID
    }

    try:

        print(
            "Sending attendance:",
            data
        )

        response = requests.post(
            ATTENDANCE_URL,
            json=data
        )

        status_code = response.status_code

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

        return (
            None,
            None
        )


# ============================================================
# RESPONSE
# ============================================================

def get_response_message(
    status_code,
    result
):

    if isinstance(
        result,
        dict
    ):

        message = result.get(
            "message"
        )

        if message:

            return str(
                message
            )

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

    return (
        "SERVER\n"
        "ERROR"
    )


# ============================================================
# FINGER REMOVAL
# ============================================================

def wait_for_finger_removal():

    while True:

        heartbeat()

        result = finger.get_image()

        if result == (
            adafruit_fingerprint.NOFINGER
        ):

            return

        time.sleep(
            0.05
        )


# ============================================================
# ATTENDANCE SCAN
# ============================================================

def process_fingerprint():

    display(
        "READING..."
    )

    if finger.image_2_tz(
        1
    ) != adafruit_fingerprint.OK:

        display(
            "TRY AGAIN"
        )

        time.sleep(2)

        return

    if finger.finger_fast_search(
    ) != adafruit_fingerprint.OK:

        display(
            "NO MATCH"
        )

        time.sleep(2)

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

    response_start = (
        time.monotonic()
    )

    while (
        time.monotonic()
        - response_start
        < RESPONSE_DISPLAY_TIME
    ):

        heartbeat()

        result = finger.get_image()

        if result == (
            adafruit_fingerprint.OK
        ):

            display(
                "READING..."
            )

            time.sleep(
                0.2
            )

            if finger.image_2_tz(
                1
            ) == adafruit_fingerprint.OK:

                if finger.finger_fast_search(
                ) == adafruit_fingerprint.OK:

                    fingerprint_id = (
                        finger.finger_id
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

                    response_start = (
                        time.monotonic()
                    )

            wait_for_finger_removal()

        time.sleep(
            0.05
        )

    display(
        BOOT_MESSAGE
    )


# ============================================================
# MAIN LOOP
# ============================================================

print("--------------------------------")
print("Attendance Device")
print("--------------------------------")
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
print("--------------------------------")


send_device_status()

last_heartbeat = (
    time.monotonic()
)

display(
    BOOT_MESSAGE
)

while True:

    try:

        heartbeat()


        # =========================
        # CHECK WEBSITE COMMAND
        # =========================

        command_data = check_command()

        if command_data is not None:

            command = command_data.get(
                "command"
            )

            if command is not None:

                execute_command(
                    command
                )

                display(
                    BOOT_MESSAGE
                )

                time.sleep(0.2)

                continue


        # =========================
        # ATTENDANCE SCANNING
        # =========================

        result = finger.get_image()

        if result == adafruit_fingerprint.OK:

            process_fingerprint()

            wait_for_finger_removal()

            display(
                BOOT_MESSAGE
            )


        elif result != adafruit_fingerprint.NOFINGER:

            print(
                "Fingerprint sensor error:",
                result
            )

            display(
                "SENSOR\nERROR"
            )

            time.sleep(2)

            display(
                BOOT_MESSAGE
            )


        time.sleep(0.05)


    except Exception as e:

        print(
            "Main loop error:",
            e
        )

        display(
            "SYSTEM\nERROR"
        )

        time.sleep(3)

        display(
            BOOT_MESSAGE
        )

    try:

        heartbeat()

        result = finger.get_image()

        if result == (
            adafruit_fingerprint.OK
        ):

            process_fingerprint()

            wait_for_finger_removal()

            display(
                BOOT_MESSAGE
            )

        elif result != (
            adafruit_fingerprint.NOFINGER
        ):

            print(
                "Fingerprint sensor error:",
                result
            )

            display(
                "SENSOR\nERROR"
            )

            time.sleep(2)

            display(
                BOOT_MESSAGE
            )

        time.sleep(
            0.05
        )

    except Exception as e:

        print(
            "Main loop error:",
            e
        )

        display(
            "SYSTEM\nERROR"
        )

        time.sleep(3)

        display(
            BOOT_MESSAGE
        )