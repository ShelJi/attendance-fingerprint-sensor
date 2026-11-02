# Firebase notifications setup

Use this guide for Android push notifications in **PL admin** and **PL attendance**. Firebase Cloud Messaging (FCM) delivers alerts to the phone; attendance data stays in Django. FCM is a no-cost Firebase product; app builds and server hosting have separate quotas or charges. See [Firebase pricing](https://firebase.google.com/pricing).

## Example: an employee checks in

1. An employee scans their fingerprint or checks in through PL attendance.
2. Django saves the attendance and a notification event.
3. The [server worker or cron job](SERVER_CRON_JOB.md) finds the event and sends it to Expo.
4. Expo uses FCM to deliver the Android notification.
5. PL admin receives the management alert; a registered staff phone receives only its own user's events.

Firebase configuration and the server worker are both required for regular Android attendance push. A closed app can receive push, subject to notification permissions, network and OS restrictions; force-stop can prevent delivery.

## 1. Prepare each app separately

| App | Folder | Android package | EAS project ID |
| --- | --- | --- | --- |
| PL admin | `mobile-app` | `com.shelj.myapp` | `08f807fa-2804-4fe9-ad0f-4e0ed751432e` |
| PL attendance | `staff-app` | `com.attendance.staff` | `6a776c40-ca46-4054-8dcf-dce9a37c940c` |

Run these commands in PowerShell for admin:

```powershell
cd D:\github\attendance-fingerprint-sensor\mobile-app
npm ci
```

For staff, run them in its own folder too:

```powershell
cd D:\github\attendance-fingerprint-sensor\staff-app
npm ci
```

Each folder needs its own installed dependencies. Installing admin dependencies does not install staff dependencies. Wait for `npm ci` to finish successfully before running EAS.

Create `.env` from `.env.example` only if it does not already exist. In each app's `.env`, set:

```dotenv
EXPO_PUBLIC_API_URL=https://s.plsofttech.com
GOOGLE_SERVICES_JSON=./google-services.json
```

Both app configs already map `GOOGLE_SERVICES_JSON` to Android's `googleServicesFile`. These are public build settings. Never place private service account key contents in `.env` or an `EXPO_PUBLIC_*` variable.

## 2. Register Android apps in Firebase

Open the [Firebase Console](https://console.firebase.google.com/), create a project such as `PL Attendance`, and keep the free Spark plan for FCM. Google Analytics is optional for this setup.

Add an Android app with package `com.shelj.myapp`, nickname `PL admin`. Download its `google-services.json` into:

```text
D:\github\attendance-fingerprint-sensor\mobile-app\google-services.json
```

Add another Android app in the same Firebase project with package `com.attendance.staff`, nickname `PL attendance`. Download its config into:

```text
D:\github\attendance-fingerprint-sensor\staff-app\google-services.json
```

The downloaded config must contain a client matching the corresponding package. For example, a config containing only `com.shelj.myapp` cannot initialize the staff app. You can use separate Firebase projects instead, but each app's config and sending credential must come from the same Firebase project.

Expo handles native integration: do not manually follow Firebase's Gradle-editing steps for this project. See [Firebase Android registration](https://firebase.google.com/docs/android/setup).

## 3. Generate the sending credential

In Firebase, open **Project settings → Service accounts → Generate new private key**. Store the downloaded JSON outside this repository.

There are two different JSON files:

| File | Purpose | Where it belongs |
| --- | --- | --- |
| `google-services.json` | Identifies the Android app's Firebase project | Corresponding app folder; included in the build |
| Service account JSON containing `private_key` | Authorizes Expo to send through FCM | Private storage; uploaded to EAS credentials |

Do not bundle or commit the service account JSON. The client `google-services.json` contains public identifiers and can be committed. It must be present in the EAS build upload, or supplied through an EAS file environment variable named `GOOGLE_SERVICES_JSON`.

## 4. Assign the key in EAS for each app

From the admin folder:

```powershell
cd D:\github\attendance-fingerprint-sensor\mobile-app
npx eas-cli@latest whoami
npx eas-cli@latest credentials
```

If not logged in, run `npx eas-cli@latest login`. If already logged in as `shelj`, skip login; declining its continue prompt simply aborts that login command.

Choose **Android → preview → Google Service Account → Manage your Google Service Account Key for Push Notifications (FCM V1) → Set up a Google Service Account Key → Upload a new service account key**. Menu wording can vary. Enter the path to the private service account JSON, not `google-services.json`.

Confirm the application identifier is `com.shelj.myapp` and FCM V1 shows the expected Firebase project. Once assigned, choose **Go back** and exit. FCM Legacy and Play Store Submissions can stay unassigned for this setup.

Repeat `credentials` from the **staff-app** folder, confirming `com.attendance.staff`. If both apps use the same Firebase project, you can select the existing service account key, but it must be assigned to each application's FCM V1 credentials. Keep the two EAS projects separate.

Official instructions: [Expo FCM V1 credentials](https://docs.expo.dev/push-notifications/fcm-credentials/).

## 5. Check configuration and rebuild

In each app folder:

```powershell
npx expo config --type public
```

Check the Android package and `googleServicesFile: './google-services.json'`. Then build:

```powershell
npx eas-cli@latest build --platform android --profile preview
```

Install the resulting APK, sign in, and allow notifications. Repeat the build in the other app folder for its APK. An old APK does not gain Firebase configuration merely because you uploaded the sending key. Expo Go is not the push test environment for these apps.

## 6. Test with understandable cases

**Case A: check provider setup without attendance.** In an installed app, use **Settings → Test notification**. The backend sends this test directly; the attendance cron job is not needed. `Sent` means Expo accepted the request; `Received` means the running app observed the notification. A Sent result alone does not prove phone delivery.

**Case B: check the complete attendance flow.** Sign in to the rebuilt apps first, then create a new accepted check-in/out. With one-minute cron, allow roughly a minute plus provider delivery time. Admin should receive the management alert and the relevant staff phone its personal alert. Respect the five-minute attendance cooldown; a rejected attempt creates no event.

**Case C: old attendance produces no alert after first sign-in.** This is expected: first push registration skips existing history. Create a new event after registration to test delivery.

## Troubleshooting

| Message or symptom | Action |
| --- | --- |
| `Failed to resolve plugin ... expo-router` | Run `npm ci` in the failing app folder and wait for success |
| `Set EXPO_PUBLIC_API_URL ...` | Check that app's `.env`; use a server origin without an API path; retry config evaluation |
| Unable to get Firebase messaging instance / googleServicesFile error | Check the client config exists, contains the right package and is included in the build; rebuild and install |
| FCM V1 says None assigned | Assign the service account key for that app's application identifier |
| Test works but new attendance alerts do not | Check the deployed attendance worker or cron job and its logs |
| `SENDER_ID_MISMATCH` | Ensure the installed client config and EAS sending key belong to the same Firebase project |
| `Deploy the backend update for saved mobile login` | Deploy updated Django auth code and restart the backend, then sign in; Firebase cannot fix missing auth support |

This guide covers Android. iOS additionally needs Apple APNs credentials; see [Expo push setup](https://docs.expo.dev/push-notifications/push-notifications-setup/).
