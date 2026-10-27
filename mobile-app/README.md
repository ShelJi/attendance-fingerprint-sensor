# PL admin — Management App

The app display name is **PL admin**. The bell opens Office/Outdoor attendance
activity with date filters and verification details. Live toasts cover all staff
check-ins/outs while the app is open; durable history remains available afterward.
See [workplace setup and notifications](../main/WORKPLACE_ATTENDANCE.md).

Expo SDK 58 + TypeScript app for Android and iOS. All requests use the existing
`/api/mobile/` endpoints. This app is for managers: employee records, attendance
monitoring, reports and fingerprint device control. Managers can change their
password in Settings. Personal staff attendance is available in the separate
[staff app](../staff-app/README.md).

## Accounts and first setup

Start the [Django backend](../main/README.md), apply migrations and create a
management account before using this app. Sign in with a Django staff/superuser
account or an existing management account without an employee profile. Ordinary
employee accounts are directed to the staff app before entering admin navigation.

Creating an employee with this app provisions a linked login account. The unique
employee ID is its username. Leave Password blank for the initial `12345`, or enter
a custom password. The employee can sign in to the
staff app and change that password. The employee name is a display name, not a
login identifier. Employee edits do not reset credentials.

## Run

```powershell
cd mobile-app
npm ci
Copy-Item .env.example .env
```

Copy the example only on first setup. Set `.env` to the local backend computer's Wi-Fi IP, for example:

```dotenv
EXPO_PUBLIC_API_URL=http://192.168.1.20:8000
```

Replace that example IP using `ipconfig` on the backend computer. With Django running on `0.0.0.0:8000`, start this app with:

```powershell
npm start -- --port 8081 --lan
```

Keep this terminal and the backend terminal open. Scan this app's QR code on the phone. If staff-app is also running, give it port 8082. Port 8081 serves Expo; the Backend URL must use Django's port 8000. Restart Expo and reload the app after changing `.env`.

## How it works

PL admin signs in to the shared Django backend with a management account. It keeps authentication in session cookies and sends CSRF tokens for changes. Employees, session totals, calendar data and reports come from that backend; the app does not keep a separate attendance database.

Adding a person creates both an employee record and its initial login account. Device actions queue commands on the backend, then poll for the sensor result. The sensor must be connected and polling to execute them. The bell reads saved attendance events and evidence; foreground polling displays new check-ins/outs as toasts. Settings changes the backend connection or the signed-in manager's password.

Open the QR code in a matching Expo Go version, or use an Android/iOS development
build. iOS simulator requires macOS. This project targets native mobile; browser
authentication/CORS and web PDF sharing are not configured.

Sign in with an existing local Django username/password. The default backend is
`http://127.0.0.1:8000`, configured in `src/settings.ts`. For a physical phone,
set `EXPO_PUBLIC_API_URL` in `.env` to your computer's Wi-Fi IP on port 8000
and restart Expo. The phone and computer must share the same Wi-Fi. The old saved
`https://s.plsofttech.com` default is automatically replaced by the local default.
Open **Settings**
from the login screen or any main tab to change it. Settings is available both
before and after sign-in; changing servers returns you to sign-in. The URL
field does not appear directly in the sign-in form. You can also copy
`.env.example` to `.env` and set
`EXPO_PUBLIC_API_URL` as the default. Saved in-app Settings override this default.
The URL is public configuration,
not a secret. The last successful origin is saved with Expo SecureStore; passwords
and CSRF tokens are not persisted by app code. Native networking manages session
cookies; on launch the app checks the session and asks for login if it has expired.
The web visual-preview adapter stores only that public origin in localStorage;
it does not store credentials or configure production browser authentication.

## Local backend

From the repository root:

```powershell
.venv/Scripts/python.exe main/manage.py runserver 0.0.0.0:8000
```

