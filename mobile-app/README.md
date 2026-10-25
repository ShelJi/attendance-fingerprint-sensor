# PL admin — Management App

The app display name is **PL admin**. The bell opens Office/Outdoor attendance
activity with date filters and verification details. Live toasts cover all staff
check-ins/outs while the app is open; durable history remains available afterward.
See [workplace setup and notifications](../main/WORKPLACE_ATTENDANCE.md).

Expo SDK 58 + TypeScript app for Android and iOS. All requests use the existing
`/api/mobile/` endpoints. This app is for managers: employee records, attendance
monitoring, reports and fingerprint device control. Personal staff attendance and
password changes are available in the separate [staff app](../staff-app/README.md).

## Accounts and first setup

Start the [Django backend](../main/README.md), apply migrations and create a
management account before using this app. Sign in with a Django staff/superuser
account or an existing management account without an employee profile. Ordinary
employee accounts can authenticate but cannot access management data.

Creating an employee with this app provisions a linked login account. The unique
employee ID is its initial username and password. The employee can sign in to the
staff app and change that password. The employee name is a display name, not a
login identifier. Employee edits do not reset credentials.

## Run

```powershell
cd mobile-app
npm ci
npm start
```

Open the QR code in a matching Expo Go version, or use an Android/iOS development
build. iOS simulator requires macOS. This project targets native mobile; browser
authentication/CORS and web PDF sharing are not configured.

Sign in with an existing Django username/password. The default backend is
`https://s.plsofttech.com`, configured in `src/settings.ts`. Open **Settings**
from the login screen to change it; if signed in, sign out first. The current
route configuration makes Settings available only while signed out. The URL
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
2. Use **Employees** to add an employee or inspect their attendance history.
3. Use **Device** to enroll or manage the fingerprint slot matching the employee's
   fingerprint ID. The device must be online and actively polling commands.
4. Use **Calendar** for daily attendance and **Reports** for date-range totals and
   PDF sharing.
5. Tap the **bell** to inspect Office/Outdoor activity and all employee attendance events.
6. Sign out when finished. To change the backend, open **Settings** on the sign-in screen. Appearance follows the device's light/dark preference.

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

Policy editing is **Django Admin → Office locations**, not this app. An authorized backend administrator enters real SSID/BSSID, coordinates, radius and accuracy limits. Read the [backend office setup](../main/README.md#configure-office-policies) before onboarding staff.

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
script; its fixtures must match current protected routes and endpoints before
running it after route/API changes. Screenshots are written to ignored
`test-results/`. See [UI_REDESIGN.md](UI_REDESIGN.md) for the earlier visual audit.

## Troubleshooting and deployment

| Symptom | Check |
| --- | --- |
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
