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

For installed Android notifications, follow [Firebase setup](FIREBASE_SETUP.md), then [server cron job setup](SERVER_CRON_JOB.md). These guides cover both apps, the current cPanel paths, troubleshooting and worked examples.

1. A manager creates an employee with a name, unique employee ID and unique fingerprint slot ID.
2. The backend creates a linked login account. The employee ID is the username; new employees use initial password `12345` unless the manager enters a different password. Existing accounts keep their current passwords.
3. An administrator configures office Wi-Fi and coordinates in **Dashboard → App configuration** (also available in PL admin and Django Admin → Office locations).
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

Install Node.js and npm. Keep Django running in its own terminal. Find the backend computer's Wi-Fi IPv4 address with `ipconfig`; the examples below use `192.168.1.20`, which you must replace with your actual address.

For **PL admin**, open a second terminal at the repository root:

```powershell
cd mobile-app
npm ci
Copy-Item .env.example .env
```

Edit `mobile-app/.env` to contain your computer's address:

```dotenv
EXPO_PUBLIC_API_URL=http://192.168.1.20:8000
```

Then run `npm start -- --port 8081 --lan`. For **PL attendance**, open a third terminal at the repository root:

```powershell
cd staff-app
npm ci
Copy-Item .env.example .env
```

Set `staff-app/.env` to the same backend address, then run `npm start -- --port 8082 --lan`. Copy the example files only on first setup so existing `.env` values are preserved. Scan each terminal's QR code in a compatible Expo Go client, or open its URL in the corresponding development build.

Keep the phone and computer on the same reachable Wi-Fi. Django uses port **8000**; ports **8081/8082** serve the app code, not the attendance API. Keep all three terminals open. Stop each server with Ctrl+C. If the computer's IP changes, update both `.env` files and any saved PL admin backend URL, then restart Expo.

Both apps use Expo SDK 58 and TypeScript. Reliable staff Wi-Fi verification needs a native build; iOS requires the configured Access Wi-Fi Information entitlement and location permission, which Expo Go may not provide.

Set the management backend in **Settings**, available before and after sign-in. Set the staff backend on its sign-in screen. Both default to `http://127.0.0.1:8000` and accept `EXPO_PUBLIC_API_URL` in their own `.env` files. A phone connecting to the local backend needs the computer's LAN IP, such as `http://192.168.1.20:8000`; `127.0.0.1` refers to the phone itself. Restart Expo after changing `.env`. Release sign-in requires HTTPS.

## First use: admin and employee

