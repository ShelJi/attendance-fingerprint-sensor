import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import vm from 'node:vm';
import ts from 'typescript';

const source = readFileSync(new URL('../src/notifications.tsx', import.meta.url), 'utf8');
const code = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS } }).outputText;

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
