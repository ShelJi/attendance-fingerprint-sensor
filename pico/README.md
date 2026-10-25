# Pico Fingerprint Attendance Device

CircuitPython firmware and hardware experiments for a Raspberry Pi Pico 2 W with an AS608 fingerprint sensor. The HTTP attendance firmware connects to the included Django backend, records recognized fingerprints, sends heartbeats and executes sensor commands queued by managers.

## Choose the correct script

| File | Purpose |
| --- | --- |
| `code/phase_6.py` | HTTP attendance firmware with OLED feedback, heartbeat, enrollment and remote device commands; matches this repository's Django HTTP APIs |
| `fingerprint and overall/code.py` | Standalone serial menu for sensor wiring, enrollment, search and deletion; no backend connection |
| `fingerprint and overall/aaa_finished_new_registration_main_code.py` | Standalone sensor administration and enrollment menu |
| `fingerprint and overall/aaa_finished_main_code.py` | Earlier HTTP scan/heartbeat implementation |
| `fingerprint and overall/main.py`, `attendance_device.py` | MQTT variants requiring a separate broker and consumer; the included Django project has no MQTT consumer |
| `display/`, `code/phase_1.py` through earlier phases | Hardware bring-up and development experiments |

Copy only the selected entry script to the board as `code.py`. The files in this folder are alternatives and experiments, not a single package that should all run together. Google Sheets integration is a separate experiment and is not needed for Django attendance.

## Hardware

- Raspberry Pi Pico 2 W running CircuitPython.
- AS608-compatible UART fingerprint sensor.
- For `phase_6.py`, a compatible 128×64 SPI OLED wired for its included display driver.
- Wi-Fi access to the backend and a data-capable USB cable for setup/serial output.

Fingerprint wiring used by the scripts:

| Sensor | Pico |
| --- | --- |
| VCC | 3V3(OUT), subject to the module's power specification |
| GND | GND |
| TX | GP1 / UART RX |
| RX | GP0 / UART TX |

The default UART baud rate is 57600. Check the module specification and adjust `UART_BAUDRATE` if needed. The OLED connections in `phase_6.py` are SCK GP10, MOSI GP11, CS GP9, DC GP8 and reset GP12; connect power/ground according to the display's specification.

## Install and configure HTTP firmware

1. Install CircuitPython for the Pico 2 W. The board should appear as `CIRCUITPY` over USB.
2. From the repository root, install host tools with `uv sync` and install the required CircuitPython libraries onto the connected board:

   ```powershell
   uv run circup install adafruit_fingerprint adafruit_requests
   ```

3. Make a local copy of `code/phase_6.py`. Set `WIFI_SSID`, `WIFI_PASSWORD`, `BACKEND_URL` and `DEVICE_ID` for your installation. Use the backend host's LAN address or HTTPS hostname; `localhost` on the board cannot reach your computer. Keep actual credentials out of commits.
4. Copy that configured script to `CIRCUITPY/code.py`. It starts automatically; open a serial terminal to monitor startup and network/sensor errors.
5. Start the [Django backend](../main/README.md), then wait for heartbeats to show the device in the web or management app. The status endpoint creates/updates its device record; command polling requires an active matching device ID.
6. Enroll a fingerprint into a known sensor slot, then create an employee whose `fingerprint_id` matches that slot. A recognized slot without a matching employee cannot register attendance.

`phase_6.py` reads its connection values from constants, not `settings.toml`. The TOML example under `fingerprint and overall/` belongs to the alternate firmware; do not assume it configures the HTTP script.

## Attendance and commands

The HTTP firmware posts matched slot IDs to `/api/attendance/scan/` and displays the backend's result. It sends heartbeats to `/api/device/status/` about every 30 seconds; the backend considers a device online for two minutes after its last heartbeat.

The backend records the first action as check-in. Check-out requires five minutes of active time, and a new check-in requires five minutes after check-out. These are server rules shared with the staff app. Fingerprint templates stay in the sensor; the backend stores their slot identifiers and attendance records.

## Relationship to office/outdoor mobile attendance

**PL attendance** verifies a phone’s connected Wi-Fi and GPS for Office actions,
or GPS/place/work details for Outdoor actions. These mobile evidence requirements
do not change the Pico scan payload or firmware. The Pico does not submit phone
GPS, and a successful scan is not described as mobile Office verification.

With backend migration 0006 applied, accepted Pico logins/logouts also create
durable attendance notifications. The employee’s signed-in staff app receives
its own new scan toasts; PL admin and management web pages receive events for all
employees while active. A cooldown response creates no new event. There is no
OS push delivery to a closed app.

Pico scans and older sessions without mobile evidence appear under
**Device / legacy** in PL admin’s bell/activity screen and
`/web/work-attendance/`. Office and Outdoor remain separate filters. This source
label preserves history without inventing GPS proof or changing worked times.
No firmware modification or photo capture is needed for notification support.
See [backend deployment and office setup](../main/WORKPLACE_ATTENDANCE.md).

Remote commands use GET `/api/device/command/` and POST `/api/device/command/result/`. Supported commands include listing slots, manual/automatic enrollment, deletion, replacement, verification, summary and sensor information. The device must actively poll before a queued command can execute.

In `phase_6.py`, capturing a fingerprint image starts/restarts a 100-second command-polling session, checked at one-second intervals. If a queued command remains pending, place a finger on the reader to open that polling window and check serial output. It does not poll continuously at all times. Delete/replace operations change sensor templates, so check the employee-to-slot mapping before issuing them.

## MQTT alternatives

The MQTT scripts read Wi-Fi, broker and device settings through `os.getenv()`. They publish to `professional-admin/devices/<device_id>/attendance` and `professional-admin/devices/<device_id>/heartbeat`, and require the fingerprint, NTP and MiniMQTT CircuitPython libraries.

These variants reference a separate MQTT backend architecture. This repository's Django application exposes HTTP device endpoints and does not provide the referenced consumer command. Use the HTTP firmware for the included web/mobile applications unless you supply that integration yourself.

## Troubleshooting and validation

- Sensor not found: verify common ground, crossed TX/RX, module power and baud rate; use the standalone sensor menu first.
- Device offline: verify Wi-Fi, backend origin, matching device ID and heartbeat requests.
- Employee not found: ensure the enrolled template slot equals an employee's `fingerprint_id`.
- Command pending: confirm the device is active and inside its polling session.
- Attendance unchanged: check the backend's five-minute cooldown response.

Firmware requires the physical board and is not executable with desktop CPython. Files in `display/` are manual hardware tests. The host-side [testing scripts](../main/README.md#checks-and-manual-device-testing) can exercise HTTP endpoints without the board, but do not verify sensor wiring, OLED behavior or template operations.

See the [system overview](../README.md), [web backend](../main/README.md) and [management app](../mobile-app/README.md).
