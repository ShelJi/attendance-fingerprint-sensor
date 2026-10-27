# Workplace attendance and notifications

PL attendance is the staff app; PL admin is the management app. Both use the
supplied PL logo. Photo verification is disabled: no camera permission, upload,
photo field, or photo requirement is part of this feature.

## Deployment and office setup

Run `python manage.py migrate` from `main/` when deploying. Migration 0006 creates
office configuration, verification evidence, and a durable notification log. It
backfills login/logout events for existing sessions without changing attendance
times. Those records appear as **Device / legacy** because no mobile Wi-Fi/GPS
evidence was captured. Existing fingerprint scan/cooldown calculations are reused.

In the web dashboard or PL admin, open **App configuration**. Select an office or choose **Add office**, use **Use current location** at the office centre (or enter coordinates manually), then save an active office with:

- Name, exact Wi-Fi SSID and router/access-point **BSSID** (not the phone MAC).
- Office latitude/longitude, allowed radius in metres, and maximum GPS uncertainty.
- Active enabled. Add one row per access point if the office has several BSSIDs.

Defaults are a 100 m radius and at most 50 m GPS uncertainty. The server requires
the reported uncertainty circle to fit inside the office radius. Office Wi-Fi
and GPS must both match an active configuration; missing configuration fails
closed. Staff cannot change office policies. Managers can update these settings
through App configuration; Django Admin also controls the same office records.
Wi-Fi passwords are not stored. Changes apply to future submissions; disable an old
configuration to keep its history. Browser GPS requires HTTPS or localhost.

The local database was backed up to an ignored `main/db-backup-*.sqlite3` file
before applying migrations. Deploy these changes and migrations to the hosted
backend separately; local migrations do not update the hosted database.

## Staff submission

Both check-in and check-out require fresh GPS (within two minutes, not reported
as mocked, with uncertainty within 0.1–100 m inclusive).

- **Office:** exact SSID/BSSID match plus the configured office GPS/radius checks.
- **Outdoor:** GPS, non-empty place name (up to 200 characters), and the day’s work
  description (up to 4000 characters). Wi-Fi matching and photos are not required.

Only the signed-in employee can submit or read their own evidence. Attendance
uses server time and retains the existing five-minute minimum/cooldown rules.
Rejected/cooldown submissions do not create evidence or notifications. GPS is
captured only when submitting; there is no background location tracking.

Payload for `POST /api/mobile/me/attendance/`:

```json
{
  "action": "login",
  "mode": "office",
  "wifi_ssid": "Office WiFi",
  "wifi_bssid": "aa:bb:cc:dd:ee:ff",
  "location": {
    "latitude": 10.0, "longitude": 76.0, "accuracy": 10,
    "captured_at": "2026-10-25T09:00:00+05:30", "mocked": false
  }
}
```

For outdoor mode supply `place_name` and `work_description` instead of Wi-Fi fields.
The coordinates above are an example, not a configured office. Actual office
coordinates and BSSIDs must be entered by the admin. The staff app rejects an old
backend that does not advertise verification support.

Wi-Fi identifiers and GPS readings are device-reported, not cryptographic proof
of presence. Known mock locations are rejected, but a modified client or spoofed
radio/GPS environment can still falsify device measurements. This implementation
does not include device attestation.

## Admin and web views

Tap the bell in PL admin to open **Attendance activity**. The web sidebar links
to `/web/work-attendance/`. Both provide separate **Office**, **Outdoor**, **All**,
and **Device / legacy** views, date filtering, and pagination. Rows show employee,
check-in/out time, source, coordinates, accuracy and capture time; office rows
include SSID/BSSID, and outdoor rows include place and work description. Mixed
sessions (office check-in, outdoor check-out) are classified per action.

Management JSON: `GET /api/mobile/attendance/records/` with optional `mode`,
`start_date`, `end_date`, and `page`. Dates default to the full current backend
month. Staff accounts receive 403. Responses are private and uncached.

## Notifications

Every accepted attendance login/logout creates exactly one durable event,
including fingerprint device scans. Normal refreshes and cooldown responses do
not duplicate it. The event is committed with its attendance transaction.

- `GET /api/mobile/me/notifications/`: signed-in employee’s events only.
- `GET /api/mobile/notifications/`: management feed for all employees.
- `?after=<id>` retrieves new events in ascending ID order, up to 100 at a time;
  follow `cursor` while `has_more` is true. The initial call returns the latest 20
  for a baseline and does not replay old records as toasts.

Staff sees a toast immediately on their own accepted submission and for their
new device events. Their displayed attendance refreshes after a toast. PL admin
receives queued foreground toasts for all employees. Both apps poll every five
seconds while active; the web dashboard polls every fifteen seconds. Toasts can
be dismissed. All history stays available to management in the workplace view.

These are **in-app toasts and persistent history**, not OS push notifications.
When the app is closed/backgrounded there is no push delivery; reconnecting
retains the durable history. No Expo push service credentials/tokens are used.

## Native setup and verification

The staff app uses Expo Location and NetInfo. It needs precise foreground
location permission and enabled location services. iOS requires a signed build
with Access Wi-Fi Information entitlement (configured in `staff-app/app.json`);
Expo Go may not expose SSID/BSSID. Missing readings show a clear error and never
bypass office checks. Rebuild the installed staff app for new permissions, logo,
and **PL attendance** launcher name.

Backend tests cover matching/mismatched Wi-Fi, geofence uncertainty, stale/mock/
invalid GPS, outdoor requirements without photos, personal/management access,
source filtering, cooldowns, durable notification deduplication and history backfill.
Native Wi-Fi permission behavior, GPS indoors, and toast delivery during actual
device scans need a physical-device smoke test. Builds/export checks produce
Metro/Hermes bundles, not signed APK/IPA files.
