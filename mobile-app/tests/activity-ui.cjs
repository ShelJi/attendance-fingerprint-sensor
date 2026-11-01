// Isolated API fixtures; no requests or writes reach the deployed backend.
const assert = require('node:assert/strict');
const http = require('node:http');
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const root = path.resolve(__dirname, '../dist');
const output = path.resolve(__dirname, '../test-results');
fs.mkdirSync(output, { recursive: true });
const base = { employee_id: 1, employee_code: 'TEST-1', name: 'Test Employee', session_id: 1, occurred_at: '2026-10-25T09:00:00+05:30' };
const proof = { latitude: 10, longitude: 76, accuracy_meters: 10, captured_at: base.occurred_at, wifi_ssid: 'PL Office WiFi', wifi_bssid: 'aa:bb:cc:dd:ee:ff' };
const records = [
  { ...base, id: 1, action: 'login', mode: 'office', verification: { ...proof, office: 'PL Test Office', place_name: '', work_description: '' } },
  { ...base, id: 2, action: 'logout', mode: 'outdoor', verification: { ...proof, office: null, place_name: 'Test Client Site', work_description: 'Completed installation and client training' } },
];
const server = http.createServer((req, res) => {
  let file = path.resolve(root, '.' + new URL(req.url, 'http://localhost').pathname);
  if (!file.startsWith(root + path.sep) || !fs.existsSync(file) || fs.statSync(file).isDirectory()) file = path.join(root, 'index.html');
  res.setHeader('Content-Type', { '.html': 'text/html', '.js': 'application/javascript', '.png': 'image/png', '.jpg': 'image/jpeg', '.ttf': 'font/ttf' }[path.extname(file)] || 'application/octet-stream');
  fs.createReadStream(file).pipe(res);
});
(async () => {
  await new Promise(resolve => server.listen(9124, '127.0.0.1', resolve));
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  const page = await browser.newPage({ viewport: { width: 390, height: 844 } });
  const errors = []; page.on('pageerror', error => errors.push(error.message));
  let deliver = false;
  await page.route('**/api/mobile/**', async route => {
    const url = new URL(route.request().url()); const key = url.pathname.split('/api/mobile/')[1];
    let data;
    if (key === 'auth/session/') data = { authenticated: true, username: 'Test Admin', csrf_token: 'fixture' };
    if (key === 'dashboard/') data = { total_employees: 1, today_sessions: 1, active_sessions: 0, device: null };
    if (key === 'notifications/') {
      const after = url.searchParams.get('after');
      data = { notifications: after === null ? [records[0]] : deliver && after === '1' ? [records[1]] : [], cursor: after === null ? 1 : deliver ? 2 : 1, has_more: false };
    }
    if (key === 'attendance/records/') {
      const mode = url.searchParams.get('mode'); const filtered = mode ? records.filter(row => row.mode === mode) : records;
      data = { records: filtered, totals: { office: 1, outdoor: 1, device: 0 }, page: 1, pages: 1, count: filtered.length, has_next: false, has_previous: false };
    }
    assert.ok(data, key);
    await route.fulfill({ json: data, headers: { 'Access-Control-Allow-Origin': 'http://127.0.0.1:9124', 'Access-Control-Allow-Credentials': 'true' } });
  });
  try {
    await page.goto('http://127.0.0.1:9124/');
    await page.getByText('Hello, Test Admin', { exact: true }).waitFor();
    await page.getByRole('button', { name: 'All attendance notifications', exact: true }).click();
    await page.getByText('Completed installation and client training', { exact: true }).waitFor();
    for (const width of [320, 390, 844]) {
      await page.setViewportSize({ width, height: width === 844 ? 390 : 844 });
      for (const mode of ['Office', 'Outdoor']) {
        await page.getByRole('button', { name: mode, exact: true }).click();
        await page.getByText(mode === 'Office' ? 'PL Test Office' : 'Test Client Site', { exact: true }).waitFor();
        await page.evaluate(() => document.fonts.ready);
        assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1));
        await page.screenshot({ path: path.join(output, `work-${mode.toLowerCase()}-${width}.png`) });
      }
    }
    deliver = true;
    assert.equal(await page.getByRole('button', { name: /Dismiss notification/ }).count(), 0);
    await page.screenshot({ path: path.join(output, 'work-no-toast.png') });
    assert.deepEqual(errors, []);
    console.log('Activity UI passed: navigation, separate Office/Outdoor filters, details, three widths, no in-app toasts, and no runtime errors.');
  } catch (error) {
    await page.screenshot({ path: path.join(output, 'work-failure.png') }); throw error;
  } finally { await browser.close(); await new Promise(resolve => server.close(resolve)); }
})().catch(error => { console.error(error); server.close(); process.exitCode = 1; });
