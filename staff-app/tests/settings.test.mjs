import test from 'node:test';
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import fs from 'node:fs';
import { DEFAULT_BACKEND_URL } from '../src/settings.ts';
const require = createRequire(import.meta.url);
const initialBackend = process.env.EXPO_PUBLIC_API_URL?.trim() || '';
const configure = require('../app.config.js');
const config = require('../app.json').expo;

test('backend environment overrides local configuration', t => {
  t.mock.method(fs, 'existsSync', () => false);
  assert.equal(DEFAULT_BACKEND_URL, initialBackend);
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

test('Android release profiles build a versioned bundle with Firebase configured', () => {
  const eas = require('../eas.json');
  assert.equal(eas.cli.appVersionSource, 'remote');
  assert.equal(eas.build.production.autoIncrement, true);
  assert.equal(eas.build.production.distribution, 'store');
  assert.equal(eas.build.production.android.buildType, 'app-bundle');
  assert.equal(eas.build.preview.android.buildType, 'apk');
  const before = process.env.GOOGLE_SERVICES_JSON;
  try {
    delete process.env.GOOGLE_SERVICES_JSON;
    assert.equal(configure({ config }).android.googleServicesFile, './google-services.json');
    process.env.GOOGLE_SERVICES_JSON = '/eas/firebase.json';
    assert.equal(configure({ config }).android.googleServicesFile, '/eas/firebase.json');
  } finally {
    if (before === undefined) delete process.env.GOOGLE_SERVICES_JSON;
    else process.env.GOOGLE_SERVICES_JSON = before;
  }
});
