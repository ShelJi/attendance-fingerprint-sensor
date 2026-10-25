# PL attendance

Expo SDK 58 / React Native app for employees on Android and iOS. It connects to the same Django backend as the website and management app, while exposing only the employee's personal attendance workflow.

## Features

- Sign in with an employee username and password.
- Check in or check out with a clear current attendance status.
- View today's sessions, including check-in/out times and open sessions.
- Refresh attendance after using another device or the fingerprint reader.
- Change the account password without leaving the current session.
- Sign out, with visible loading, validation, cooldown and network error states.
- Office verification using admin-configured Wi-Fi SSID/BSSID and GPS radius.
- Outdoor attendance with GPS, place name and daily work description; no photos.
- Toast notifications for your own accepted check-ins/outs and fingerprint scans while signed in.

Employee creation, team reports and sensor administration belong to the [management app](../mobile-app/README.md) and [web portal](../main/README.md).

## Run

First apply the backend migration from the repository root:

```powershell
uv sync
.venv/Scripts/python.exe main/manage.py migrate
.venv/Scripts/python.exe main/manage.py runserver 0.0.0.0:8000
```

Then in `staff-app`:

```powershell
npm ci
npm start
```

Use an Android/iOS build for reliable Wi-Fi verification. iOS needs the configured Access Wi-Fi Information entitlement in a signed build; Expo Go may not expose SSID/BSSID. Enter your backend origin on the sign-in screen, or set `EXPO_PUBLIC_API_URL` before starting Expo. On a physical phone use the computer's LAN address rather than `127.0.0.1`. Release builds require HTTPS. Use a distinct origin/session for management and employee accounts during testing.

The default origin is `https://s.plsofttech.com`. For a phone on the same Wi-Fi use an origin such as `http://192.168.1.20:8000`; the Android emulator can use `http://10.0.2.2:8000`. Enter only the origin, without `/api/mobile/`. The app targets native mobile; browser authentication/CORS is not configured.

## Accounts and sign-in

Each employee's unique `employee_id` is their initial username **and** password. Existing employees receive accounts during migration. New employees created through the management API, web form or `Employee.objects.create()` receive accounts automatically. Django admin's employee form instead exposes the required linked user field; create/select a suitable user there. Names are not used because they need not be unique. Editing an employee does not reset their password or change their login username. Existing Django accounts retain their credentials.

If an employee ID already matches an existing Django username, migration stops without claiming that account or resetting its password. Resolve that username collision before migrating. Account creation should use `Employee.save()` / `objects.create()`, not `bulk_create()`.

Passwords are never stored by the app. Authentication uses the backend's existing session cookies and CSRF protection. Reopen the app and sign in again; no persistent credential storage is added.

Attendance uses server timestamps and the same five-minute cooldown as fingerprint scans. Staff can only submit and view their own attendance; management accounts without an employee profile cannot submit attendance. Office submissions now require Wi-Fi and GPS matching; outdoor submissions require fresh GPS, place and work details. See [workplace setup and notification behavior](../main/WORKPLACE_ATTENDANCE.md).

## Daily workflow

1. Enter the backend origin and sign in. On first use, open **Change password** and replace the initial password.
2. Choose **In office** or **Outdoor**. For outdoor work enter a place name and the day’s work description. Enable precise location and connect to office Wi-Fi when in office.
3. Tap **Verify & check in** when starting work or **Verify & check out** when finished. The backend requires at least five minutes after check-in.
4. For another session that day, wait five minutes after check-out before checking in again.
5. Tap **Refresh attendance** after fingerprint scans or if another client changed attendance. Sign out when done.

Password changes require the current password and matching new-password fields. Django rejects weak replacements, including overly short, common, numeric or overly similar passwords. Changing the initial password is recommended but is not enforced at sign-in.

The backend groups today's activity in `Asia/Kolkata`. An open session from a previous day is not automatically closed. The app requires a network connection and does not queue offline attendance. Server selection and credentials are not persisted by app code; there is no self-service account registration screen.

