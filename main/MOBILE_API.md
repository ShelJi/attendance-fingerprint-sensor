# React Native API

Workplace verification, admin Office/Outdoor views, and personal/management notification
feeds are documented in [WORKPLACE_ATTENDANCE.md](WORKPLACE_ATTENDANCE.md).
Staff attendance POST requests now require `mode` and a fresh `location` object,
plus office Wi-Fi identifiers or outdoor place/work details. Photos are disabled.

Base URL: `/api/mobile/`. Existing `/api/` and `/web/` URLs are unchanged.
Mobile data views reuse the existing calculations and EmployeeForm validation.
Workplace evidence and notification models are additive; the existing scan and
five-minute cooldown calculations are reused.

## Authentication

Use HTTPS and retain cookies between requests in the mobile HTTP client.

1. GET `auth/session/` to obtain `csrf_token` and the CSRF cookie.
2. POST `auth/login/` with JSON `{"username":"...","password":"..."}`
   and header `X-CSRFToken: <csrf_token>`.
3. Keep the session cookie and use the **new** CSRF token returned by login
   for subsequent POST requests.
4. POST `auth/logout/` with that token to end the session.

Protected endpoints return JSON 401 when signed out. CSRF failures use Django's
existing 403 response. No CORS configuration is needed for a native mobile client.

## Endpoints

| Method | Path | Response / input |
| --- | --- | --- |
| GET | `auth/session/` | `{authenticated, username, csrf_token}`; available before sign-in |
| POST | `auth/login/` | JSON username/password; returns username and rotated csrf_token |
| POST | `auth/logout/` | Sign out; retain CSRF protection |
| POST | `auth/password/` | old_password, new_password1, new_password2; returns success and new csrf_token |
| GET, POST | `me/attendance/` | Personal status/evidence or verified Office/Outdoor attendance submission |
| GET | `me/notifications/` | Personal attendance events; optional after cursor |
| GET | `notifications/` | Management-only event feed across all employees; optional after cursor |
| GET | `attendance/records/` | Management records with evidence; mode, start_date, end_date, page |
| GET | `employees/` | `employee_data`: employees with last action, time, worked duration |
| POST | `employees/create/` | JSON name, employee_id, fingerprint_id; 201 employee or 400 errors |
| GET | `employees/<id>/` | employee, page_obj, total_worked; query start_date, end_date, page |
| GET, POST | `configuration/offices/` | Management-only: list offices or create office configuration |
| GET, POST | `configuration/offices/<id>/` | Management-only: read or update an office |
| GET | `dashboard/` | device, total_employees, today_sessions, active_sessions |
| GET | `device/control/` | device including is_online |
| POST | `device/control/command/` | Existing JSON command and optional fingerprint_id; queues command |
| GET | `device/control/result/` | Query command_id; existing status/result response |
| GET | `calendar/` | Query year, month; calendar_days is a JSON array |
| GET | `calendar/day/` | Query date=YYYY-MM-DD; existing daily attendance response |
| GET | `report/` | Query start_date, end_date; report_data, totals |
| GET | `report/pdf/` | Same date filters; application/pdf download |

Dates and times are ISO strings; durations use ISO 8601 duration strings.
page_obj contains results, page, pages, count, has_next, has_previous.
Direct `report/` and `report/pdf/` calls without dates retain the web default
of month-start through today. PL admin’s Reports screen supplies explicit dates
for the first through the last day of the current month on initial load. Workplace
`attendance/records/` independently defaults to a full current server month.

The existing hardware JSON APIs remain at `/api/attendance/scan/`,
`/api/device/status/`, `/api/device/command/`, and `/api/device/command/result/`.
These serve device scanning, heartbeats, command polling and result submission;
the app controls the device using the authenticated mobile control endpoints.
## Employee authentication and self attendance

New employee accounts use their unique employee ID as username and `12345` as the default initial password. `POST employees/create/` accepts optional `password` alongside `name`, `employee_id` and `fingerprint_id`; missing/blank password uses `12345`. A supplied custom password is validated and hashed in the linked Django user account, never included in the employee response. Existing Django account passwords are unchanged; historical migration `0005_employee_user` used employee IDs as initial passwords and is not rewritten. Login/session/logout endpoints work for all active accounts.

