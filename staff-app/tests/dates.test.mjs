import test from 'node:test';
import assert from 'node:assert/strict';
import { clockTime, dateKey, dateValid, monthCells, monthRange, shiftMonth, validateRange } from '../src/dates.ts';

test('calendar times use 12-hour format at midnight, noon, and evening', () => {
  assert.equal(clockTime('00:05:00'), '12:05 AM');
  assert.equal(clockTime('12:00:00'), '12:00 PM');
  assert.equal(clockTime('23:45:10'), '11:45 PM');
  assert.equal(clockTime(null), '—');
});

test('calendar cells use Monday alignment and correct leap days', () => {
  const october = monthCells(2026, 10);
  assert.deepEqual(october.slice(0, 4), [null, null, null, '2026-10-01']);
  assert.equal(october.length % 7, 0);
  assert.equal(october.filter(Boolean).length, 31);
  assert.ok(monthCells(2024, 2).includes('2024-02-29'));
  assert.ok(!monthCells(2025, 2).includes('2025-02-29'));
  assert.equal(monthCells(1, 1).filter(Boolean).length, 31);
});
test('month navigation rolls years and local selection retains the local date', () => {
  assert.deepEqual(shiftMonth(2026, 12, 1), { year: 2027, month: 1 });
  assert.deepEqual(shiftMonth(2026, 1, -1), { year: 2025, month: 12 });
  assert.equal(dateKey(new Date(2026, 9, 25, 23, 30)), '2026-10-25');
});
test('invalid dates and reversed filters are rejected', () => {
  assert.equal(dateValid('2026-02-30'), false);
  assert.equal(dateValid('2024-02-29'), true);
  assert.throws(() => validateRange('2026-10-25', '2026-10-01'));
  assert.doesNotThrow(() => validateRange('', ''));
});

test('report default includes the entire month, including leap days and year end', () => {
  assert.deepEqual(monthRange(new Date(2026, 9, 25)), { start_date: '2026-10-01', end_date: '2026-10-31' });
  assert.deepEqual(monthRange(new Date(2024, 1, 15)), { start_date: '2024-02-01', end_date: '2024-02-29' });
  assert.deepEqual(monthRange(new Date(2025, 1, 15)), { start_date: '2025-02-01', end_date: '2025-02-28' });
  assert.deepEqual(monthRange(new Date(2026, 11, 31)), { start_date: '2026-12-01', end_date: '2026-12-31' });
});
