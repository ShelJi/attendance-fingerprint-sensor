# PL attendance — personal staff app

The staff app includes the admin app’s personal attendance features: overview, profile and session history, monthly calendar with bottom refresh, reports and PDF sharing, Office/Outdoor activity with verification details, native phone notifications, saved login, password settings, 12-hour times, and device light/dark appearance. Office Wi-Fi/GPS verification and outdoor work descriptions remain available on Today.

Every personal data endpoint derives the employee from the authenticated user. Staff cannot choose another employee through query parameters, URLs, or notification registration. Calendar counts, totals, session history, PDF contents, GPS/work evidence and phone notifications contain only that employee’s records. Existing management accounts keep their admin access. Staff have no people-management, employee creation, device-control or office-configuration screens or API access.

## Run locally

```powershell
npm ci
# First setup only: copy .env.example to .env, then set your backend URL.
npx expo start --clear
```

Set `EXPO_PUBLIC_API_URL` in `staff-app/.env` to the Django server origin (no `/api/mobile/` suffix). On a phone, use the computer’s reachable Wi-Fi IP rather than localhost. The app embeds the URL during bundling and uses it for all backend requests without displaying it in Settings; old stored URL choices are ignored. Missing/invalid URLs fail app configuration. The root `.easignore` includes this public configuration file in cloud builds. CI builds must supply the same file or environment variable.

The configured HTTP URL is supported in installable builds as requested. HTTP sends credentials and attendance traffic without transport encryption. Rebuild to update the native network settings when changing between HTTP and HTTPS.

## Screens

- **Today:** your current status, today’s sessions, verified office/outdoor check-in/out, refresh and sign-out.
- **My profile:** your employee details, total worked time, date-filtered session history and pagination.
- **Calendar:** your attendance days, worked time, day details, month navigation and bottom Refresh preserving the selected date.
- **Reports:** your date-filtered work totals and daily breakdown, plus native PDF save/share.
- **Bell / activity:** your Office/Outdoor/device history, source/date filters, GPS/Wi-Fi/work evidence and map links.
- **Settings:** password changes and account details. Appearance follows the phone.

Your employee ID is your username. Initial password is `12345` unless the admin chose another password. Change it in Settings. Native login stores the opaque session credential in Expo SecureStore, never your password. Reopening the app or restarting the phone restores and verifies the saved session; sign-out or server expiry clears it. Password changes preserve the current login and update its rotated credential. Credentials are bound to the build-time server origin. Browser previews use HttpOnly cookies instead of localStorage credentials.

Attendance requires a linked employee account. Missing links are rejected. Office submissions require matching office Wi-Fi and GPS configured by the admin. Outdoor submissions require GPS, place name and work description. Existing five-minute attendance intervals remain enforced by the backend.

## Backend deployment and native notifications

Deploy this backend before distributing the updated staff app:

```powershell
python manage.py migrate
python manage.py send_attendance_push
```

Run one supervised push worker alongside Django; it serves both admin and personal staff subscriptions. Personal devices receive only their user’s events. Logout, session expiry/revocation, loss of the employee link, and invalid push tokens stop delivery. Submission retries and Expo receipts are tracked. Ambiguous network failures can cause duplicate notifications.

Use the staff app’s **own EAS project**, Firebase app `com.attendance.staff`, and iOS bundle `com.attendance.staff`. Initialize/configure that EAS project and set `EXPO_PUBLIC_EAS_PROJECT_ID` in the build environment (or `extra.eas.projectId` in app config). Do not reuse the admin app’s project ID or Firebase client configuration. For Android, provide its `google-services.json` via the EAS file variable `GOOGLE_SERVICES_JSON` and upload the FCM v1 server credential to EAS. Configure APNs credentials for iOS. See [Expo push setup](https://docs.expo.dev/push-notifications/push-notifications-setup/).

```powershell
npx eas-cli@latest build --profile preview --platform android
```

A new native binary is required for the added modules/configuration. Allow phone notifications and sign in once to register. Expo Go safely skips push registration; the rest of the app can be previewed there. Closed-app push requires the native build and configured provider credentials. PDF sharing and Wi-Fi/GPS verification need native device testing. OS restrictions and force-stop can prevent notifications.

## Personal API

All routes below require authentication; data routes require a linked employee. They accept no employee selector:

| Path under `/api/mobile/` | Purpose |
| --- | --- |
| `me/attendance/` | Today’s attendance and verified POST check-in/out |
| `me/profile/` | Own profile/session history with date filters and pagination |
| `me/calendar/` | Own month overview |
| `me/calendar/day/` | Own date details |
| `me/report/` | Own report and totals |
| `me/report/pdf/` | Own PDF export |
| `me/attendance/records/` | Own filtered activity/evidence |
| `me/notifications/` | Own durable event feed |
| `me/notifications/device/` | Register a personal push token |
| `auth/session/`, `auth/login/`, `auth/logout/`, `auth/password/` | Session and password management |

## Checks

```powershell
npm run lint
npm run typecheck
npm test
npx expo export --platform android
npx expo export --platform web
```

Backend privacy tests use two employees and check data, totals, PDF rows, notification recipients, forged employee selectors, missing employee links, and denial of management/legacy routes. Physical phone login restoration, Wi-Fi/GPS, PDF sharing and push delivery need end-to-end testing after rebuilding.


## Compact mobile sizing

`src/design.ts` defines the same 24/18/14/12 typography scale, 4/8px spacing grid, and component sizes as PL admin. Cards use 16px padding, fields/buttons retain 48px targets, and chips/icon buttons/calendar dates retain at least 44px targets. Page gutters adapt to phone width and safe areas. Navigation labels wrap in a bar that grows when necessary; native font scaling remains enabled. All staff screens were checked at 320–844px widths and with enlarged text using isolated fixtures. See [the sizing audit](../mobile-app/UI_REDESIGN.md).


## App sessions and notifications

App-recorded session cards use a teal background and an App badge; fingerprint-only cards remain neutral. Check-in location and Check-out location open Google Maps with the corresponding action’s stored GPS coordinates, without rounding. Buttons appear only when that action has saved app evidence. Staff can still see only their own records; admins retain their authorized management view.

Check-in and checkout notifications stay enabled in the app. The former preference is ignored, including for accounts that previously disabled it. Phone notification permission still applies.

Settings now has **Test notification**. It registers the current phone, sends an authenticated test through the backend/Expo push service, and listens for that test ID. **Sent** means Expo accepted it; **Received** means the app observed the notification. After 15 seconds without an observed receipt, the status stays Sent. Provider/network errors show Not sent or a short error. The listener is removed after success, failure or timeout. No attendance event is created by a test.

The test requires an installed native build with push credentials and permissions; Expo Go/browser previews show Use the installed app. The backend sends tests directly, so this button does not depend on the attendance worker. Regular attendance delivery still needs the worker. Restart Django and the worker after deploying this change. Staff verification rules are unchanged.

Calendar and reports support All, App logins, and Device logins filters. The check-in method determines the login source. Calendar day details show individual sessions and saved app check-in/checkout map links. PDF reports include login source counts and respect the selected filter.
