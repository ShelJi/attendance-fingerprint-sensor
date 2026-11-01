// Isolated UI preview: API requests are answered in-page and never reach a real backend.
const http = require('node:http');
const fs = require('node:fs');
const path = require('node:path');

function fixtures() {
  if (location.search.includes('light')) {
    const matchMedia = window.matchMedia.bind(window);
    window.matchMedia = query => query.includes('prefers-color-scheme') ? { matches: false, media: query, addListener() {}, removeListener() {}, addEventListener() {}, removeEventListener() {} } : matchMedia(query);
  }
  let authenticated = !location.search.includes('signedout');
  const person = { id: 1, name: 'Alexandra Morgan-Williams', employee_id: 'EMP-001', fingerprint_id: '12' };
  const session = { id: 1, login_at: '2026-11-01T09:00:00+05:30', logout_at: '2026-11-01T17:30:00+05:30', worked_hours: 'PT8H30M', evidence: [{ action: 'login', mode: 'office', latitude: 10.1234567, longitude: 76.7654321 }, { action: 'logout', mode: 'outdoor', latitude: 10.2234567, longitude: 76.8654321 }] };
  const fingerprintSession = { ...session, id: 2, evidence: [] };
  const device = { device_id: 'attendance-office-01', is_online: true, is_active: true, last_seen: session.logout_at };
  const office = { id: 1, name: 'Downtown office', is_active: true, wifi_ssid: 'PL Office WiFi', wifi_bssid: 'aa:bb:cc:dd:ee:ff', latitude: 10, longitude: 76, radius_meters: 100, max_accuracy_meters: 50 };
  const detail = { employee: person, page_obj: { results: [session, fingerprintSession], count: 2, page: 1, pages: 1, has_next: false, has_previous: false }, total_worked: '17h 0m' };
  const report = { start_date: '2026-11-01', end_date: '2026-11-30', total_records: 1, grand_total: '8h 30m', report_data: [{ employee: person, employee_total: '8h 30m', records: [{ date: '2026-11-01', ...session, sessions: 1, worked_hours: '8h 30m' }] }] };
  const realFetch = window.fetch.bind(window);
  window.fetch = async (input, options) => {
    const url = new URL(typeof input === 'string' ? input : input.url, location.origin);
    if (!url.pathname.includes('/api/mobile/')) return realFetch(input, options);
    const key = url.pathname.split('/api/mobile/')[1].replace(/^me\//, '');
    const source = url.searchParams.get('source') || 'all';
    const sessions = source === 'app' ? [session] : source === 'device' ? [fingerprintSession] : [session, fingerprintSession];
    const counts = { app_logins: source === 'device' ? 0 : 1, device_logins: source === 'app' ? 0 : 1 };
    let data;
    if (key === 'auth/session/') data = { authenticated, username: authenticated ? 'Alex' : null, csrf_token: 'fixture' };
    if (key === 'auth/login/') { authenticated = true; data = { username: 'Alex', csrf_token: 'fixture' }; }
    if (key === 'auth/logout/') { authenticated = false; data = { success: true }; }
    if (key === 'notification-settings/') {
      data = { enabled: true };
    }
    if (key === 'dashboard/') data = { device, total_employees: 12, today_sessions: 9, active_sessions: 6 };
    if (key === 'employees/') data = { employee_data: [{ employee: person, last_action: 'Logout', last_time: session.logout_at }] };
    if (key === 'employees/1/' || key === 'profile/') data = detail;
    if (key === 'attendance/') data = { employee: person, username: 'Alex', checked_in: false, action: null, notification_id: null, sessions: [session], evidence: [], verification: { office_configured: true } };
    if (key === 'calendar/') {
      const now = new Date(); const year = +(url.searchParams.get('year') || now.getFullYear()); const month = +(url.searchParams.get('month') || now.getMonth() + 1);
      data = { year, month, calendar_days: [{ date: `${year}-${String(month).padStart(2, '0')}-15`, employee_count: 1, total_worked_seconds: 30600 * sessions.length, ...counts }] };
    }
    if (key === 'calendar/day/') data = { date: url.searchParams.get('date'), employee_count: 1, total_worked: '8h 30m', employees: [{ employee_id: 1, name: person.name, login_at: '09:00', logout_at: '17:30', worked_hours: '8h 30m', is_active: false, ...counts, sessions }] };
    if (key === 'report/') data = { ...report, report_data: [{ ...report.report_data[0], records: report.report_data[0].records.map(row => ({ ...row, ...counts, sessions: sessions.length })) }] };
    if (key === 'device/control/') data = { device };
    if (key === 'device/control/command/') data = { command_id: 42, status: 'pending', message: 'Command queued' };
    if (key === 'device/control/result/') data = { status: 'completed', result: { message: 'Fingerprint sensor ready', device_id: 'attendance-office-01', status: 'online' } };
    if (key === 'configuration/offices/') data = { offices: [office] };
    if (key === 'notifications/') data = { notifications: [], cursor: 0, has_more: false };
    if (key === 'attendance/records/') data = { records: [{ id: 1, employee_id: 1, employee_code: person.employee_id, name: person.name, session_id: 1, action: 'login', mode: 'outdoor', occurred_at: session.login_at, verification: { office: null, latitude: 10, longitude: 76, accuracy_meters: 10, captured_at: session.login_at, place_name: 'Client office', work_description: 'Completed installation and employee training.', wifi_ssid: '', wifi_bssid: '' } }], totals: { office: 0, outdoor: 1, device: 0 }, page: 1, pages: 1, count: 1, has_next: false, has_previous: false };
    return Response.json(data || { error: 'Preview is read-only' }, { status: data ? 200 : 400 });
  };
  if (location.search.includes('largeText')) {
    const scale = () => document.querySelectorAll('[dir="auto"],input,textarea').forEach(element => {
      if (element.dataset.scaled || element.getAttribute('aria-hidden') === 'true') return;
      element.dataset.scaled = 'true';
      const style = getComputedStyle(element);
      element.style.fontSize = `${parseFloat(style.fontSize) * 1.5}px`;
      if (style.lineHeight !== 'normal') element.style.lineHeight = `${parseFloat(style.lineHeight) * 1.5}px`;
    });
    new MutationObserver(scale).observe(document, { childList: true, subtree: true });
  }
}

for (const [app, port] of [['mobile-app', 9140], ['staff-app', 9141]]) {
  const root = path.resolve(__dirname, '..', app, 'dist');
  http.createServer((req, res) => {
    let file = path.resolve(root, '.' + decodeURIComponent(new URL(req.url, 'http://localhost').pathname));
    if (!file.startsWith(root + path.sep) || !fs.existsSync(file) || fs.statSync(file).isDirectory()) file = path.join(root, 'index.html');
    res.setHeader('Content-Type', { '.html': 'text/html', '.js': 'application/javascript', '.ttf': 'font/ttf', '.png': 'image/png', '.jpg': 'image/jpeg', '.json': 'application/json' }[path.extname(file)] || 'application/octet-stream');
    if (file.endsWith('index.html')) res.end(fs.readFileSync(file, 'utf8').replace('<head>', `<head><script>(${fixtures.toString()})();</script>`));
    else fs.createReadStream(file).pipe(res);
  }).listen(port, '127.0.0.1', () => console.log(`${app}: http://127.0.0.1:${port}`));
}
