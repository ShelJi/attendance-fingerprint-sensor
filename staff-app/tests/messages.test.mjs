import test from 'node:test';
import assert from 'node:assert/strict';
import { simpleError } from '../src/messages.ts';

test('staff errors stay brief without exposing platform setup details', () => {
  assert.equal(simpleError('Connect to your office Wi-Fi. The app needs permission to read its SSID/BSSID; iOS requires a signed build with Wi-Fi access enabled.'), 'Connect to the Wi-Fi.');
  assert.equal(simpleError('Connect to the Wi-Fi.'), 'Connect to the Wi-Fi.');
  assert.equal(simpleError('Could not reach the server. Check its URL, network connection, and HTTPS certificate.'), "Can't connect.");
});
