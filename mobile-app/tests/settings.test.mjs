import test from 'node:test';
import assert from 'node:assert/strict';
import { configuredBackend, DEFAULT_BACKEND_URL } from '../src/settings.ts';

test('new installs and the old hosted default use the local backend', () => {
  assert.equal(configuredBackend(null), DEFAULT_BACKEND_URL);
  assert.equal(configuredBackend('https://s.plsofttech.com'), DEFAULT_BACKEND_URL);
  assert.equal(configuredBackend('http://192.168.1.10:8000'), 'http://192.168.1.10:8000');
});
