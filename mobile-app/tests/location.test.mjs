import test from 'node:test';
import assert from 'node:assert/strict';
import { googleMapsUrl } from '../src/location.ts';

test('map links preserve recorded coordinates without rounding', () => {
  const url = new URL(googleMapsUrl(10.1234567, -76.7654321));
  assert.equal(url.origin, 'https://www.google.com');
  assert.equal(url.searchParams.get('query'), '10.1234567,-76.7654321');
  assert.equal(url.searchParams.get('api'), '1');
  for (const point of [[NaN, 1], [91, 1], [1, 181]]) assert.throws(() => googleMapsUrl(...point), /unavailable/);
});
