# Attendance Web Portal and Backend

Django application serving the browser management portal, mobile JSON APIs and fingerprint device HTTP APIs. It stores employees, linked login accounts, attendance sessions, device availability and queued sensor commands in SQLite by default.

## Features

- Employee creation and listing, individual attendance history, date filters and pagination.
- Dashboard with employee counts, today's attendance and active sessions.
- Monthly attendance calendar with daily detail.
- Attendance reports with worked durations and PDF export.
- Device online status, command submission and result polling.
- Automatic employee login accounts, session authentication and password changes through the API.
- Personal attendance API used by the separate staff app.
- Configurable office Wi-Fi/GPS policies and outdoor place/work evidence; photos are disabled.
- Separate Office/Outdoor/Device activity views and durable attendance notifications.

## Setup

Use Python 3.13 or newer. All commands below run from the **repository root**, not `main/`:

```powershell
uv sync
.venv/Scripts/python.exe main/manage.py migrate
.venv/Scripts/python.exe main/manage.py createsuperuser
.venv/Scripts/python.exe main/manage.py runserver 0.0.0.0:8000
```

Use `.venv/bin/python` on macOS/Linux. `uv sync` installs the dependencies declared in the root `pyproject.toml`. Database location: `main/db.sqlite3`. Project settings: `main/main/settings.py`. Application code: `main/attendance/`.

Back up existing data before migration. Migration `0005_employee_user` creates employee accounts; it is irreversible through Django's normal migration rollback. A username collision stops the migration without taking ownership of the existing account. Resolve the collision and retry.

Migration `0006_officelocation_attendancenotification_and_more` adds `OfficeLocation`, `AttendanceEvidence` and `AttendanceNotification`. It backfills notification events for existing login/logout timestamps; it does not invent GPS evidence or change historical attendance times. Historical events are classified as Device / legacy. Apply migrations on each deployed database, not only on your development machine, then restart the server process.

## How it works

Django is the shared source of employee accounts and attendance for the website, PL admin, PL attendance and the Pico. Browser pages under `/web/` return HTML; phone endpoints under `/api/mobile/` return JSON. Both mobile apps use Django session cookies and CSRF tokens. The Pico uses the hardware scan, heartbeat and command endpoints under `/api/`.

Creating an employee also creates a linked Django user with the employee ID as its username and `12345` as its default first-time password. The employee form accepts an optional custom password instead. The staff API identifies the employee from that signed-in user, verifies Office/Outdoor evidence, and calls the same attendance service as fingerprint scans. An accepted check-in opens a session; check-out closes it and records worked duration. Each accepted action creates a notification. Calendar and reports read these shared sessions rather than keeping a separate copy of attendance.

## How to use the backend

1. Start Django with the setup commands above and leave its terminal open. Run `createsuperuser` only when a new administrator is needed; reuse your existing account on later starts.
2. Open `http://127.0.0.1:8000/admin/` on the computer and sign in as the superuser.
3. Add an **Employee** with a name, employee ID and fingerprint ID. For example, `EMP-001` receives username `EMP-001` and initial password `12345` when Password is blank. Enter a custom password to override it. No separate user creation is needed.
4. Add the real active **Office location** before staff use Office attendance. Outdoor attendance needs GPS and work details but no office policy.
5. Configure both phone apps with `http://<computer-Wi-Fi-IP>:8000`. Visit `/api/mobile/auth/session/` at that address in the phone's browser: it must return JSON. A logged-out session is expected to return `authenticated: false`.
6. Use `/web/dashboard/`, `/web/employees/`, `/web/work-attendance/`, `/web/calendar/` and `/web/report/` for everyday management. Use `/admin/` for direct record/account changes.

| Django admin section | Use it for |
| --- | --- |
| Employees | Names, employee IDs, fingerprint IDs and linked accounts |
| Users / Groups | Login usernames, password resets, active status and permissions |
| Attendance sessions | Check-in/out timestamps and saved worked durations |
| Attendance devices / Device commands | Device activation and queued command records |
| Office locations | Office Wi-Fi/GPS policies |
| Attendance evidence / Attendance notifications | Submitted verification and attendance event records |

Automatic creation of notification rows runs when a session is saved, but editing historical session timestamps does not rewrite existing notification timestamps or automatically recalculate worked duration. When correcting records manually, check all affected values. For normal sensor operations, issue commands through PL admin or `/web/device/control/`.

