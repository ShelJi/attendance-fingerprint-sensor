import assert from 'node:assert/strict';
import test from 'node:test';
import { Api, ApiError, serverUrl } from '../src/api.ts';
import { attendanceMessage } from '../src/attendance.ts';

test('login refreshes CSRF and attendance writes send the rotated token', async () => {
  const calls = [];
  const api = new Api('https://attendance.example.com', async (url, options) => {
    calls.push({ url, options });
    const data = url.endsWith('auth/session/') ? { csrf_token: 'initial' }
      : url.endsWith('auth/login/') ? { username: 'E1', csrf_token: 'rotated' }
      : { action: 'login', checked_in: true };
    return new Response(JSON.stringify(data), { status: 200 });
  });
  assert.equal(await api.login('E1', 'E1'), 'E1');
  await api.post('attendance/', { action: 'login' });
  assert.equal(calls[1].options.headers['X-CSRFToken'], 'initial');
  assert.equal(calls[2].options.headers['X-CSRFToken'], 'rotated');
  assert.equal(calls[2].options.credentials, 'include');
  assert.equal(calls[2].url, 'https://attendance.example.com/api/mobile/me/attendance/');
  assert.deepEqual(JSON.parse(calls[2].options.body), { action: 'login' });
});

test('expired attendance sessions and validation errors are surfaced', async () => {
  let expired = false;
  const api = new Api('https://attendance.example.com', async () => new Response(JSON.stringify({ error: 'Authentication required' }), { status: 401 }));
  api.onUnauthorized = () => { expired = true; };
  await assert.rejects(api.get('attendance/'), error => error instanceof ApiError && error.status === 401);
  assert.equal(expired, true);
});

test('server configuration rejects embedded credentials and paths', () => {
  assert.equal(serverUrl(' https://attendance.example.com/ '), 'https://attendance.example.com');
  assert.throws(() => serverUrl('https://user:secret@example.com'));
  assert.throws(() => serverUrl('https://example.com/api/'));
});

test('cooldown responses do not claim attendance succeeded', () => {
  assert.match(attendanceMessage('already_logged_in'), /Wait five minutes/);
  assert.match(attendanceMessage('already_done'), /Wait five minutes/);
  assert.match(attendanceMessage('logout'), /Checked out/);
});

test('HTML, empty and malformed responses show a useful server error', async () => {
  for (const body of ['<!doctype html><html>Sign in</html>', '', '{broken']) {
    const api = new Api('http://127.0.0.1:8000', async () => new Response(body));
    await assert.rejects(api.session(), error => error instanceof ApiError && /invalid JSON response.*Check EXPO_PUBLIC_API_URL/.test(error.message));
    await assert.rejects(api.post('auth/login/', {}), ApiError);
  }
  const missing = new Api('http://127.0.0.1:8000', async () => new Response('<html>Not Found</html>', { status: 404 }));
  await assert.rejects(missing.session(), /Mobile API not found/);
});

test('expired password and logout sessions notify; invalid credentials do not', async () => {
  let expired = 0;
  const api = new Api('http://127.0.0.1:8000', async () => Response.json({ error: 'Authentication required' }, { status: 401 }));
  api.onUnauthorized = () => expired++;
  for (const path of ['auth/password/', 'auth/logout/']) await assert.rejects(api.post(path, {}), ApiError);
  assert.equal(expired, 2);
  await assert.rejects(api.post('auth/login/', {}), ApiError);
  assert.equal(expired, 2);
});

test('native login survives a new client and clears the stored session on logout', async () => {
  const calls = [];
  let saved = null;
  const key = 's'.repeat(32);
  const replies = [
    { authenticated: false, csrf_token: 'initial', session_key: null },
    { username: 'admin', csrf_token: 'rotated', session_key: key },
  ];
  const api = new Api('https://example.com', async (url, options) => { calls.push(options); return Response.json(replies.shift()); });
  api.sessionKey = null;
  api.onSessionChange = async value => { saved = value; };
  await api.login('admin', 'secret');
  assert.equal(saved, key);
  assert.equal(calls[1].credentials, 'omit');
  assert.equal(calls[1].headers.Cookie, 'csrftoken=initial');
  assert.equal(calls[1].headers['X-App-Client'], 'native');
  const restarted = new Api('https://example.com', async (url, options) => {
    calls.push(options);
    return Response.json(url.endsWith('auth/logout/') ? { success: true, session_key: null } : { authenticated: true, username: 'admin', csrf_token: 'fresh', session_key: key });
  });
  restarted.sessionKey = saved;
  restarted.onSessionChange = async value => { saved = value; };
  assert.equal((await restarted.session()).authenticated, true);
  assert.equal(calls[2].headers.Cookie, `sessionid=${key}`);
  await restarted.logout();
  assert.equal(calls[3].headers.Cookie, `sessionid=${key}; csrftoken=fresh`);
  assert.equal(saved, null);
});

test('native password rotation updates saved credentials and session expiry clears them', async () => {
  let saved = 'old';
  let expired = false;
  const api = new Api('https://example.com', async url => url.endsWith('auth/password/')
    ? Response.json({ csrf_token: 'new-csrf', session_key: 'new-session' })
    : Response.json({ error: 'Authentication required' }, { status: 401 }));
  api.sessionKey = saved;
  api.onSessionChange = async value => { saved = value; };
  api.onUnauthorized = () => { expired = true; };
  await api.post('auth/password/', {});
  assert.equal(saved, 'new-session');
  await assert.rejects(api.get('dashboard/'), ApiError);
  assert.equal(saved, null);
  assert.equal(api.sessionKey, null);
  assert.equal(expired, true);
});
