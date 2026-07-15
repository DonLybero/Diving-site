import { test } from 'node:test';
import assert from 'node:assert/strict';
import { MemoryStore } from '../../lib/divelog/store.js';

const dive = (id, startedAt, durationSec = 2880) => ({ id, startedAt, durationSec, diveType: 'scuba', visibility: 'private' });

test('put/list/get/delete round trip, newest first', async () => {
  const store = await new MemoryStore().init();
  await store.putDives([dive('a', '2025-03-12T09:30:00'), dive('b', '2025-03-14T09:30:00'), dive('c', '2025-03-13T09:30:00')]);
  const list = await store.listDives();
  assert.deepEqual(list.map((d) => d.id), ['b', 'c', 'a']);
  assert.equal((await store.getDive('c')).startedAt, '2025-03-13T09:30:00');
  await store.deleteDive('c');
  assert.equal(await store.getDive('c'), undefined);
  assert.equal((await store.listDives()).length, 2);
});

test('upsert replaces by id', async () => {
  const store = await new MemoryStore().init();
  await store.putDives([dive('a', '2025-03-12T09:30:00')]);
  await store.putDives([{ ...dive('a', '2025-03-12T09:30:00'), notes: 'edited' }]);
  const list = await store.listDives();
  assert.equal(list.length, 1);
  assert.equal(list[0].notes, 'edited');
});

test('returned objects are copies, not live references', async () => {
  const store = await new MemoryStore().init();
  await store.putDives([dive('a', '2025-03-12T09:30:00')]);
  const got = await store.getDive('a');
  got.notes = 'mutated';
  assert.equal((await store.getDive('a')).notes, undefined);
});

test('imports and settings', async () => {
  const store = await new MemoryStore().init();
  await store.putImport({ id: 'i1', createdAt: '2025-03-12T10:00:00Z', imported: 3, skipped: 1 });
  await store.putImport({ id: 'i2', createdAt: '2025-03-13T10:00:00Z', imported: 5, skipped: 0 });
  assert.deepEqual((await store.listImports()).map((r) => r.id), ['i2', 'i1']);
  assert.equal(await store.getSetting('units'), undefined);
  await store.setSetting('units', 'imperial');
  assert.equal(await store.getSetting('units'), 'imperial');
  await store.setSetting('csvMapping', { Date: 'date', 'Max Depth': 'maxDepthM' });
  assert.deepEqual(await store.getSetting('csvMapping'), { Date: 'date', 'Max Depth': 'maxDepthM' });
});

test('clearAll wipes dives and imports but keeps settings', async () => {
  const store = await new MemoryStore().init();
  await store.putDives([dive('a', '2025-03-12T09:30:00')]);
  await store.putImport({ id: 'i1', createdAt: '2025-03-12T10:00:00Z' });
  await store.setSetting('units', 'imperial');
  await store.clearAll();
  assert.equal((await store.listDives()).length, 0);
  assert.equal((await store.listImports()).length, 0);
  assert.equal(await store.getSetting('units'), 'imperial');
});

test('putDives without id throws', async () => {
  const store = await new MemoryStore().init();
  await assert.rejects(() => store.putDives([{ startedAt: '2025-03-12T09:30:00' }]));
});