## Office attendance: required setup and checks

The backend administrator must first add an active **Office location** in Django Admin (`/admin/`). It contains the exact SSID, router/access-point BSSID, centre coordinates, allowed radius and maximum GPS uncertainty. This is configured in the backend, not entered by staff on each check-in. Add a policy per access point when several BSSIDs serve the office. Do not enter the phone’s MAC or a Wi-Fi password.

1. Connect the phone to the configured Wi-Fi.
2. Enable location services and grant precise foreground location permission.
3. Choose **In office**, then tap **Verify & check in/out**.
4. The app obtains a current GPS fix and reads connected Wi-Fi SSID/BSSID. Missing identifiers or permissions block submission.
5. The server independently compares the submitted readings with an active policy and records evidence only for an accepted attendance action.

Both Wi-Fi and location must match. Default policy: 100 m radius, maximum 50 m uncertainty. The full GPS uncertainty circle must fit inside the configured radius; being near its edge may still fail. Wi-Fi matching is SSID case-sensitive and BSSID case-insensitive. Office mode is disabled in the app if the backend reports no active office; direct unverified API submissions are rejected as well.

All staff GPS readings must have finite valid coordinates, accuracy within 0.1–100 m inclusive, no reported mock location, and a timezone-aware capture time no older than two minutes (up to thirty seconds clock lead allowed). Office policies may impose a tighter uncertainty limit. The phone’s GPS attempt times out after thirty seconds; an unavailable reading never bypasses validation.

On iOS, the signed native app must include **Access Wi-Fi Information**, already configured in `app.json`, and meet permission requirements. Expo Go may not return SSID/BSSID. On Android, use the configured Wi-Fi/network/fine-location permissions and enabled location services. Test a real phone; an emulator, approximate location or hidden/redacted SSID is not proof of a supported office setup.

## Outdoor attendance: no photo required

Choose **Outdoor** and enter a **Place name** (up to 200 characters) and **Today’s work description** (up to 4000). Both must contain non-whitespace text. Describe the actual day’s work; the place is staff-entered text, not an automatically verified reverse-geocoded address. The independently captured coordinates are shown to management alongside it.

Tap **Verify & check in/out**. The app captures fresh GPS at submission time. Office Wi-Fi matching is not required in Outdoor mode. A camera/photo is not requested, uploaded, stored or used for verification. Both check-in and check-out need the location/place/work details; completed text can be reused or edited for checkout during the current app session.

The selected mode belongs to each attendance action. For example, checking in at the office and checking out at a client site creates Office and Outdoor evidence for the same work session. The five-minute attendance rules still apply.

## What is saved and who can see it

The server saves the session/action, mode, coordinates, GPS uncertainty and capture time. Office evidence includes the matched office and SSID/BSSID; Outdoor evidence includes place name and work description. The app displays the latest captured coordinates and today’s own evidence/activity. It does not continuously track the phone or request background location access.

Other employees cannot view your records. Management can view the submitted details in PL admin’s bell/activity screen, `/web/work-attendance/`, and Django Admin’s evidence view. The website/admin app can open the coordinates in an external map. No photo-verification data is collected.

These are device-reported Wi-Fi/GPS measurements, not tamper-proof identity or presence attestation. Known mock readings are rejected, but the system does not prevent all modified-client/radio/GPS spoofing.

## Personal toast notifications

An accepted check-in/out produces an immediate toast. While signed in and active, the app polls your personal notification feed every five seconds and also shows new events created by your fingerprint scans. Toasts are queued, can be dismissed, and disappear after roughly 4.5 seconds each. Your displayed attendance refreshes after a toast; the explicit Refresh attendance action remains available.

The notification ID prevents a local successful submission from being shown again when polling sees the same event. Cooldown attempts, failed validation, refreshes and stale actions do not create new notifications. Account sign-in/sign-out is separate from attendance check-in/out and does not publish attendance events.

