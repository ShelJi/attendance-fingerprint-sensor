"""Minimal connection test between the AS608 fingerprint sensor and the Pico 2 W.

Run this before code.py when the sensor isn't responding at all — it isolates
wiring/baud-rate problems from the higher-level enroll/search logic in
code.py by doing the smallest possible thing: open the UART, try the
official library's handshake at each common baud rate, and if that fails,
listen for any raw bytes on the line so you can tell "nothing is wired" apart
from "wired, but wrong baud rate/protocol."

Wiring (AS608 -> Pico 2 W)
---------------------------
    VCC -> 3V3(OUT)
    GND -> GND
    TX  -> GP1 (UART0 RX)
    RX  -> GP0 (UART0 TX)

Usage: copy to CIRCUITPY/code.py (temporarily replacing code.py) and watch
the serial console.
"""

import time
import board
import busio
import adafruit_fingerprint

# AS608 modules ship at different default baud rates depending on the
# batch/vendor — try each common one instead of assuming 57600.
BAUD_RATES_TO_TRY = (57600, 9600, 115200)


def listen_for_raw_bytes(uart, seconds=2):
    """Report whether anything at all arrives on RX, independent of the library."""
    print(f"Listening on the line for {seconds}s to check basic wiring...")
    deadline = time.monotonic() + seconds
    seen_any = False
    while time.monotonic() < deadline:
        data = uart.read(32)
        if data:
            seen_any = True
            print(f"Raw bytes received: {data}")
    if not seen_any:
        print(
            "No bytes seen at all. Check: sensor has power (VCC/GND), TX/RX "
            "are not swapped (sensor TX -> Pico GP1, sensor RX -> Pico GP0), "
            "and connections are solid."
        )
    else:
        print("Bytes were seen but the library couldn't parse a valid reply — likely a baud-rate mismatch.")


def main():
    for baudrate in BAUD_RATES_TO_TRY:
        print(f"\n--- Trying {baudrate} baud ---")
        uart = busio.UART(board.GP0, board.GP1, baudrate=baudrate, timeout=1)

        try:
            finger = adafruit_fingerprint.Adafruit_Fingerprint(uart)
        except RuntimeError as error:
            print(f"Library handshake failed: {error}")
            listen_for_raw_bytes(uart)
            uart.deinit()
            continue

        print(f"Connection confirmed at {baudrate} baud.")
        if finger.read_templates() == adafruit_fingerprint.OK:
            print(f"Stored template slots: {finger.templates}")
        print(f"\nUse UART_BAUDRATE = {baudrate} in code.py.")
        return

    tried = ", ".join(str(b) for b in BAUD_RATES_TO_TRY)
    print(
        f"\nCould not connect at any common baud rate ({tried}). Double-check "
        "wiring (VCC/GND/TX/RX), confirm this is genuinely an AS608/R30x-"
        "protocol module, and that `circup install adafruit_fingerprint` "
        "completed without errors."
    )


main()
