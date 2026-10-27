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
  await api.post('me/attendance/', { action: 'login' });
  assert.equal(calls[1].options.headers['X-CSRFToken'], 'initial');
  assert.equal(calls[2].options.headers['X-CSRFToken'], 'rotated');
  assert.equal(calls[2].options.credentials, 'include');
  assert.deepEqual(JSON.parse(calls[2].options.body), { action: 'login' });
});

test('expired attendance sessions and validation errors are surfaced', async () => {
  let expired = false;
  const api = new Api('https://attendance.example.com', async () => new Response(JSON.stringify({ error: 'Authentication required' }), { status: 401 }));
  api.onUnauthorized = () => { expired = true; };
  await assert.rejects(api.get('me/attendance/'), error => error instanceof ApiError && error.status === 401);
  assert.equal(expired, true);
});

test('server configuration rejects embedded credentials and paths', () => {
  assert.equal(serverUrl(' https://attendance.example.com/ '), 'https://attendance.example.com');
  assert.throws(() => serverUrl('https://user:secret@example.com'));
  assert.throws(() => serverUrl('https://example.com/api/'));
});

test('cooldown responses do not claim attendance succeeded', () => {
  assert.match(attendanceMessage('already_logged_in'), /wait five minutes/);
  assert.match(attendanceMessage('already_done'), /wait five minutes/);
  assert.match(attendanceMessage('logout'), /checked out/);
});

test('HTML, empty and malformed responses show a useful server error', async () => {
  for (const body of ['<!doctype html><html>Sign in</html>', '', '{broken']) {
    const api = new Api('http://127.0.0.1:8000', async () => new Response(body));
    await assert.rejects(api.session(), error => error instanceof ApiError && /invalid JSON response.*local Django backend/.test(error.message));
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