1. Sign in at [Django admin](http://127.0.0.1:8000/admin/) using the superuser created during setup.
2. Under **Employees**, add a name, unique employee ID such as `EMP-001`, and a unique fingerprint slot ID. Password is optional: leave it blank for `12345` or enter a custom password. The login account is created automatically with username `EMP-001`.
3. For office attendance, add an active **Office location** with the real Wi-Fi SSID, access-point BSSID, coordinates and GPS limits. Outdoor attendance does not need an office policy.
4. Sign in to **PL admin** with the management account. Use People to create/view employees, Device for sensor commands, Calendar for daily attendance, Reports for worked hours/PDFs, and the bell for Office/Outdoor/Device activity. Change your own password under Settings.
5. Sign in to **PL attendance** with the employee account. Open Change password, enter the current password and a matching new password, then save. Choose In office or Outdoor and submit Verify & check in. Submit Verify & check out when finished, respecting the five-minute interval.
6. Update employee details in Django Admin → Employees and login usernames, account status or passwords in Users. Editing an employee ID does not rename the existing username or reset its password. A superuser can also manage sessions, devices, commands, offices, evidence and notifications; protected references can prevent deletion.

Both apps and the Pico must point to the same backend to share attendance. Fingerprint scanning additionally requires an enrolled sensor template whose slot matches the employee's fingerprint ID; see the [device setup](pico/README.md).

## Check the local connection

On the phone, open `http://192.168.1.20:8000/api/mobile/auth/session/`, replacing the IP. A working API returns JSON containing `authenticated` and `csrf_token`; `authenticated: false` is normal before sign-in.

| Problem | What to do |
| --- | --- |
| Cannot reach the server | Keep Django running on `0.0.0.0:8000`, check the computer's current IP, use the same reachable Wi-Fi and allow inbound access to port 8000 |
| Invalid JSON / HTML / 404 | Use the local backend origin on port 8000, without `/api/mobile/`; verify the session endpoint above instead of using a website or Expo server URL |
| App still uses an old address | Update PL admin Settings or the staff sign-in Server URL; restart Expo after editing `.env` and reload the app |
| Employee cannot open PL admin | Use the superuser/management account there; employee accounts belong in PL attendance |
| Sign-in says no employee profile | Create the employee and use its linked account; a standalone superuser is not an employee |
| Office attendance is disabled or rejected | Configure an active office, grant precise location, connect to its Wi-Fi and check the submitted GPS/SSID/BSSID |

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
- **PL attendance:** employees see only their own attendance/evidence and receive native notifications for their own accepted check-ins/outs, including scans made on the fingerprint reader.
- **Management:** PL admin receives native attendance notifications for employees; the web dashboard uses in-page activity alerts. The durable log retains events for the management history view.

Notifications mean **attendance check-in/out**, not account sign-in/sign-out. Native push requires provider credentials, a rebuilt installed app, notification permission, signed-in device registration and one server delivery worker or cron job. First registration skips existing events. Web pages poll every fifteen seconds while visible. Refreshes and rejected cooldown attempts do not create new events.

For example, an employee checks in after registering the rebuilt staff app. Django saves the event; the next cron run sends it through Expo and Firebase to registered phones. With one-minute cron, allow roughly a minute plus delivery time. A Settings test notification bypasses the attendance worker, so a successful test alone does not verify cron. See [Firebase examples](FIREBASE_SETUP.md#6-test-with-understandable-cases) and [cron examples](SERVER_CRON_JOB.md#5-test-with-real-examples).

## Deployment order

1. Back up the backend database and deploy the backend code.
2. Run migrations on the deployed server and restart its application process.
3. Configure active offices through Dashboard → App configuration and confirm employee accounts.
4. Set both apps to that backend origin; rebuild installed apps for launcher branding and native permission changes.
   Configure [Firebase and EAS credentials](FIREBASE_SETUP.md), then run one [attendance push worker or cPanel cron job](SERVER_CRON_JOB.md) for both apps.
5. Test office matching, an incorrect Wi-Fi/location, outdoor submissions, fingerprint scans, role access, notifications and password changes on real phones.

PL admin and PL attendance use the same supplied PL logo. Expo Go retains its own launcher identity; installed-app names/icons require a new native build. Signing credentials and production hosting configuration are not included.

## Accounts and APIs

### Employee passwords

| Action | Password behavior |
| --- | --- |
| Create an employee with Password blank | Initial password is `12345`; username is the employee ID |
| Create an employee with a custom Password | Uses the entered password after validation |
| Edit an employee with Password blank | Preserves the current password |
| Enter a Password on the Django admin employee edit form | Resets the linked account's password |
| Employee changes password in PL attendance | Requires current password and matching valid new passwords; keeps the session signed in |

Example: create employee `EMP-001` with Password blank, then sign in to PL attendance with username `EMP-001` and password `12345`. Tap **Change password**, enter `12345` as the current password, enter the new password twice and tap **Save password**. Future sign-ins use that new password. Existing employees keep their existing password until they or an administrator explicitly change it.

Only a superuser can use the employee edit form to reset a staff/superuser account's password. Employee passwords are saved as hashes in Django's linked user account; the form never reveals a saved password.

- Management access: Django staff/superuser accounts and existing accounts without employee profiles.
- Employee access: personal attendance and password changes. Ordinary employee accounts cannot access management pages or APIs.
- Mobile JSON endpoints: `/api/mobile/`; see the [API contract](main/MOBILE_API.md).
- Hardware HTTP endpoints: `/api/attendance/scan/` and `/api/device/...`.
- Browser management pages: `/web/`; equivalent legacy routes also exist under `/api/`.

Passwords are hashed in the linked Django user account, never stored as readable employee-table values or returned by the employee API. The employee form provides a Password field for setting/resetting that account's password. Blank means `12345` for a new employee and preserves the password on edits. Existing accounts are not reset automatically. Employees should change the initial password after first sign-in; no mandatory-change screen is enforced.

## Validation

```powershell
.venv/Scripts/python.exe main/manage.py test attendance --noinput
```

In either mobile app directory, run `npm test`, `npm run typecheck` and `npm run lint`. See each component README for device setup, bundle export and operating limits. The checked-in Django settings are for development; configure production settings before exposing the service publicly.

Additional reference: [mobile API contract](main/MOBILE_API.md), [workplace rules](main/WORKPLACE_ATTENDANCE.md), and [admin UI audit/verification](mobile-app/UI_REDESIGN.md).

Known limits: Wi-Fi/GPS are device-reported and are not cryptographic proof of presence; there is no device attestation, OS push delivery, offline attendance queue or automatic closure of yesterday’s open sessions. Actual phone permissions, indoor GPS, native cookies, PDF sharing and sensor operations require physical-device testing.
