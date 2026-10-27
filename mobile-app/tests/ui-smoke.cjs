// Isolated browser fixtures: no requests reach the real backend or change user data.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const http = require('node:http');
const path = require('node:path');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const root = path.resolve(__dirname, '../dist');
const output = path.resolve(__dirname, '../test-results');
fs.mkdirSync(output, { recursive: true });
if (fs.existsSync(path.join(output, 'failure.png'))) fs.unlinkSync(path.join(output, 'failure.png'));
const person = { id: 1, name: 'Alexandra Morgan-Williams', employee_id: 'EMP-001', fingerprint_id: '12' };
const session = { id: 1, login_at: '2026-10-25T09:00:00+05:30', logout_at: '2026-10-25T10:00:00+05:30', worked_hours: 'P0DT01H00M00S' };
const device = { device_id: 'attendance-01', is_online: true, is_active: true, last_seen: '2026-10-25T10:00:00+05:30' };
const requests = [];
let authenticated = false;
let empty = false;
let unavailable = false;
let managementDenied = false;
let expirePassword = false;
const server = http.createServer((req, res) => {
  const pathname = decodeURIComponent(new URL(req.url, 'http://localhost').pathname);
  let file = path.resolve(root, '.' + pathname);
  if (!file.startsWith(root + path.sep) || !fs.existsSync(file) || fs.statSync(file).isDirectory()) file = path.join(root, 'index.html');
  const mime = { '.html': 'text/html', '.js': 'application/javascript', '.css': 'text/css', '.png': 'image/png', '.ttf': 'font/ttf', '.woff': 'font/woff', '.json': 'application/json' };
  res.setHeader('Content-Type', mime[path.extname(file)] || 'application/octet-stream');
  fs.createReadStream(file).pipe(res);
});

