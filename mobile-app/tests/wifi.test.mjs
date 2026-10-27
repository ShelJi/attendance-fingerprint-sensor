import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import ts from 'typescript';
const code = ts.transpileModule(fs.readFileSync(new URL('../src/wifi.ts', import.meta.url), 'utf8'), { compilerOptions: { module: ts.ModuleKind.CommonJS } }).outputText;
function fixture({ os = 'android', granted = true, enabled = true, network = { type: 'wifi', isConnected: true, details: { ssid: 'My Hotspot', bssid: 'AA:BB:CC:11:22:33' } } } = {}) {
  const calls = [];
  const context = { exports: {}, require: name => ({
    'react-native': { Platform: { OS: os } },
    'expo-location': { requestForegroundPermissionsAsync: async () => ({ granted }), hasServicesEnabledAsync: async () => enabled },
    '@react-native-community/netinfo': { __esModule: true, default: { configure: options => calls.push(options), fetch: async type => { assert.equal(type, 'wifi'); return network; } } },
  })[name] };
  vm.runInNewContext(code, context);
  return { capture: context.exports.captureWifi, calls };
}
test('captures connected hotspot identifiers and enables iOS SSID access', async () => {
  for (const os of ['android', 'ios']) {
    const f = fixture({ os });
    const data = await f.capture();
    assert.equal(data.wifi_ssid, 'My Hotspot');
    assert.equal(data.wifi_bssid, 'aa:bb:cc:11:22:33');
    assert.equal(f.calls[0].shouldFetchWiFiSSID, os === 'ios');
  }
});
test('rejects browser, denied permission, disabled location, and disconnected Wi-Fi', async () => {
  for (const [options, message] of [[{ os: 'web' }, /Browsers/], [{ granted: false }, /permission/], [{ enabled: false }, /location services/], [{ network: { type: 'cellular', isConnected: true } }, /Connect this phone/]]) {
    await assert.rejects(fixture(options).capture(), message);
  }
});
test('rejects missing or redacted Wi-Fi identifiers', async () => {
  for (const details of [{}, { ssid: '<unknown ssid>', bssid: 'aa:bb:cc:11:22:33' }, ...['02:00:00:00:00:00', '00:00:00:00:00:00', 'invalid', null].map(bssid => ({ ssid: 'Hotspot', bssid }))]) {
    await assert.rejects(fixture({ network: { type: 'wifi', isConnected: true, details } }).capture(), /unavailable/);
  }
});

