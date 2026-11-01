import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import vm from 'node:vm';
import ts from 'typescript';

const source = readFileSync(new URL('../src/notifications.tsx', import.meta.url), 'utf8');
const code = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS } }).outputText;

function notificationClient({ expoGo = false, received = true } = {}) {
  const exports = {};
  let callback;
  let removed = false;
  vm.runInNewContext(code, {
    exports,
    setTimeout(fn) { if (!received) queueMicrotask(fn); return 1; },
    clearTimeout() {},
    require(name) {
      if (name === 'react') return {};
      if (name === 'react-native') return { Platform: { OS: 'android' } };
      if (name === 'expo-constants') return { __esModule: true, default: { easConfig: { projectId: 'test-project' } } };
      if (name === 'expo') return { isRunningInExpoGo: () => expoGo };
      if (name === 'expo-notifications') return {
        AndroidImportance: { HIGH: 4 }, setNotificationHandler() {},
        async setNotificationChannelAsync() {},
        async getPermissionsAsync() { return { granted: true }; },
        async getExpoPushTokenAsync() { return { data: 'ExponentPushToken[device]' }; },
        addNotificationReceivedListener(fn) { callback = fn; return { remove() { removed = true; } }; },
      };
      throw new Error(name);
    },
  });
  return { exports, receive(id) { callback({ request: { content: { data: { test_id: id } } } }); }, removed: () => removed };
}

test('push test confirms receipt only for the matching test ID', async () => {
  const client = notificationClient();
  const paths = [];
  const api = { async post(path, data) {
    paths.push(path);
    if (path === 'notifications/test/') {
      client.receive('unrelated-test');
      client.receive(data.test_id);
      return { sent: true };
    }
    return {};
  } };
  assert.equal(await client.exports.testNotification(api), 'Received.');
  assert.deepEqual(paths, ['notifications/device/', 'notifications/test/']);
  assert.equal(client.removed(), true);
});

test('accepted push without observed receipt reports Sent and removes listener', async () => {
  const client = notificationClient({ received: false });
  assert.equal(await client.exports.testNotification({ async post() { return { sent: true }; } }), 'Sent.');
  assert.equal(client.removed(), true);
});

test('Expo Go test is unavailable and failed sends clean up listeners', async () => {
  await assert.rejects(notificationClient({ expoGo: true }).exports.testNotification({}), /Use the installed app/);
  const client = notificationClient();
  await assert.rejects(client.exports.testNotification({ async post(path) { if (path === 'notifications/test/') throw new Error('Not sent.'); } }), /Not sent/);
  assert.equal(client.removed(), true);
});

for (const [platform, expoGo, expectedLoads] of [['android', true, 0], ['ios', true, 0], ['web', false, 0], ['android', false, 1]]) {
  test(`notification import is safe on ${platform}, Expo Go=${expoGo}`, () => {
    let loads = 0;
    let handlers = 0;
    const exports = {};
    vm.runInNewContext(code, {
      exports,
      require(name) {
        if (name === 'react') return {};
        if (name === 'react-native') return { Platform: { OS: platform } };
        if (name === 'expo-constants') return { default: {} };
        if (name === 'expo') return { isRunningInExpoGo: () => expoGo };
        if (name === 'expo-notifications') {
          loads++;
          assert.equal(expoGo, false, 'Expo Go must never evaluate the unsupported native module');
          return { setNotificationHandler() { handlers++; } };
        }
        throw new Error(`Unexpected import ${name}`);
      },
    });
    assert.equal(loads, expectedLoads);
    assert.equal(handlers, expectedLoads);
    assert.equal(typeof exports.useAttendanceAlerts, 'function');
  });
}
