# Fingerprint Attendance System

Employee attendance system with a Django web portal and API, a management mobile app, a staff mobile app, and Raspberry Pi Pico fingerprint firmware. Fingerprint scans and staff submissions share the same attendance records and check-in/check-out rules.

## Applications

| Component | Purpose | Documentation |
| --- | --- | --- |
| `main/` | Django management website, authentication, attendance API, reports and device commands | [Web and backend](main/README.md) |
| `mobile-app/` | **PL admin**: Android/iOS management app, Office/Outdoor activity, reports, notifications and device control | [Management app](mobile-app/README.md) |
| `staff-app/` | **PL attendance**: Android/iOS personal attendance with office Wi-Fi/GPS or outdoor work details | [Staff app](staff-app/README.md) |
| `pico/` | CircuitPython fingerprint scanning, device heartbeats and sensor commands | [Device firmware](pico/README.md) |
| `testing/` | Manual HTTP scripts for scans, heartbeats and device command polling | See [backend checks](main/README.md#checks-and-manual-device-testing) |

## How it works

1. A manager creates an employee with a name, unique employee ID and unique fingerprint slot ID.
2. The backend creates a linked login account. The employee ID is both the initial username and password; existing employees receive accounts through migration `0005_employee_user`.
3. An administrator configures office Wi-Fi and coordinates in **Django Admin → Office locations**.
4. The employee changes their password in PL attendance, then submits verified Office or Outdoor attendance, or scans an enrolled fingerprint on the device.
5. Managers view attendance, separate workplace activity, calendar summaries and PDF reports in PL admin or the website. Accepted check-ins/outs also create notification events.

The first attendance action of the day checks in. An active session can check out after five minutes. Another check-in is allowed five minutes after checking out. Multiple sessions per day are supported; worked duration is saved when a session closes. The server uses the `Asia/Kolkata` timezone and its own timestamps.

## Start the web backend

Requirements: Python 3.13 or newer and `uv`. Run from the repository root on Windows PowerShell:

```powershell
uv sync
.venv/Scripts/python.exe main/manage.py migrate
.venv/Scripts/python.exe main/manage.py createsuperuser
.venv/Scripts/python.exe main/manage.py runserver 0.0.0.0:8000
```

On macOS/Linux, replace `.venv/Scripts/python.exe` with `.venv/bin/python`. SQLite data is stored in `main/db.sqlite3`.

Open [web login](http://127.0.0.1:8000/login/), then [dashboard](http://127.0.0.1:8000/web/dashboard/) or [employees](http://127.0.0.1:8000/web/employees/). Django administration is at [admin](http://127.0.0.1:8000/admin/). There is no homepage route at `/`.

Back up an existing database before migration. If an employee ID already matches an existing Django username, the account migration stops rather than claiming or resetting that account. Resolve the collision before retrying.

## Start a mobile app

Install Node.js and npm. In a separate terminal, choose the application:

```powershell
cd mobile-app
npm ci
npm start
```

Use `cd staff-app` instead for PL attendance. Both apps use Expo SDK 58 and TypeScript. PL admin can be previewed in a compatible Expo Go client. Reliable staff Wi-Fi verification needs a native build; iOS requires the configured Access Wi-Fi Information entitlement and location permission, which Expo Go may not provide.

Set the management backend in **Settings on the sign-in screen**; sign out first if already in PL admin. Set the staff backend on its sign-in screen. Both default to `https://s.plsofttech.com` and accept `EXPO_PUBLIC_API_URL`. A phone connecting to a local backend needs the computer's LAN IP, such as `http://192.168.1.20:8000`; `127.0.0.1` refers to the phone itself. Release sign-in requires HTTPS. Local changes do not deploy code or migrations to the hosted server.

## Workplace verification

| Attendance source | Required information | What management sees |
| --- | --- | --- |
| Office in PL attendance | Fresh GPS and connected Wi-Fi SSID/BSSID matching an active office | Office name, check-in/out, coordinates, accuracy, capture time and Wi-Fi identifiers |
| Outdoor in PL attendance | Fresh GPS, place name and description of the day’s work | Place, work description, check-in/out, coordinates, accuracy and capture time |
| Fingerprint device or historical session | Existing fingerprint/session workflow; no mobile GPS evidence | **Device / legacy** classification; mobile verification is not implied |

Photo capture and photo verification are disabled. GPS is captured only when submitting attendance; there is no background location tracking. Requirements apply to both check-in and check-out.

An office policy contains an exact SSID, access-point BSSID, latitude/longitude, allowed radius and GPS uncertainty limit. The defaults are a 100 m radius and a 50 m uncertainty limit. The server requires the entire uncertainty circle to fit within the radius. Missing or mismatched office data blocks office attendance. Outdoor attendance does not require office Wi-Fi.

Migration `0006_officelocation_attendancenotification_and_more` adds office policies, per-action evidence and notifications. It creates notification history for existing sessions without changing their times; those events remain Device / legacy. Use real office settings, not the example coordinates in the documentation. See [complete workplace configuration and API details](main/WORKPLACE_ATTENDANCE.md).

## Viewing attendance and notifications

- **PL admin:** tap the bell on a main tab for Attendance activity. Choose All, Office, Outdoor or Device / legacy, change the date range, and page through records. Date defaults cover the whole current month.
- **Website:** choose **Office & Outdoor** in the sidebar, or open `/web/work-attendance/`. The same separate views and submitted details are available.
- **PL attendance:** employees see only their own attendance/evidence and receive toasts for their own accepted check-ins/outs, including scans made on the fingerprint reader.
- **Management:** PL admin and the web dashboard receive attendance toasts for all employees. The durable log retains events for the management history view.

Notifications mean **attendance check-in/out**, not account sign-in/sign-out. Apps poll while active every five seconds; web pages poll every fifteen seconds. Refreshes and five-minute cooldown attempts do not create duplicate events. Existing history is not replayed as toasts on a fresh app launch. These are in-app toasts, not background/closed-app push notifications.

## Deployment order

1. Back up the backend database and deploy the backend code.
2. Run migrations on the deployed server and restart its application process.
3. Configure active Office locations in Django Admin and confirm employee accounts.
4. Set both apps to that backend origin; rebuild installed apps for launcher branding and native permission changes.
5. Test office matching, an incorrect Wi-Fi/location, outdoor submissions, fingerprint scans, role access, notifications and password changes on real phones.

PL admin and PL attendance use the same supplied PL logo. Expo Go retains its own launcher identity; installed-app names/icons require a new native build. Signing credentials and production hosting configuration are not included.

## Accounts and APIs

- Management access: Django staff/superuser accounts and existing accounts without employee profiles.
- Employee access: personal attendance and password changes. Ordinary employee accounts cannot access management pages or APIs.
- Mobile JSON endpoints: `/api/mobile/`; see the [API contract](main/MOBILE_API.md).
- Hardware HTTP endpoints: `/api/attendance/scan/` and `/api/device/...`.
- Browser management pages: `/web/`; equivalent legacy routes also exist under `/api/`.

Passwords are hashed by Django. Existing Django credentials are preserved. The initial employee password is predictable by design; employees should change it after first sign-in. No password-change requirement is enforced by the application.

## Validation

```powershell
.venv/Scripts/python.exe main/manage.py test attendance --noinput
```

In either mobile app directory, run `npm test`, `npm run typecheck` and `npm run lint`. See each component README for device setup, bundle export and operating limits. The checked-in Django settings are for development; configure production settings before exposing the service publicly.

Additional reference: [mobile API contract](main/MOBILE_API.md), [workplace rules](main/WORKPLACE_ATTENDANCE.md), and [admin UI audit/verification](mobile-app/UI_REDESIGN.md).

Known limits: Wi-Fi/GPS are device-reported and are not cryptographic proof of presence; there is no device attestation, OS push delivery, offline attendance queue or automatic closure of yesterday’s open sessions. Actual phone permissions, indoor GPS, native cookies, PDF sharing and sensor operations require physical-device testing.
