"""AS608 fingerprint sensor bring-up/test script for the Raspberry Pi Pico 2 W.

This is a standalone hardware test, not the production attendance firmware —
it only proves the sensor itself is wired and working over UART before any
MQTT/Wi-Fi/attendance logic is added on top of it (see
context/architecture.md's "IoT Fingerprint System").

Setup
-----
1. Flash the Pico 2 W with CircuitPython (circuitpython.org/board/raspberry_pi_pico2_w/).
2. Install the official Adafruit CircuitPython Fingerprint library onto the
   board's CIRCUITPY/lib folder using circup (the official Adafruit library
   installer):
       pip install circup
       circup install adafruit_fingerprint
3. Copy this file to CIRCUITPY/code.py (CircuitPython auto-runs code.py on boot).
4. Open the board's serial console (e.g. `mpremote` or a serial terminal) to
   see the interactive test menu and enter commands.

Wiring (AS608 -> Pico 2 W)
---------------------------
    VCC -> 3V3(OUT)
    GND -> GND
    TX  -> GP1 (UART0 RX)
    RX  -> GP0 (UART0 TX)

AS608 modules commonly default to 57600 baud; some ship at 9600 — change
UART_BAUDRATE below if the sensor never responds.
"""

import board
import busio
import adafruit_fingerprint

UART_BAUDRATE = 57600

uart = busio.UART(board.GP0, board.GP1, baudrate=UART_BAUDRATE)

try:
    finger = adafruit_fingerprint.Adafruit_Fingerprint(uart)
except RuntimeError:
    print("Could not find the fingerprint sensor. Check wiring and UART_BAUDRATE.")
    raise


def search_fingerprint():
    """Scan a finger and search it against every template stored on the sensor."""
    print("Place finger on sensor...")
    while finger.get_image() != adafruit_fingerprint.OK:
        pass

    if finger.image_2_tz(1) != adafruit_fingerprint.OK:
        print("Could not process that image, try again")
        return

    if finger.finger_fast_search() != adafruit_fingerprint.OK:
        print("No match found")
        return

    print(f"Match found: id={finger.finger_id}, confidence={finger.confidence}")


def enroll_fingerprint(location):
    """Enroll a new fingerprint into the sensor's on-board template slot."""
    for scan in (1, 2):
        print(f"Place finger on sensor... (scan {scan} of 2)")
        while finger.get_image() != adafruit_fingerprint.OK:
            pass

        if finger.image_2_tz(scan) != adafruit_fingerprint.OK:
            print("Could not process that image, enrollment cancelled")
            return

        if scan == 1:
            print("Remove finger")
            while finger.get_image() != adafruit_fingerprint.NOFINGER:
                pass

    if finger.create_model() != adafruit_fingerprint.OK:
        print("The two scans did not match, enrollment cancelled")
        return

    if finger.store_model(location) != adafruit_fingerprint.OK:
        print(f"Could not store the template at slot {location}")
        return

    print(f"Enrolled fingerprint at slot {location}")


def delete_fingerprint(location):
    if finger.delete_model(location) == adafruit_fingerprint.OK:
        print(f"Deleted slot {location}")
    else:
        print(f"Could not delete slot {location}")


def show_templates():
    if finger.read_templates() != adafruit_fingerprint.OK:
        print("Could not read the template list")
        return
    print(f"Stored template slots: {finger.templates}")


def prompt_slot_number():
    while True:
        try:
            return int(input("Slot number (1-127): "))
        except ValueError:
            print("Enter a number")


def run_menu():
    print("AS608 fingerprint sensor connected.")
    show_templates()
    while True:
        print("\ne) enroll  f) find/search  d) delete  s) show slots  q) quit")
        choice = input("> ").strip().lower()
        if choice == "e":
            enroll_fingerprint(prompt_slot_number())
        elif choice == "f":
            search_fingerprint()
        elif choice == "d":
            delete_fingerprint(prompt_slot_number())
        elif choice == "s":
            show_templates()
        elif choice == "q":
            break
        else:
            print("Unknown option")


run_menu()