All paths below are relative to `/api/mobile/`. Use session cookies; fetch `auth/session/` first and send its `csrf_token` as `X-CSRFToken` for POST requests. Login rotates that token, so use the token returned by login thereafter.

* `POST auth/password/`: `{"old_password":"...","new_password1":"...","new_password2":"..."}`. Uses Django password validation, returns `{success, csrf_token}` and keeps the current session signed in. Validation errors return HTTP 400 with `errors`.
* `GET me/attendance/`: returns `{employee, username, checked_in, sessions, action, notification_id, verification, evidence}` for today's attendance in the server timezone. `verification.office_configured` indicates whether any active office policy exists. Evidence belongs only to the signed-in employee.
* `POST me/attendance/`: requires an explicit `action` plus mode-specific verification; see examples below. Employee identity and attendance timestamps come from the authenticated account and server. The result in `action` is `login`, `logout`, `already_logged_in` or `already_done`. The latter two are HTTP 200 cooldown responses and must not be displayed as newly recorded attendance. A newly accepted action returns its `notification_id`; a GET or cooldown response returns null. Stale actions return HTTP 409; refresh before retrying.

Staff accounts linked to employees cannot access management APIs or management web views unless granted Django staff/superuser privileges. Existing management accounts without employee profiles retain management access. Self attendance requires a linked employee profile (HTTP 403 otherwise). Anonymous API requests return HTTP 401; POST requests retain CSRF protection.

The separate employee client is in `staff-app/`.

## Verified attendance JSON

Example Office check-in (replace example time/coordinates/network with the current device reading):

```json
{
  "action": "login",
  "mode": "office",
  "wifi_ssid": "Office WiFi",
  "wifi_bssid": "aa:bb:cc:dd:ee:ff",
  "location": {
    "latitude": 10.0,
    "longitude": 76.0,
    "accuracy": 10,
    "captured_at": "2026-10-25T09:00:00+05:30",
    "mocked": false
  }
}
```

Example Outdoor check-out:

```json
{
  "action": "logout",
  "mode": "outdoor",
  "place_name": "Client site, Kochi",
  "work_description": "Completed installation and trained the client team.",
  "location": {
    "latitude": 10.0,
    "longitude": 76.0,
    "accuracy": 10,
    "captured_at": "2026-10-25T17:00:00+05:30",
    "mocked": false
  }
}
```

These timestamps are examples and will fail freshness checks when reused later.
Both actions require the same mode-specific fields. Action-only posts are rejected.
No photo, multipart upload or Wi-Fi password is used.

| Field | Server validation |
| --- | --- |
| action | login or logout; must match the current session state |
| mode | office or outdoor |
| location.latitude / longitude | Finite numeric values within -90…90 / -180…180; booleans rejected |
| location.accuracy | Numeric metres, 0.1–100 inclusive |
| location.captured_at | Timezone-aware ISO time, at most two minutes old / thirty seconds ahead |
| location.mocked | Must be the boolean false |
| wifi_ssid / wifi_bssid | Office only: exact active-policy SSID and case-insensitive BSSID match |
| place_name | Outdoor only: non-empty after trimming, at most 200 characters |
| work_description | Outdoor only: non-empty after trimming, at most 4000 characters |

An Office policy further requires `accuracy <= max_accuracy_meters` and
`distance_to_office + accuracy <= radius_meters`. The backend rejects missing or
mismatched Wi-Fi/GPS rather than trusting an app-side accepted flag. Known mock
readings are rejected, but this is not cryptographic device attestation.

Evidence returned by the personal endpoint contains id, session_id, action, mode,
coordinates, accuracy_meters, place_name and work_description. Management’s detailed
record endpoint additionally provides office, Wi-Fi identifiers and captured_at.

## Management workplace records

`GET attendance/records/?mode=office&start_date=2026-10-01&end_date=2026-10-31&page=1`

