# React Native API

Base URL: `/api/mobile/`. Existing `/api/` and `/web/` URLs are unchanged.
Mobile data views reuse the existing view calculations. Employee creation uses
the existing EmployeeForm validation. No model or attendance rules were changed.

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
| GET | `employees/` | `employee_data`: employees with last action, time, worked duration |
| POST | `employees/create/` | JSON name, employee_id, fingerprint_id; 201 employee or 400 errors |
| GET | `employees/<id>/` | employee, page_obj, total_worked; query start_date, end_date, page |
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
Dates and report defaults retain the existing web behavior.

The existing hardware JSON APIs remain at `/api/attendance/scan/`,
`/api/device/status/`, `/api/device/command/`, and `/api/device/command/result/`.
These serve device scanning, heartbeats, command polling and result submission;
the app controls the device using the authenticated mobile control endpoints.