Use your computer's LAN IP on a physical phone (same Wi-Fi), for example
`http://192.168.1.20:8000`. Android emulator can use `http://10.0.2.2:8000`.
`localhost` on the phone refers to the phone. Allow port 8000 through your local
firewall if needed. HTTP is for local development only; release login requires
HTTPS. Native development builds may require platform-specific local network /
cleartext configuration or an HTTPS tunnel. Do not put passwords in environment files.

## Features

- Session login/logout with cookie credentials, CSRF bootstrap and token rotation.
- Password changes in Settings, preserving the current session and rotating CSRF.
- Overview counts and device availability.
- Search employees, create with existing server validation, filter and page history.
- Device commands, ID validation, delete/replace confirmation, result polling.
  Stop watching only stops local polling; it does not cancel a server command.
- Calendar month summaries and daily attendance.
- Date-filtered reports and authenticated PDF download to the native share sheet.
  Temporary PDF cache files are removed after sharing.
- Loading, empty, retry, validation, network failure, and expired-session states.
- Separate Office/Outdoor/Device activity with submitted workplace evidence.
- Live management attendance toasts and persistent event history, including fingerprint scans.

Hardware scan/heartbeat/command polling APIs are intentionally left to the Pico;
the app uses the authenticated device-control endpoints. Device command state is
not saved across app restarts. Calendar/report views use the server's existing
grouping and totals. Large reports are rendered in a scroll view; use narrower
date ranges for large installations.

## Typical workflow

1. Sign in, then check **Overview** for attendance and device availability.
2. Use the **People** tab to add an employee or inspect their attendance history. Enter a name, unique employee ID and fingerprint ID. Password is optional; blank uses `12345`. Share the employee ID as username and the chosen/default password; the employee changes it in PL attendance.
3. Use **Device** to enroll or manage the fingerprint slot matching the employee's
   fingerprint ID. The device must be online and actively polling commands.
4. Use **Calendar** for daily attendance and **Reports** for date-range totals and
   PDF sharing.
5. Tap the **bell** to inspect Office/Outdoor activity and all employee attendance events.
6. Open **Settings** from the header to change your password or backend URL. A password change keeps the current session; a server change returns you to sign-in. Settings is also available before sign-in.
7. Sign out from Overview when finished. Appearance follows the device's light/dark preference.

Employee editing, account activation, username changes and password resets are handled in the backend's Django Admin: **Employees** for profile details and **Users** for account details. A superuser can manage all registered attendance models there. The mobile employee screen displays attendance history; it is not a profile-editing form.

### Create an employee with a password

1. Open **People → Add team member**.
2. Enter Full name, Employee ID and Fingerprint ID.
3. Leave **Password** blank to use `12345`, or enter a custom password.
4. Tap **Create employee**. The employee uses the Employee ID as their username in PL attendance and changes the initial password there.

For example, Employee ID `EMP-001` with Password blank creates login `EMP-001` / `12345`. Passwords are not shown in employee details. To reset an existing password, use Django Admin → Employees → the employee → Password → Save; blank preserves the existing password. Creating/updating other employee details does not reset existing credentials. Changing your own password in PL admin Settings affects only your management account.

The backend applies five-minute minimum intervals between check-in/out actions.
Counts, dates and worked durations come from the server. Changing a backend URL
returns the app to sign-in; supply only an origin, with no `/api/mobile/` suffix.

## Screens and navigation

| Screen / entry point | What it provides |
| --- | --- |
| Sign-in / Settings | Username/password, configured server, saved backend origin; no stored password |
| Overview | Team count, today’s sessions, active sessions, device availability and shortcuts |
| People | Search by name/employee ID; create a member; open attendance details |
| Employee details | Date filters, worked total, sessions and pagination |
| Add employee | Name, unique employee ID and fingerprint slot; server form validation |
| Device | Command selection, applicable fingerprint ID, delete/replace confirmation, queued/running results |
| Calendar | Monthly grid, previous/next and month/year jump, today/weekends/attendance markers, daily drill-down |
| Reports | Full-current-month initial dates, editable filters, employee totals and PDF share/save |
| Bell → Attendance activity | All, Office, Outdoor and Device / legacy events with detailed verification |

