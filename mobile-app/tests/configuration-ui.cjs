// Isolated browser fixtures: no configuration changes reach the real backend.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const http = require('node:http');
const path = require('node:path');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const root = path.resolve(__dirname, '../dist');
const output = path.resolve(__dirname, '../test-results');
fs.mkdirSync(output, { recursive: true });
const offices = [{ id: 1, name: 'Test Office', is_active: true, wifi_ssid: 'Office WiFi', wifi_bssid: 'aa:bb:cc:dd:ee:ff', latitude: 10, longitude: 76, radius_meters: 100, max_accuracy_meters: 50 }];
const writes = [];
const server = http.createServer((req, res) => {
  let file = path.resolve(root, '.' + new URL(req.url, 'http://localhost').pathname);
  if (!file.startsWith(root + path.sep) || !fs.existsSync(file) || fs.statSync(file).isDirectory()) file = path.join(root, 'index.html');
  res.setHeader('Content-Type', { '.html': 'text/html', '.js': 'application/javascript', '.css': 'text/css', '.png': 'image/png', '.jpg': 'image/jpeg', '.ttf': 'font/ttf' }[path.extname(file)] || 'application/octet-stream');
  fs.createReadStream(file).pipe(res);
});
(async () => {
  await new Promise(resolve => server.listen(9125, '127.0.0.1', resolve));
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  const context = await browser.newContext({ viewport: { width: 390, height: 844 }, permissions: ['geolocation'], geolocation: { latitude: 10.25, longitude: 76.5, accuracy: 5 } });
  const page = await context.newPage();
  const errors = []; page.on('pageerror', error => errors.push(error.message));
  await page.route('**/api/mobile/**', async route => {
    const request = route.request(); const key = new URL(request.url()).pathname.split('/api/mobile/')[1];
    const headers = { 'Access-Control-Allow-Origin': 'http://127.0.0.1:9125', 'Access-Control-Allow-Credentials': 'true', 'Access-Control-Allow-Headers': 'Content-Type, X-CSRFToken', 'Access-Control-Allow-Methods': 'GET, POST, OPTIONS' };
    if (request.method() === 'OPTIONS') return route.fulfill({ status: 204, headers });
    let data;
    if (key === 'auth/session/') data = { authenticated: true, username: 'Manager', csrf_token: 'fixture-csrf' };
    if (key === 'dashboard/') data = { total_employees: 1, today_sessions: 0, active_sessions: 0, device: null };
    if (key === 'notifications/') data = { notifications: [], cursor: 0, has_more: false };
    if (key.startsWith('configuration/offices/')) {
      if (request.method() === 'POST') {
        const body = request.postDataJSON();
        if (body.wifi_bssid === 'invalid') return route.fulfill({ status: 400, headers, json: { errors: { wifi_bssid: [{ message: 'Enter the router BSSID.' }] } } });
        assert.equal(request.headers()['x-csrftoken'], 'fixture-csrf');
        writes.push({ key, body });
        const id = Number(key.split('/')[2]) || offices.length + 1;
        const office = { ...body, id };
        const index = offices.findIndex(item => item.id === id);
        if (index < 0) offices.push(office); else offices[index] = office;
        data = { office };
      } else data = { offices };
    }
    assert.ok(data, key);
    await route.fulfill({ headers, json: data });
  });
  try {
    await page.goto('http://127.0.0.1:9125/');
    await page.getByRole('button', { name: 'App configuration', exact: true }).click();
    await page.getByRole('button', { name: 'Test Office', exact: true }).click();
    assert.equal(await page.getByRole('textbox', { name: 'Office name', exact: true }).inputValue(), 'Test Office');
    await page.getByRole('button', { name: 'Use connected Wi-Fi', exact: true }).click();
    await page.getByText('Browsers cannot read Wi-Fi names or BSSIDs.', { exact: false }).waitFor();
    assert.equal(await page.getByRole('textbox', { name: 'Wi-Fi network name (SSID)', exact: true }).inputValue(), 'Office WiFi');
    await page.getByRole('button', { name: 'Use current location', exact: true }).click();
    await page.getByText('Location captured (±5 m). Review it and save the configuration.', { exact: true }).waitFor();
    assert.equal(await page.getByRole('textbox', { name: 'Latitude', exact: true }).inputValue(), '10.250000');
    await page.getByRole('textbox', { name: 'Wi-Fi access-point BSSID', exact: true }).fill('invalid');
    await page.getByRole('button', { name: 'Save configuration', exact: true }).click();
    await page.getByText('wifi_bssid: Enter the router BSSID.', { exact: true }).waitFor();
    assert.equal(writes.length, 0);
    await page.getByRole('textbox', { name: 'Wi-Fi access-point BSSID', exact: true }).fill('11:22:33:44:55:66');
    await page.getByRole('button', { name: 'Save configuration', exact: true }).click();
    await page.getByText('Configuration saved. Staff attendance will use these settings on the next submission.', { exact: true }).waitFor();
    assert.equal(writes[0].key, 'configuration/offices/1/');
    assert.equal(writes[0].body.latitude, 10.25);
    assert.equal(writes[0].body.longitude, 76.5);
    await page.getByRole('button', { name: 'Active · Accept office attendance', exact: true }).click();
    await page.getByRole('button', { name: 'Save configuration', exact: true }).click();
    await page.getByRole('button', { name: 'Test Office (inactive)', exact: true }).waitFor();
    assert.equal(writes.at(-1).body.is_active, false);
    for (const width of [320, 390, 844]) {
      await page.setViewportSize({ width, height: 844 });
      await page.evaluate(() => document.fonts.ready);
      assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1));
      await page.screenshot({ path: path.join(output, `configuration-${width}.png`), fullPage: true });
    }
    await page.getByRole('button', { name: 'Add office', exact: true }).click();
    assert.equal(await page.getByRole('textbox', { name: 'Office name', exact: true }).inputValue(), '');
    assert.ok(await page.getByRole('button', { name: 'Save configuration', exact: true }).isDisabled());
    assert.deepEqual(errors, []);
    console.log('Configuration UI passed: dashboard navigation, GPS capture, validation, save, deactivate, add-office reset and three widths.');
  } finally { await browser.close(); await new Promise(resolve => server.close(resolve)); }
})().catch(error => { console.error(error); server.close(); process.exitCode = 1; });
