import test from 'node:test';
import assert from 'node:assert/strict';
import { Api, ApiError, query, serverUrl } from '../src/api.ts';

test('server origins and filter encoding', () => {
  assert.equal(serverUrl(' https://example.com/ '), 'https://example.com');
  for (const value of ['file:///secret', 'https://user:pass@example.com', 'https://example.com/api/']) assert.throws(() => serverUrl(value));
  assert.equal(query({ start_date: '', page: 2, name: 'A&B' }), '?page=2&name=A%26B');
});
test('cookie credentials, CSRF bootstrap, rotation, and logout', async () => {
  const calls = [];
  const replies = [{ authenticated: false, csrf_token: 'initial' }, { username: 'admin', csrf_token: 'rotated' }, { success: true }];
  const api = new Api('https://example.com', async (url, options) => { calls.push({ url, ...options }); return Response.json(replies.shift()); });
  assert.equal(await api.login('admin', 'secret'), 'admin');
  await api.logout();
  assert.equal(calls[0].credentials, 'include');
  assert.equal(calls[1].headers['X-CSRFToken'], 'initial');
  assert.equal(calls[2].headers['X-CSRFToken'], 'rotated');
  assert.equal(calls[1].headers.Referer, 'https://example.com/');
  assert.equal(api.csrf, '');
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
test('validation, non-JSON errors, session expiry, and PDF bytes', async () => {
  let expired = false;
  const api = new Api('https://example.com', async () => Response.json({ errors: { employee_id: [{ message: 'Already exists.' }] } }, { status: 400 }));
  await assert.rejects(api.post('employees/create/', {}), /employee_id: Already exists/);
  const denied = new Api('https://example.com', async () => new Response('<html>Denied</html>', { status: 403 }));
  await assert.rejects(denied.get('dashboard/'), /CSRF verification/);
  const expiredApi = new Api('https://example.com', async () => Response.json({ error: 'Authentication required' }, { status: 401 }));
  expiredApi.onUnauthorized = () => { expired = true; };
  await assert.rejects(expiredApi.get('dashboard/'), ApiError); assert.equal(expired, true);
  const pdf = new Api('https://example.com', async () => new Response('%PDF-1.7', { headers: { 'Content-Type': 'application/pdf' } }));
  assert.equal(await (await pdf.response('report/pdf/')).text(), '%PDF-1.7');
});

test('expired password and logout sessions notify; invalid login does not', async () => {
  let expired = 0;
  const api = new Api('https://example.com', async () => Response.json({ error: 'Authentication required' }, { status: 401 }));
  api.onUnauthorized = () => expired++;
  for (const path of ['auth/password/', 'auth/logout/']) await assert.rejects(api.post(path, {}), ApiError);
  assert.equal(expired, 2);
  await assert.rejects(api.post('auth/login/', {}), ApiError);
  assert.equal(expired, 2);
});

test('management access is checked before entering admin', async () => {
  const employee = new Api('https://example.com', async () => Response.json({ error: 'Management access required' }, { status: 403 }));
  await assert.rejects(employee.requireManagement(), /Use the staff app/);
  const manager = new Api('https://example.com', async () => Response.json({ total_employees: 1 }));
  await manager.requireManagement();
});

test('HTML and malformed successful responses show a useful error instead of a JSON parse exception', async () => {
  for (const body of ['<!doctype html><html>Sign in</html>', '', '{broken']) {
    const api = new Api('https://example.com', async () => new Response(body));
    for (const request of [() => api.get('auth/session/'), () => api.post('auth/login/', {})]) {
      await assert.rejects(request, error => error instanceof ApiError && /invalid JSON response.*Check the backend URL/.test(error.message));
    }
  }
});

test('missing deployed mobile routes identify the URL and deployment fix', async () => {
  const api = new Api('https://example.com', async () => new Response('<html>Not Found</html>', { status: 404 }));
  await assert.rejects(api.session(), error => error instanceof ApiError && error.status === 404 && error.message.includes('https://example.com/api/mobile/auth/session/') && error.message.includes('deploy/restart'));
  const missing = new Api('https://example.com', async () => Response.json({ error: 'Not found' }, { status: 404 }));
  await assert.rejects(missing.get('employees/999/'), /Not found/);
});