The calendar represents attendance, not an event scheduler: there are no event-creation, recurrence, reminder or weekly-scheduling features. Existing web calculations supply the actual totals; no production mock data is displayed.

## Office and outdoor details

Open the bell from any main tab. Select **Office** or **Outdoor** to see each source separately; **All** includes both plus fingerprint/historical events. A compact date summary starts at the first and ends on the last day of the current month. Tap its options control to edit dates. The endpoint returns 50 records per page, newest event first.

Each event shows employee name/code, check-in/out, time, session and source. Office details include office name, SSID/BSSID, coordinates, GPS uncertainty and capture time. Outdoor details include place name, day’s work, coordinates, uncertainty and capture time. **View location on map** opens the reported coordinates in an external map. No pictures are collected or displayed for verification.

Counts are attendance events, not unique employees: one check-in and one check-out count as two. Totals show all sources for the selected date range even when rows are filtered by one source. A mixed session is classified per action, so its Office check-in and Outdoor check-out appear in their respective views.

Device / legacy means no mobile GPS/Wi-Fi evidence exists; it must not be interpreted as a verified mobile Office check-in. Existing historical sessions are included through migration backfill. Normal worked-duration reports remain available separately.

Open **Overview → App configuration** as a manager. Select an office to update it, or tap **Add office**. Stand at the office centre, tap **Use current location**, and allow location access. Review the captured latitude/longitude or enter them manually. Enter the office name, exact Wi-Fi SSID and access-point BSSID, allowed radius (10–1000 m), and maximum GPS uncertainty (1–100 m), then tap **Save configuration**. Defaults are 100 m radius and 50 m uncertainty.