Existing history is used as the initial cursor baseline rather than replayed as old toasts on a fresh launch. Background polling is paused; it resumes when active. There is no OS push notification service, so a closed app does not receive a push alert. Management retains the durable attendance event history.

## API and structure

All calls use `/api/mobile/` with session cookies and CSRF protection:

| Endpoint | Purpose |
| --- | --- |
| `auth/session/`, `auth/login/`, `auth/logout/` | Session bootstrap, sign-in and sign-out |
| `auth/password/` | Change the current user's password |
| `me/attendance/` | GET personal status/activity; POST an explicit login/logout action |
| `me/notifications/` | GET personal accepted attendance events with cursor polling |

Attendance identity comes from the logged-in account; clients cannot choose another employee. Cooldown responses keep the existing status and display the reason. Stale actions trigger a refresh so the next attempt reflects current server state.

The attendance POST is JSON and includes `action`, `mode` and `location`. Office adds `wifi_ssid`/`wifi_bssid`; Outdoor adds `place_name`/`work_description`. Action-only posts are no longer valid. GET/POST returns today’s sessions, `verification.office_configured`, the employee’s evidence and `notification_id` for an accepted submitted action. See [MOBILE_API.md](../main/MOBILE_API.md) for field-level examples and status codes. The app refuses sign-in against an older backend without verification support.

`src/app/index.tsx` contains the employee screen; `_layout.tsx` configures navigation. `src/api.ts` handles HTTP and authentication, while `src/attendance.ts` contains attendance types and feedback messages. See the [API contract](../main/MOBILE_API.md) for payloads and response codes.

`src/verification.ts` obtains one-shot GPS and connected Wi-Fi details; `src/notifications.tsx` handles personal polling, deduplication and the toast queue. There are no camera/photo dependencies in this flow. The configured application ID remains `com.attendance.staff`; its display name is **PL attendance**. `assets/pl-logo.jpg`, `pl-icon.png` and `pl-adaptive-icon.png` use the same artwork as PL admin. Launcher branding and native permission changes require a new installed build; Expo Go retains its own launcher identity.

## Checks

```powershell
npm test
npm run typecheck
npm run lint
npx expo export --platform android --output-dir dist
```

For signed installable binaries, configure your Expo/EAS project and signing credentials, then run `npx eas-cli@latest build --platform android` or `--platform ios`.

Use `npx --yes expo-doctor` for dependency compatibility checks and `npx expo export --platform android --platform ios` for both native bundles. Native modules/configuration must be present in the installed build; restarting Metro alone does not add iOS entitlements to an old binary.

## Troubleshooting and deployment

| Symptom | Resolution |
| --- | --- |
| Backend update required / 404 | Deploy backend API changes, apply migrations there, and restart its server |
| No employee profile linked | Administrator must create/link the employee to the signed-in user |
| Office mode disabled | Administrator must enable a valid Office location in Django Admin |
| Office Wi-Fi mismatch | Compare exact SSID and access-point BSSID; a phone MAC is not the BSSID |
| Wi-Fi details unavailable | Check permissions, actual Wi-Fi connection and location services; use an entitled iOS build |
| GPS stale/inaccurate/outside radius | Check device clock, precise location and reception; retry with a fresh location |
| 409 attendance changed | Refresh current state before retrying; another client may have changed the session |
| Five-minute cooldown | Wait for the required interval; repeated attempts do not create events |
| No toast while closed | In-app notifications do not provide closed-app push delivery |
| Cannot connect locally | Phone/computer on the same reachable network, correct LAN origin and accessible backend port |

Deploy backend and migrations first, configure real office policies, then rebuild/install the staff app and set its origin. Local code and migrations do not update the hosted backend automatically. Test Office success, incorrect Wi-Fi/GPS rejection, Outdoor success without pictures, both check-in/out, password changes and a fingerprint-originated personal toast on physical phones.

An exported bundle is not an APK/IPA. Physical-device networking, session cookies and the end-to-end attendance flow still require a smoke test against your backend. See the [repository overview](../README.md) for related components.