(async () => {
  await new Promise(resolve => server.listen(9123, '127.0.0.1', resolve));
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  const context = await browser.newContext({ viewport: { width: 390, height: 844 }, locale: 'en-US', colorScheme: 'light' });
  const page = await context.newPage();
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  await context.route('**/api/mobile/**', async route => {
    const request = route.request(); const url = new URL(request.url()); const key = url.pathname.split('/api/mobile/')[1];
    requests.push({ key, query: url.search, method: request.method(), body: request.postDataJSON() });
    const headers = { 'Access-Control-Allow-Origin': 'http://127.0.0.1:9123', 'Access-Control-Allow-Credentials': 'true', 'Access-Control-Allow-Headers': 'Content-Type, X-CSRFToken', 'Access-Control-Allow-Methods': 'GET, POST, OPTIONS' };
    if (request.method() === 'OPTIONS') return route.fulfill({ status: 204, headers });
    if (managementDenied && key === 'dashboard/') return route.fulfill({ status: 403, headers, json: { error: 'Management access required' } });
    if (expirePassword && key === 'auth/password/') {
      authenticated = false;
      return route.fulfill({ status: 401, headers, json: { error: 'Authentication required' } });
    }
    if (unavailable && key === 'dashboard/') return route.fulfill({ status: 503, headers, json: { error: 'Test connection unavailable' } });
    let data;
    if (key === 'auth/session/') data = { authenticated, username: authenticated ? 'Alex' : null, csrf_token: 'test-csrf' };
    if (key === 'auth/login/') { authenticated = true; data = { username: 'Alex', csrf_token: 'test-rotated' }; }
    if (key === 'auth/logout/') { authenticated = false; data = { success: true }; }
    if (key === 'auth/password/') data = { success: true, csrf_token: 'password-rotated' };
    if (key === 'notifications/') data = { notifications: [], cursor: 0, has_more: false };
    if (key === 'dashboard/') data = { device, total_employees: 1, today_sessions: 1, active_sessions: 0 };
    if (key === 'employees/') data = { employee_data: empty ? [] : [{ employee: person, last_action: 'Logout', last_time: session.logout_at, worked_hours: session.worked_hours }] };
    if (key === 'employees/create/') data = { employee: person };
    if (key === 'employees/1/') data = { employee: person, page_obj: { results: empty ? [] : [session], count: empty ? 0 : 1, page: 1, pages: 1, has_next: false, has_previous: false }, total_worked: '1h 0m' };
    if (key === 'calendar/') {
      const year = +(url.searchParams.get('year') || 2026); const month = +(url.searchParams.get('month') || 10);
      data = { year, month, calendar_days: empty ? [] : [{ date: `${String(year).padStart(4, '0')}-${String(month).padStart(2, '0')}-15`, employee_count: 1, total_worked_seconds: 3600 }] };
    }
    if (key === 'calendar/day/') data = { date: url.searchParams.get('date'), employee_count: empty ? 0 : 1, total_worked: '1h 0m', employees: empty ? [] : [{ employee_id: 1, name: person.name, login_at: '09:00', logout_at: '10:00', worked_hours: '1h 0m', is_active: false }] };
    if (key === 'device/control/') data = { device };
    if (key === 'device/control/command/') data = { command_id: 42, status: 'pending', message: 'Command queued' };
    if (key === 'device/control/result/') data = { status: 'completed', result: { message: 'Sensor ready' } };
    if (key === 'report/') data = { start_date: '2026-10-01', end_date: '2026-10-25', total_records: empty ? 0 : 1, grand_total: '1h 0m', report_data: empty ? [] : [{ employee: person, employee_total: '1h 0m', records: [{ date: '2026-10-25', ...session, sessions: 1, worked_hours: '1h 0m' }] }] };
    assert.ok(data, `Unhandled fixture: ${key}`);
    await route.fulfill({ status: key === 'employees/create/' ? 201 : 200, headers, json: data });
  });
  async function visit(route, text) { await page.goto(`http://127.0.0.1:9123${route}`); await page.getByText(text, { exact: true }).first().waitFor(); await page.waitForLoadState('networkidle'); await page.evaluate(() => document.fonts.ready); }
  async function capture(name) {
    assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), `${name} horizontally overflows`);
    for (const tab of await page.getByRole('tab').all()) {
      const box = await tab.boundingBox();
      const text = await tab.locator('[dir="auto"]').last().boundingBox();
      if (box && text) assert.ok(text.y + text.height <= box.y + box.height + 1, `${name} clips a bottom-tab label`);
    }
    await page.screenshot({ path: path.join(output, name + '.png') });
  }
  try {
    await visit('/login', 'Welcome back');
    assert.equal(await page.getByRole('textbox', { name: 'Backend URL', exact: true }).count(), 0);
    await page.getByRole('textbox', { name: 'Username', exact: true }).fill('Alex');
    await page.getByLabel('Password', { exact: true }).fill('test-only');
    await capture('login-390');
    await page.getByRole('button', { name: 'Sign in', exact: true }).click();
    await page.getByText('Hello, Alex', { exact: true }).waitFor();
    await capture('overview-390');
    await page.getByRole('button', { name: 'Settings', exact: true }).click();
    await page.getByRole('textbox', { name: 'Backend URL', exact: true }).waitFor();
    await page.getByLabel('Current password', { exact: true }).fill('test-only');
    await page.getByLabel('New password', { exact: true }).fill('new-strong-secret');
    await page.getByLabel('Confirm new password', { exact: true }).fill('different-secret');
    await page.getByRole('button', { name: 'Save password', exact: true }).click();
    await page.getByText('The new passwords do not match.', { exact: true }).waitFor();
    assert.equal(requests.filter(item => item.key === 'auth/password/').length, 0);
    await page.getByLabel('Confirm new password', { exact: true }).fill('new-strong-secret');
    await page.getByRole('button', { name: 'Save password', exact: true }).click();
    await page.getByText('Password updated. You are still signed in.', { exact: true }).waitFor();
    assert.equal(await page.getByLabel('Current password', { exact: true }).inputValue(), '');
    const screens = [['/', 'Hello, Alex', 'overview'], ['/employees', 'Team directory', 'people'], ['/employee/1', person.name, 'employee'], ['/employee/create', 'Full name', 'create'], ['/calendar', 'Every day tells a story', 'calendar'], ['/device', 'Connected to your workday', 'device'], ['/reports', 'The bigger picture', 'reports'], ['/settings', 'Your workspace, your way', 'settings']];
    for (const width of [320, 390, 430, 844]) {
      await page.setViewportSize({ width, height: width === 844 ? 390 : 844 });
      for (const [route, text, name] of screens) { await visit(route, text); await capture(`${name}-${width}`); }
    }
    await page.setViewportSize({ width: 320, height: 844 });
    await visit('/calendar', 'Every day tells a story');
    await page.getByRole('button', { name: 'Next month', exact: true }).click();
    await page.getByRole('button', { name: 'Previous month', exact: true }).click();
    await page.getByRole('button', { name: 'Jump to month and year', exact: true }).click();
    await page.getByRole('textbox', { name: 'Year', exact: true }).fill('2024');
    await page.getByRole('textbox', { name: 'Month (1–12)', exact: true }).fill('2');
    await page.getByRole('button', { name: 'Go to month', exact: true }).click();
    const leap = page.getByRole('button', { name: /^2024-02-29,/ });
    await leap.waitFor();
    const bounds = await leap.boundingBox(); assert.ok(bounds.width >= 44 && bounds.height >= 44, 'Calendar touch target is too small');
    await leap.click();
    await page.getByText('Day details · 2024-02-29', { exact: true }).waitFor();
    await capture('calendar-selected-320');
    await visit('/employees', 'Team directory');
    await page.getByRole('textbox', { name: 'Find a team member', exact: true }).fill('does-not-exist');
    await page.getByText('No matching team members', { exact: true }).waitFor();
    await page.getByRole('textbox', { name: 'Find a team member', exact: true }).fill('');
    await page.getByRole('button', { name: 'Add team member', exact: true }).click();
    await page.getByRole('textbox', { name: 'Full name', exact: true }).fill('Test Person');
    await page.getByRole('textbox', { name: 'Employee ID', exact: true }).fill('TEST-2');
    await page.getByRole('textbox', { name: 'Fingerprint ID', exact: true }).fill('2');
    await page.getByRole('button', { name: 'Create employee', exact: true }).click();
    await page.getByText('Team directory', { exact: true }).waitFor();
    await visit('/device', 'Connected to your workday');
    await page.getByRole('button', { name: 'Send command', exact: true }).click();
    await page.getByText('completed', { exact: true }).waitFor();
    await page.getByRole('button', { name: 'Delete', exact: true }).click();
    await page.getByRole('textbox', { name: 'Fingerprint ID (1–127)', exact: true }).fill('12');
    const commandCount = requests.filter(item => item.key === 'device/control/command/').length;
    page.once('dialog', dialog => dialog.dismiss());
    await page.getByRole('button', { name: 'Send command', exact: true }).click();
    assert.equal(requests.filter(item => item.key === 'device/control/command/').length, commandCount);
    page.once('dialog', dialog => dialog.accept());
    await page.getByRole('button', { name: 'Send command', exact: true }).click();
    await page.getByText('pending', { exact: true }).waitFor();
    await page.getByText('completed', { exact: true }).waitFor();
    assert.equal(requests.filter(item => item.key === 'device/control/command/').at(-1).body.command, 'DELETE');
    await visit('/reports', 'The bigger picture');
    await page.getByRole('textbox', { name: 'From', exact: true }).fill('2026-10-25');
    await page.getByRole('textbox', { name: 'To', exact: true }).fill('2026-10-01');
    await page.getByRole('button', { name: 'Apply dates', exact: true }).click();
    await page.getByText('Enter valid YYYY-MM-DD dates, with start before end.', { exact: true }).waitFor();
    await capture('reports-validation-320');
    empty = true;
    for (const [route, text, name] of screens.filter(item => ['people', 'calendar', 'reports'].includes(item[2]))) { await visit(route, text); await capture(`${name}-empty-320`); }
    empty = false; unavailable = true;
    await visit('/', 'Hello, Alex'); await page.getByText('Test connection unavailable', { exact: true }).waitFor(); await capture('overview-error-320'); unavailable = false;
    await page.emulateMedia({ colorScheme: 'dark', reducedMotion: 'reduce' });
    await page.setViewportSize({ width: 390, height: 844 });
    for (const [route, text, name] of screens) { await visit(route, text); await capture(`${name}-dark-390`); }
    await page.emulateMedia({ colorScheme: 'light', reducedMotion: 'reduce' });
    await page.setViewportSize({ width: 320, height: 844 });
    for (const [route, text, name] of screens.filter(item => ['calendar', 'create', 'settings'].includes(item[2]))) {
      await visit(route, text);
      await page.evaluate(() => {
        for (const element of document.querySelectorAll('[dir="auto"], input')) {
          if (element.getAttribute('aria-hidden') === 'true' || element.closest('[role="tablist"]')) continue;
          const style = getComputedStyle(element);
          element.style.fontSize = `${parseFloat(style.fontSize) * 1.5}px`;
          if (style.lineHeight !== 'normal') element.style.lineHeight = `${parseFloat(style.lineHeight) * 1.5}px`;
        }
      });
      await capture(`${name}-large-text-320`);
    }
    await visit('/settings', 'Your workspace, your way');
    await page.getByRole('textbox', { name: 'Backend URL', exact: true }).fill('https://attendance.example.net');
    await page.getByRole('button', { name: 'Save backend URL', exact: true }).click();
    await page.getByText('Welcome back', { exact: true }).waitFor();
    assert.equal(await page.evaluate(() => localStorage.getItem('attendance-server')), 'https://attendance.example.net');
    assert.equal(await page.getByRole('textbox', { name: 'Backend URL', exact: true }).count(), 0);
    await page.getByRole('textbox', { name: 'Username', exact: true }).fill('Alex');
    await page.getByLabel('Password', { exact: true }).fill('test-only');
    await page.getByRole('button', { name: 'Sign in', exact: true }).click();
    await page.getByText('Hello, Alex', { exact: true }).waitFor();
    await page.getByRole('button', { name: 'Sign out', exact: true }).click();
    await page.getByText('Welcome back', { exact: true }).waitFor();
    managementDenied = true;
    await page.getByRole('textbox', { name: 'Username', exact: true }).fill('Employee');
    await page.getByLabel('Password', { exact: true }).fill('test-only');
    await page.getByRole('button', { name: 'Sign in', exact: true }).click();
    await page.getByText('Management access required. Use the staff app for an employee account.', { exact: true }).waitFor();
    assert.equal(await page.getByRole('tab').count(), 0);
    await visit('/login', 'Welcome back');
    assert.equal(await page.getByRole('tab').count(), 0);
    managementDenied = false;
    await page.getByRole('textbox', { name: 'Username', exact: true }).fill('Alex');
    await page.getByLabel('Password', { exact: true }).fill('test-only');
    await page.getByRole('button', { name: 'Sign in', exact: true }).click();
    await page.getByText('Hello, Alex', { exact: true }).waitFor();
    await page.getByRole('button', { name: 'Settings', exact: true }).click();
    await page.getByLabel('Current password', { exact: true }).fill('test-only');
    await page.getByLabel('New password', { exact: true }).fill('new-strong-secret');
    await page.getByLabel('Confirm new password', { exact: true }).fill('new-strong-secret');
    expirePassword = true;
    await page.getByRole('button', { name: 'Save password', exact: true }).click();
    await page.getByText('Not signed in', { exact: true }).waitFor();
    assert.equal(await page.getByLabel('Current password', { exact: true }).count(), 0);
    await page.getByRole('button', { name: 'Back to sign in', exact: true }).click();
    await page.getByText('Welcome back', { exact: true }).waitFor();
    assert.equal(errors.length, 0, errors.join('\n'));
    assert.ok(requests.some(item => item.key === 'employees/create/' && item.method === 'POST'));
    assert.ok(requests.some(item => item.key === 'device/control/command/' && item.method === 'POST'));
    fs.writeFileSync(path.join(output, 'summary.json'), JSON.stringify({ screenshots: fs.readdirSync(output).filter(name => name.endsWith('.png')).length, runtimeErrors: errors, widths: [320, 390, 430, 844], requests: requests.length }, null, 2));
    console.log('UI smoke checks passed: navigation, forms, calendar, device polling, validation, empty/error states, light/dark, and four viewport widths.');
  } catch (error) {
    await page.screenshot({ path: path.join(output, 'failure.png') });
    console.error('UI runtime errors:', errors, '\nRequests:', requests, '\nScreen:', await page.locator('body').innerText());
    throw error;
  } finally { await browser.close(); await new Promise(resolve => server.close(resolve)); }
})().catch(error => { console.error(error); server.close(); process.exitCode = 1; });
