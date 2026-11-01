import test from 'node:test';
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { DEFAULT_BACKEND_URL } from '../src/settings.ts';
const require = createRequire(import.meta.url);
const configure = require('../app.config.js');
const config = require('../app.json').expo;

test('backend comes only from the build environment', () => {
  assert.equal(DEFAULT_BACKEND_URL, process.env.EXPO_PUBLIC_API_URL?.trim() || '');
  const before = process.env.EXPO_PUBLIC_API_URL;
  try {
    delete process.env.EXPO_PUBLIC_API_URL;
    assert.throws(() => configure({ config }), /Set EXPO_PUBLIC_API_URL/);
    process.env.EXPO_PUBLIC_API_URL = 'https://example.com';
    assert.equal(configure({ config }).android.package, config.android.package);
    assert.equal(configure({ config }).plugins.includes('./plugins/with-http-backend'), false);
    process.env.EXPO_PUBLIC_API_URL = 'http://192.168.1.10:8000';
    const http = configure({ config });
    assert.ok(http.plugins.includes('./plugins/with-http-backend'));
    assert.equal(http.ios.infoPlist.NSAppTransportSecurity.NSAllowsArbitraryLoads, true);
    process.env.EXPO_PUBLIC_API_URL = 'https://example.com/api/mobile/';
    assert.throws(() => configure({ config }), /server origin/);
  } finally {
    if (before === undefined) delete process.env.EXPO_PUBLIC_API_URL;
    else process.env.EXPO_PUBLIC_API_URL = before;
  }
});
