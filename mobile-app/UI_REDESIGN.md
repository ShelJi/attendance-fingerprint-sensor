# Mobile UI redesign

## Compact sizing pass — both apps

The current design tokens live in `mobile-app/src/design.ts` and `staff-app/src/design.ts`, with matching values. This pass covers all 11 admin routes and 7 staff routes. The older audit below describes the earlier design and is retained as history.

| Element | Compact specification |
| --- | --- |
| Main heading | 24px / 30px line height |
| Section heading | 18px / 24px |
| Body / labels / buttons | 14px / 20px |
| Secondary / captions | 12px / 18px or 16px |
| Inputs | 16px text, 48px minimum control height |
| Page padding | 12px below 360px wide; 16px otherwise |
| Cards | 16px padding, 12px internal gaps, 16px corners |
| Buttons / icon buttons / chips | 48px / 44px / 44px minimum targets |
| Avatars / decorative tiles / logo | 36px minimum / 40px / 40px |
| Bottom navigation | 64px minimum plus safe area; grows with labels and native font scale |
| Calendar | 44px minimum day height and at least 44px wide at 320px |

The calendar uses near-edge spacing only on the narrowest screens so all seven columns retain touch targets. Screen and people-list gutters use safe-area insets. Date inputs and dashboard metrics reflow with native font scale; avatars and multiline controls can grow. No font scaling caps or whole-screen transforms were added. Existing button press feedback, palette, branding, attendance logic and privacy rules remain unchanged.

Browser validation used isolated fixtures through `testing/responsive-ui-server.cjs`, never live attendance data. The final audit covers all routes at actual widths 320, 360, 375, 390, 412, 480, 768, and 844px (landscape), plus 50% larger text at 320px. It checks horizontal overflow, 44px targets, label clipping, and bottom navigation staying within the viewport. 164 route/viewport checks passed. Light and dark previews were inspected. Screenshots and the measured audit are in ignored `mobile-app/test-results/compact-ui/`.

Both apps pass lint, TypeScript, unit tests, and web/Android exports. Physical Android/iOS Dynamic Type, keyboard and safe-area behavior still need device verification. Native system alerts use the OS layout.

## Earlier design audit


## Audit and scope

The existing app uses Expo SDK 58, React Native 0.88, TypeScript, Expo Router,
Django session authentication, and native PDF sharing. This update stays inside
`mobile-app/`; backend schemas, attendance calculations, device commands, API
paths, and credentials are unchanged.

| Screen | Existing issue | Implemented improvement |
| --- | --- | --- |
| Login | Plain form; weak hierarchy | Gradient welcome, icon fields, password visibility, clear progress/errors |
| Overview | Oversized repetitive actions | Compact tinted metrics, device status, clear action hierarchy |
| People | Uniform cards and text-only status | Initial avatars, search, semantic badges, improved empty/loading states |
| Employee details | Dense session text and stacked navigation | Responsive date filters, session timeline, totals, paging controls |
| Create employee | Form without hierarchy or guidance | Keyboard-aware fields and enrollment guidance; original submission payload |
| Calendar | Manual month entry and summary list | Monday-first grid, month arrows, month/year jump, today/selection/weekend states, attendance markers and daily drill-down |
| Device | Eight primary buttons competing for attention | Compact command selection, descriptions, online/status badges, themed command results |
| Reports | Nested repetitive cards | Shared filters, total-time hero, readable employee breakdown and original PDF action |
| Settings | Plain connection form | Account context, theme status, connection/security sections; backend field stays here only |

There are no event CRUD screens, recurring events, reminders, notifications, or
weekly scheduling modes in this app. The calendar continues to show attendance
from its existing month and day endpoints. Dots represent employees present,
not invented events. No production placeholder data was added.

## Design system and layout

- `src/theme.ts`: system light/dark palettes; violet primary, teal success,
  coral attention, amber waiting states; shared spacing tokens.
- `src/ui.tsx`: cards, gradients, buttons, icon buttons, avatars, badges,
  sections, date filters, empty/error/loading states and input focus treatment.
- One system font, four text sizes and two weights; 4/8-point spacing, rounded
  surfaces, subtle tinted shadows and immediate press feedback.
- Scrollable forms adjust for iOS keyboard insets. Native Android retains its
  platform resize behavior. Bottom tabs hide for the keyboard and include the
  system safe-area inset. Main content is centered and bounded on wide screens.
- Calendar cells retain at least 44px targets at the tested 320px width. Date
  accessibility labels announce today, selection and attendance counts. Decorative
  icon glyphs are excluded from accessibility names.
- Font scaling remains enabled; long names and responsive fields wrap. Landscape
  is enabled. No looping animation or motion dependency was introduced.

Two small integration fixes support browser visual verification: the default
fetch transport retains its global binding, and web stores only the public
server origin in localStorage. Native storage still uses Expo SecureStore.
Production browser API access still depends on your server's CORS/cookie setup;
native authentication remains the deployment target.

## Verification

```powershell
npm test
npm run typecheck
npm run lint
npx expo export --platform android --platform ios --platform web
```

`tests/ui-smoke.cjs` runs Chrome against the exported web bundle. Use an installed
Playwright package, or point `PLAYWRIGHT_MODULE` to its absolute module directory:

```powershell
$env:PLAYWRIGHT_MODULE = '<absolute path to playwright>'
node tests/ui-smoke.cjs
```

The suite intercepts API requests with isolated fixtures, so it never reads or
changes production backend data. It checks login/logout, protected navigation,
employee creation/search, calendar month changes/leap-day selection, device
polling, invalid date filters, Settings URL changes, empty/error states, and
horizontal overflow. Screenshots and results are saved under ignored
`test-results/`. Widths: 320, 390, 430, and 844px landscape; light/dark appearance;
three extra narrow-screen cases with 150% browser text scaling. The fixtures are
test-only and are never imported by app code.

The six unit tests cover the API contract, CSRF rotation/error handling, date
validation, Monday alignment, leap years, and month/year boundaries. Android and
iOS exports verify Metro/Hermes compilation; they are not signed APK/IPA builds.

Physical-device keyboard behavior, native Dynamic Type, native cookie persistence,
sensor enrollment/deletion, and native PDF sharing need on-device verification.
The existing five high-severity npm audit findings in Expo tooling were not
changed with a forced SDK downgrade. Browser screenshot fixtures do not prove
that the currently hosted backend has all mobile endpoints deployed.
