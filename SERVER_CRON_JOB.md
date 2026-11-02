# Attendance notification cron job on cPanel

Cron is the server's scheduler. A cron job tells it to run a command at a fixed interval, such as every minute. It does not require keeping cPanel Terminal open.

`send_attendance_push` is a Django management command, implemented in [send_attendance_push.py](main/attendance/management/commands/send_attendance_push.py). It is not a service file. It checks pending attendance events, submits alerts to Expo, checks delivery receipts, and removes invalid registrations. Failed submissions are retried; ambiguous network failures can produce duplicate alerts.

| Mode | Behavior | Use |
| --- | --- | --- |
| `python manage.py send_attendance_push` | Keeps checking every five seconds | One supervised continuous worker |
| `python manage.py send_attendance_push --once` | Processes one pass, then exits | Scheduled cPanel cron job |

Use one delivery mechanism. Do not also run a continuous worker when using this cron job. One worker handles both admin and staff subscriptions.

## 1. Check the deployed app

The following paths match the server used during setup. Replace them if the hosting account, app folder or Python version changes:

| Item | Path |
| --- | --- |
| Folder containing `manage.py` | `/home/ybtzxyhi/s.plsofttech.com/attendance` |
| Virtual environment Python | `/home/ybtzxyhi/virtualenv/s.plsofttech.com/attendance/3.13/bin/python` |
| Lock file | `/home/ybtzxyhi/attendance-push.lock` |
| Output/error log | `/home/ybtzxyhi/attendance-push.log` |

Back up your deployed database before applying migrations. In cPanel Terminal:

```bash
cd /home/ybtzxyhi/s.plsofttech.com/attendance
/home/ybtzxyhi/virtualenv/s.plsofttech.com/attendance/3.13/bin/python manage.py migrate
/home/ybtzxyhi/virtualenv/s.plsofttech.com/attendance/3.13/bin/python manage.py send_attendance_push --once
```

No output can be normal. The command does not print a success message for every pass. If `manage.py` cannot be found, locate it and correct the working directory:

```bash
find /home/ybtzxyhi/s.plsofttech.com -name manage.py -type f 2>/dev/null
```

Cron must use the same database configuration and required environment variables as the web app. It does not inherit your interactive terminal or necessarily the environment set in cPanel's Python application screen. This includes `EXPO_ACCESS_TOKEN` if Expo push security is enabled. Supply required variables through your hosting environment or a private wrapper script; do not put secrets in a public directory.

## 2. Check the locking tool

```bash
command -v flock
```

The command below assumes `/usr/bin/flock`. If your output differs, use the returned absolute path. If unavailable, ask the host for its supported locking mechanism before enabling the schedule.

## 3. Add the cron job

Open **cPanel → Advanced → Cron Jobs**. For every minute, enter:

| Field | Value |
| --- | --- |
| Minute | `*` |
| Hour | `*` |
| Day | `*` |
| Month | `*` |
| Weekday | `*` |

Paste this single line into **Command**; the schedule fields are separate:

```bash
(cd /home/ybtzxyhi/s.plsofttech.com/attendance && /usr/bin/flock -n /home/ybtzxyhi/attendance-push.lock /home/ybtzxyhi/virtualenv/s.plsofttech.com/attendance/3.13/bin/python manage.py send_attendance_push --once) >> /home/ybtzxyhi/attendance-push.log 2>&1
```

Click **Add New Cron Job** once. Confirm there is only one entry for this command. Follow your hosting provider's minimum interval; if five minutes is the minimum, set Minute to `*/5` and leave the other fields `*`. See [cPanel Cron Jobs documentation](https://docs.cpanel.net/cpanel/advanced/cron-jobs/).

The command changes to the app folder, obtains a nonblocking lock, uses the app's virtual environment Python, processes one pass, then exits. Output and errors append to the log. If a previous pass is still running, the lock causes the next run to skip. Outer parentheses also capture working-directory errors in the log.

Do not remove `--once`: otherwise every scheduled execution could start another persistent worker. Keep the lock file in place; its existence does not mean a worker is still running.

## 4. Understand the two empty files

| File | Why it can be empty |
| --- | --- |
| `attendance-push.lock` | The OS tracks the lock; no file contents are required |
| `attendance-push.log` | The worker is normally silent; output appears when something logs or fails |

These files appearing suggest the command started, but do not prove the schedule runs every minute or that a phone received an alert. Inspect errors with:

```bash
tail -n 50 /home/ybtzxyhi/attendance-push.log
```

Monitor log size and use your host's log rotation facilities if it grows.

## 5. Test with real examples

**Case A: an employee checks in at 9:00:20.** Django saves the event. If cron runs at 9:01, that pass submits it through Expo. The phone receives it after provider delivery, subject to permissions and network. One-minute cron is not instant push; a five-minute schedule adds up to roughly five minutes before processing, and backlog or a busy worker can add more delay.

**Case B: no attendance occurs overnight.** Cron still checks, finds nothing new and exits. Both files can remain empty. That alone is not an error.

**Case C: Test notification works, but attendance alerts do not.** The Settings test sends directly from Django and bypasses this worker. Check the cron schedule, paths, environment, registered sessions and log, then create a new accepted attendance event after phone registration.

**Case D: the previous pass takes more than one minute.** The next scheduled execution skips because the lock is held. Pending work stays for a later pass; do not add a second cron entry to compensate.

To test, first complete [Firebase setup](FIREBASE_SETUP.md), install the rebuilt APK, sign in and grant notification permission. Create a new accepted attendance event after registration, respecting attendance cooldowns. Existing events are skipped on first registration. Admin receives management events; staff receives only its user's events. Sign-out or expired sessions stop delivery.

## Troubleshooting and stopping

| Symptom | Action |
| --- | --- |
| Cannot open `manage.py` | Correct the `cd` path to its containing folder |
| Python not found / Django missing | Use the deployed virtual environment's absolute Python path |
| `/usr/bin/flock` not found | Check `command -v flock` and use the correct supported path |
| Missing-table errors | Back up and run deployed migrations against the same database as the web app |
| Works in Terminal, fails in cron | Compare database settings, environment variables, permissions and absolute paths |
| Provider rejects notifications | Check log errors and the app's matching Firebase/EAS credentials |
| Nothing on phone, log empty | Confirm rebuilt app, permission, signed-in registration, new event and cron execution; silence alone does not prove delivery |

To stop future scheduled runs, delete or disable this entry in **Current Cron Jobs**. An already-running pass can finish. No separate service file is needed for this cron setup.