Omit `mode` (or use an empty value) for all sources. Accepted non-empty modes are
`office`, `outdoor`, `device`; the literal value `all` is not accepted. Omitted
dates default to the full current month in the backend timezone. Reversed or
invalid dates/modes return HTTP 400. The result includes:

- `records`: action rows, newest attendance time first, up to 50 per page.
- `page`, `pages`, `count`, `has_next`, `has_previous`: pagination of selected rows.
- `mode`, `start_date`, `end_date`: applied selection.
- `totals`: Office/Outdoor/Device event counts for the date range before the mode filter.

Each row has id, employee_id (employee database primary key), employee_code,
name, session_id, action, occurred_at, mode and verification. The verification
object contains office, latitude, longitude, accuracy_meters, captured_at,
wifi_ssid, wifi_bssid, place_name and work_description. For Device / legacy,
verification is null. Classification is per action, so a mixed-mode session can
appear once in Office and once in Outdoor. Counts measure events, not employees.

## Notification feeds and cursors

Management uses `GET notifications/`; staff uses `GET me/notifications/`.
Successful responses are private and uncached:

```json
{
  "notifications": [
    {"id": 42, "employee_id": 1, "employee_code": "EMP-001", "name": "Example Employee", "session_id": 7, "action": "login", "occurred_at": "2026-10-25T09:00:00+05:30", "mode": "office"}
  ],
  "cursor": 42,
  "has_more": false
}
```

Without `after`, up to 20 recent events establish a baseline; clients do not
replay them as old toasts. `?after=42` returns newer IDs in ascending order, up to
100. Continue with the response cursor while has_more is true. `?after=0` can
traverse history from its beginning; invalid/negative cursors return HTTP 400.
Neither polling nor reading a feed marks attendance or generates another event.

One event is written for each accepted check-in/out, including fingerprint scans.
Cooldowns, validation failures, refreshes and account sign-in/out are excluded.
Apps poll every five seconds while active; web pages every fifteen seconds while
visible. There is no OS push delivery while closed. Staff is scoped by the logged-in
account; it cannot select another employee through a query parameter.

## Errors and access

| Status | Meaning |
| --- | --- |
| 200 | Successful read/write; inspect attendance action to distinguish cooldowns |
| 201 | Employee created |
| 400 | Invalid JSON/form fields, evidence, filters or cursor; read error/errors |
| 401 | Authentication required / invalid credentials |
| 403 | Insufficient management access, no linked employee profile, or CSRF rejection |
| 404 | Missing resource, or deployed server lacks the endpoint |
| 405 | Method not allowed |
| 409 | Stale attendance action or an existing conflicting device command |

Most application errors use JSON error/errors. Django’s default CSRF and
method decorators can return HTML; clients must handle a non-JSON error response.
Native mobile requests do not need browser CORS, but production browser clients
still require appropriate origin/cookie/CSRF configuration. Never embed account
passwords, Wi-Fi passwords or other secrets in EXPO_PUBLIC environment variables.

## Office app configuration

Managers can GET `configuration/offices/` for `{offices: [...]}` or GET
`configuration/offices/<id>/` for `{office: {...}}`. POST to the collection creates
an office (201); POST to its ID updates it (200). Both return `{office: {...}}`.
Send all form fields on create/update with the session cookie and CSRF token:

```json
{
  "name": "Main office",
  "is_active": true,
  "wifi_ssid": "Office Wi-Fi",
  "wifi_bssid": "AA:BB:CC:DD:EE:FF",
  "latitude": 10.25,
  "longitude": 76.5,
  "radius_meters": 100,
  "max_accuracy_meters": 50
}
```

Use actual office coordinates and network identifiers. Latitude must be -90–90,
longitude -180–180, radius 10–1000 m, and maximum uncertainty 1–100 m. SSID is
case-sensitive (maximum 32 characters); BSSID must be an access-point MAC and is
normalized to lowercase. Invalid fields return 400 with `{errors: {...}}`;
unknown IDs return 404. Staff accounts receive 403, signed-out requests 401.
No Wi-Fi password is accepted or stored by this form. Saved changes are used by
the next staff office attendance submission. Set `is_active` to false to disable
an office without deleting historical evidence.