The BSSID is the router/access-point MAC, not the phone MAC. No Wi-Fi password is stored; connect the staff phone using its device Wi-Fi settings. Add one configuration per access point. Active configurations apply to the next staff office check-in/out; disable old configurations to retain history. Staff cannot edit these settings. The website dashboard and Django Admin edit the same records. Read the [backend office setup](../main/README.md#configure-office-policies).

GPS capture uses foreground `expo-location` permission only when requested. If permission is denied or capture fails, enter coordinates manually. Browser capture needs HTTPS or localhost. Existing installed development/production apps need a new native build for the added location module and permission configuration.

## Notifications

While signed in, PL admin polls the management feed every five seconds when active. Each accepted staff check-in/out or fingerprint login/logout creates a durable event; cooldown attempts, refreshes and account sign-in/sign-out do not. New events appear as queued, dismissible toasts. The initial feed request establishes a cursor without replaying old events as toasts; missed history is available through Attendance activity.

This is foreground in-app delivery, **not OS push notification delivery when the app is closed**. No push tokens/provider are configured. Temporary connection failures are retried. A foreground toast does not automatically reload an already-open activity list; use Refresh activity or reopen the screen to obtain the latest rows.

Staff accounts cannot read this management feed. Personal attendance and personal notifications belong in [PL attendance](../staff-app/README.md).

## Branding and appearance

`app.json` sets the display name to **PL admin**. `assets/pl-logo.jpg` is the supplied artwork; `pl-icon.png` and `pl-adaptive-icon.png` package it for launchers. The web favicon and sign-in hero use the same brand. `scripts/prepare-brand-assets.cjs` can regenerate the square launcher assets from the original artwork without redrawing/cropping it.

The UI uses system light/dark appearance, shared components/theme, responsive layouts and keyboard-aware scrolling. Native launcher names/icons and permission/config-plugin changes require a new installed build. Expo Go retains its own home-screen icon; it is a preview host rather than the finished branded binary.

## Checks

```powershell
npm test
npm run typecheck
npm run lint
npx expo export --platform android
```

See the [backend API contract](../main/MOBILE_API.md).
Expo setup reference: [Router installation](https://docs.expo.dev/router/installation/).

A bundle export produces JavaScript/Hermes assets, not an installable APK/IPA.
Signed binaries require an Expo/EAS project and platform signing credentials.
Physical device networking, native cookie persistence and sensor commands need a
smoke test against the configured backend.

For both native bundles use `npx expo export --platform android --platform ios`.
`npx --yes expo-doctor` checks SDK/peer dependency alignment. Export is not a
signed APK/IPA. Configure an Expo/EAS project and platform signing credentials
before producing installable binaries.

The optional browser checks use isolated test data and never write to the real
backend. After a web export, provide an installed Playwright module if it is not
locally available:

```powershell
npx expo export --platform web
$env:PLAYWRIGHT_MODULE = '<absolute path to playwright>'
node tests/activity-ui.cjs
```

This checks workplace navigation, Office/Outdoor filters, details, three viewport
widths and live-toast dismissal. `tests/ui-smoke.cjs` is the broader UI scenario
script; it also checks signed-in Settings, password changes and destructive-command
confirmation. Screenshots are written to ignored
`test-results/`. See [UI_REDESIGN.md](UI_REDESIGN.md) for the earlier visual audit.

## Troubleshooting and deployment

| Symptom | Check |
| --- | --- |
| Invalid JSON response / HTML instead of API data | Check `http://<computer-IP>:8000/api/mobile/auth/session/` from the phone; it must return JSON. Enter the backend origin only, not an Expo port or `/web/` URL |
| Cannot reach local backend | Keep Django running on `0.0.0.0:8000`, verify the current Wi-Fi IP, same reachable Wi-Fi and inbound port 8000 access |
| Old backend after editing `.env` | Restart Expo and reload; saved Settings take priority except the old hosted default, which is replaced automatically |
| API returns 404 | Correct origin; deployed backend includes `/api/mobile/` and the new activity/notification routes |
| Login succeeds but data returns 403 | Account has management access; an ordinary employee must use PL attendance |
| POST returns CSRF 403 | Retain cookies, refresh sign-in and rotated CSRF token; check deployed HTTPS/cookie settings |
| No live toast | App is active, session valid, connection available, and event is newer than its initial baseline |
| New event absent from open list | Refresh activity; verify date/source filters and page |
| PDF unavailable | Native share support, backend PDF response, authentication and active date filters |
| Native module / icon error | Run `npm ci`, Expo Doctor, then `npx expo start --clear`; rebuild a native binary if its modules/config changed |

Deploy backend code/migrations and restart the hosted server before distributing
an app that depends on them. Changing a URL does not deploy code or configure an
office. Browser CORS and web PDF sharing are not configured as production targets.
The installed dependency audit has reported Expo tooling advisories; review the
current `npm audit` output rather than forcing an incompatible SDK downgrade.

## Project structure

- `src/app/`: Expo Router screens, including the main tabs and employee forms.
- `src/api.ts`: JSON client, session cookies, CSRF handling and request errors.
- `src/session.tsx`: session bootstrap, sign-in/out and stored server selection.
- `src/settings.ts`: backend default, overridden by saved in-app settings.
- `src/ui.tsx` and `src/theme.ts`: shared components and appearance.
- `src/app/activity.tsx`: management source/date-filtered attendance evidence.
- `src/notifications.tsx`: foreground cursor polling, deduplication and toast queue.
- `tests/`: API/date unit checks and isolated browser UI scenarios.

See the [repository overview](../README.md) for the complete system.

### Automatically fill office Wi-Fi

In **Overview → App configuration**, tap **Use connected Wi-Fi** to fill the SSID and BSSID from the phone’s current Wi-Fi connection. Allow precise location permission and enable location services. Review the fields, capture the office location, then tap **Save configuration**. Capturing alone does not save changes.

For hotspot development, connect a second phone running PL admin to the hotspot and capture from that phone. If the hotspot’s BSSID changes, capture and save it again. Browsers cannot read these identifiers; manual entry remains available. Missing permission or unavailable identifiers leave existing fields unchanged. Existing installed native apps need rebuilding for NetInfo and the iOS Wi-Fi entitlement; iPhone requires a signed build with Wi-Fi access enabled.
