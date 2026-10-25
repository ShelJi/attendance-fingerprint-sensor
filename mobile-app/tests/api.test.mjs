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