Local operation requires no hosted backend. Use `ipconfig` to find the computer's Wi-Fi IP; `127.0.0.1` is only for clients on that same computer. Stop Django with Ctrl+C. Restart it after backend changes when running with `--noreload`.

## Website routes

| URL | Purpose |
| --- | --- |
| `/login/` | Browser sign-in |
| `/logout/` | Browser sign-out via POST |
| `/web/dashboard/` | Attendance overview |
| `/web/employees/` | Employee list |
| `/web/employees/create/` | Create an employee |
| `/web/employees/<id>/` | Individual attendance history |
| `/web/device/control/` | Fingerprint device controls |
| `/web/calendar/` | Monthly attendance |
| `/web/report/` | Attendance report |
| `/web/report/pdf/` | PDF report |
| `/web/work-attendance/` | Separate Office, Outdoor, All and Device / legacy activity with verification details |
| `/admin/` | Django administration |

Open [login](http://127.0.0.1:8000/login/) to begin. Equivalent legacy attendance routes exist under `/api/`; these management views return HTML, while `/api/mobile/` provides JSON. `/` has no configured homepage. Successful browser login currently redirects to `/api/employees/`.

## Accounts and permissions

Each employee has a linked Django user. When created without an explicitly linked user, their unique `employee_id` becomes the username and the initial password defaults to `12345`. Employee display names are not used for login. The Password field on employee creation/admin forms sets the linked user's hashed password; it is not a separate plaintext database column and is never returned in employee API responses. Custom passwords other than the explicitly allowed initial `12345` use Django's password validation. Employees' own password changes always use Django's normal validation.

On the employee edit form, leave Password blank to preserve it or enter a new password to reset it. No existing password is shown. Editing other details does not reset the password or rename the login account. Existing Django user passwords, including older employee-ID defaults, are unchanged until explicitly reset.

Managers can create employees through the website or management API. Django admin also creates the login account automatically: enter the name, employee ID and fingerprint ID. A conflicting username is shown as a form error. Programmatic creation with `Employee.objects.create()` provisions an account automatically; `bulk_create()` bypasses this behavior.

Superusers can manage every attendance model at `/admin/`, including evidence and notifications. Edit employee details under **Employees**; edit usernames, account status, permissions and passwords under **Users**. Changing an employee ID keeps the existing username and password; change the username explicitly under **Users** when needed. Django's relationship protection still prevents deleting records referenced by attendance evidence.

Management views and mobile management APIs allow Django staff/superusers and existing accounts without employee profiles. Ordinary employee accounts can use authentication, password changes and their own attendance API. A management account needs a linked employee profile to register personal attendance. Deleting an employee deactivates their linked account unless it has staff/superuser privileges.

The staff app and the management app's Settings screen provide password changes. There is no separate browser portal password-change screen.

### Set or reset an employee password

1. Sign in to Django Admin and open **Employees**.
2. When adding an employee, leave **Password** blank for initial password `12345`, or supply a custom password. Their username is the employee ID.
3. To reset an existing employee's password, open their record, enter the replacement in **Password**, and save. Leave that field blank when only changing profile details.
4. Give the employee their username and initial/reset password. They sign in to PL attendance, open **Change password**, enter the current password and the new password twice, then save.

Only a superuser can reset a privileged staff/superuser account through this employee form. Existing passwords cannot be viewed or recovered from the form. Updating the application does not reset any existing accounts, and no database migration is needed for this password-field change.

## API overview

The complete mobile contract is in [MOBILE_API.md](MOBILE_API.md).

| Method | Endpoint | Access / purpose |
| --- | --- | --- |
| GET | `/api/mobile/auth/session/` | Get authentication status and CSRF token |
| POST | `/api/mobile/auth/login/` | Sign in with username/password |
| POST | `/api/mobile/auth/logout/` | End the current session |
| POST | `/api/mobile/auth/password/` | Change the signed-in user's password |
| GET, POST | `/api/mobile/me/attendance/` | Read or register the signed-in employee's attendance |
| GET | `/api/mobile/employees/`, `/api/mobile/dashboard/` | Management data |
| POST | `/api/attendance/scan/` | Hardware fingerprint scan |
| POST | `/api/device/status/` | Hardware heartbeat |
| GET | `/api/device/command/` | Hardware command polling |
| POST | `/api/device/command/result/` | Hardware command result |

Mobile authentication uses cookies and CSRF tokens. Bootstrap with `auth/session/`, retain cookies, send `X-CSRFToken` on POSTs and use the new token returned after login. Password changes require `old_password`, `new_password1` and `new_password2`; Django validates the replacement password and preserves the current session.

Personal attendance now accepts an explicit `action` (`login` or `logout`), a `mode` (`office` or `outdoor`), and fresh GPS evidence. Office requires Wi-Fi identifiers; Outdoor requires place/work details. An action-only POST is rejected. Employee identity and attendance timestamps come from the authenticated session and server. Fingerprint scans resolve employees using their stored `fingerprint_id` and retain their existing hardware workflow.

## Configure office policies

Sign in as a manager and open **Dashboard → App configuration** at `/web/configuration/`, or **Overview → App configuration** in PL admin. Select an existing office or choose **Add office**. Stand at the office centre and tap **Use current location**, allow location access, then review the coordinates. Manual coordinates also work. Enter the Wi-Fi identifiers and limits below, enable Active, and save. Django administrators can also edit these records in `/admin/` → **Office locations**.

| Field | Meaning / allowed values |
| --- | --- |
| Name / Active | Label and whether this configuration may accept office attendance |
| Wi-Fi SSID | Exact network name; at most 32 characters; matching is case-sensitive |
| Wi-Fi BSSID | Access-point MAC such as `AA:BB:CC:DD:EE:FF`; matching is case-insensitive; not the employee phone MAC |
| Latitude / Longitude | Real office centre, within -90…90 / -180…180 |
| Radius metres | 10–1000 m; defaults to 100 m |
| Max accuracy metres | 1–100 m; defaults to 50 m |

Add a row per access-point BSSID for offices with multiple radios/access points. Wi-Fi passwords are neither required nor stored. Saved changes apply to the next staff office attendance submission. Disable an old configuration to retain its history. Browser location capture requires HTTPS or localhost; on a phone connected to the local backend, use native PL admin or enter coordinates manually.

Office submissions must match an active SSID/BSSID and satisfy both `accuracy <= max_accuracy_meters` and `distance_from_office + accuracy <= radius_meters`. A reported point inside the circle can still fail if its uncertainty extends outside. No active/matching office means rejection, not a fallback acceptance.

Both modes require numeric, finite GPS coordinates and accuracy within 0.1–100 m inclusive. Location capture must be timezone-aware, no older than two minutes and no more than thirty seconds in the future. Reported mock locations are rejected. Outdoor additionally requires a trimmed non-empty place name (maximum 200 characters) and work description (maximum 4000). No photo fields or upload API are used. See [payload examples and the full contract](WORKPLACE_ATTENDANCE.md).

Evidence records store the employee session/action, mode, coordinates, accuracy and capture time; Office adds office/SSID/BSSID, Outdoor adds place/work details. Staff sees only its own evidence; management can view all in `/web/work-attendance/`, PL admin’s bell/activity view, or **Attendance evidence** in Django Admin. Evidence is read-only for ordinary administrators; superusers can add, edit and delete it. References protect verified sessions and office policies from deletion; employee deletion may therefore be refused when protected history exists. Deactivate an old office policy rather than removing audit history.

## Office/outdoor views and date defaults

The new workplace page shows one row per check-in/out action, not one row per employee. Its Office/Outdoor/Device counts are **event counts** for the date range; they are not employee counts or worked-hour totals. Mode selection filters rows while totals retain all modes for that date range. The page/API returns 50 events per page, newest attendance time first. An Office check-in and Outdoor check-out in the same session appear in their respective views.

Each row includes employee name/ID, action, attendance time, session and source. Verified rows add coordinates/map link, GPS uncertainty and capture time. Office rows include office name and Wi-Fi identifiers; Outdoor rows include place and work description. Device / legacy rows explicitly have no mobile evidence. The new workplace view defaults to the first through the last day of the current server month.

PL admin’s Reports screen also starts with a full-month explicit filter and uses that selected range for PDF export. The original web report and direct `report/` / `report/pdf/` API defaults remain month-start through today when dates are omitted. The workplace activity view and worked-duration report are separate views of the same sessions.

## Notifications and delivery

An accepted attendance check-in/out creates one `AttendanceNotification` per session/action. Signals cover the staff flow and fingerprint scans; the scan service runs in a transaction so a failed notification write rolls back that scan. Cooldowns and refreshes create no new event. Migration 0006 backfills older sessions, and unique constraints prevent duplicates.

| Endpoint | Access / result |
| --- | --- |
| `GET /api/mobile/me/notifications/` | Authenticated account’s employee events only |
| `GET /api/mobile/notifications/` | Management feed across all employees |
| `GET /api/mobile/attendance/records/` | Management records with detailed Office/Outdoor evidence, mode/date/page filters |

The first feed request returns up to 20 recent events in ascending ID order and a cursor. It establishes the UI baseline without replaying old toasts. `?after=<cursor>` returns up to 100 newer events; use the returned cursor and continue while `has_more` is true. Management records and successful feed responses use `Cache-Control: private, no-store`.

Staff sees immediate accepted-action toasts and polls for its own device events; its attendance status refreshes after a toast. PL admin polls every five seconds while active, and management web pages poll every fifteen seconds while visible. Toasts are queued and dismissible. Rejected attempts and account sign-in/sign-out are not attendance notifications.

No OS push provider, push tokens or closed-app delivery is configured. History remains in the database; a fresh app launch does not replay it as toasts. There is no automatic event-retention expiry policy; deleting a session also deletes its notification rows where evidence protection permits that deletion.

## Attendance and device behavior

The first scan/check-in of a day opens a session. Check-out is allowed after five minutes; another check-in requires five minutes after the previous check-out. Earlier attempts return a cooldown action without changing attendance. A stale explicit action from the staff app returns HTTP 409. Staff submissions and hardware scans use the same `process_scan()` service.

Attendance is grouped by login date in `Asia/Kolkata`; an open session from a prior day is not automatically closed by the current-day lookup. Worked duration is recorded on check-out. Device status is considered online when its last heartbeat is less than two minutes old.

Supported sensor commands: `LIST_IDS`, `ENROLL`, `ENROLL_AUTO`, `DELETE`, `REPLACE`, `VERIFY`, `SUMMARY` and `INFO`. A running, compatible device must poll commands and submit results; creating a command alone does not execute it.

## Checks and manual device testing

From the repository root:

```powershell
.venv/Scripts/python.exe main/manage.py check
.venv/Scripts/python.exe main/manage.py test attendance --noinput
.venv/Scripts/python.exe main/manage.py makemigrations --check --dry-run
```

With the local backend running, these scripts make actual hardware API requests:

```powershell
.venv/Scripts/python.exe testing/pico_status.py
.venv/Scripts/python.exe testing/pico_simulator.py
.venv/Scripts/python.exe testing/device_commands.py
```

The scripts default to `http://127.0.0.1:8000` and device ID `attendance-01`. The scan simulator prompts for a fingerprint ID, which must match an employee. Scan and heartbeat requests change database state; command polling can consume queued work.

## Configuration and limits

The current settings use development values (`DEBUG=True`, wildcard hosts and a checked-in development secret). Configure a private secret, explicit hosts, HTTPS, secure cookies, static-file serving and a suitable application server for deployment. The hardware endpoints currently use neither session authentication nor a device API key; restrict their network access appropriately. No MQTT consumer is included in this Django project.

For deployment: back up data, deploy backend code, run migrations, restart the application server, configure Office locations, then point both apps at the origin and rebuild native apps where required. Local database migrations do not update `https://s.plsofttech.com`. No hosting credentials or automatic deployment workflow are supplied.

Wi-Fi identifiers/GPS are client-reported, not cryptographic presence proof; there is no device attestation. GPS collection is submission-time only, with no background tracking. iOS SSID/BSSID retrieval requires the staff app’s configured Wi-Fi entitlement in a signed native build; permissions and real hardware behavior must be verified on a phone.

Troubleshooting: a mobile route returning 404 usually means missing deployment; missing-table errors require migrations; HTTP 401 requires sign-in; HTTP 403 can indicate management access or CSRF failure; a location/Wi-Fi HTTP 400 should be resolved from the response message. Use an active office and accurate GPS rather than loosening checks to bypass a failed verification.

Related applications: [management app](../mobile-app/README.md), [staff app](../staff-app/README.md), [Pico firmware](../pico/README.md).
