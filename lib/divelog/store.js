// Thin data-access layer (PRD §6): the store is swappable and no IndexedDB
// call ever appears in UI code. IndexedDBStore backs the live page;
// MemoryStore backs node tests and is the template for a Phase-2 synced store.
//
// Store interface (all methods async):
//   init()                    open/prepare the store
//   listDives()               → CanonicalDive[] newest-first
//   getDive(id)               → CanonicalDive | undefined
//   putDives(dives)           bulk upsert (dives must carry ids)
//   deleteDive(id)
//   clearAll()                wipe dives + imports ("delete all my dives")
//   putImport(rec) / listImports()  import audit records, newest-first
//   getSetting(key) / setSetting(key, value)

import { startMs } from './dedupe.js';

const byStartDesc = (a, b) => startMs(b) - startMs(a);
const byCreatedDesc = (a, b) => String(b.createdAt || '').localeCompare(String(a.createdAt || ''));

export class MemoryStore {
  constructor() {
    this.dives = new Map();
    this.imports = new Map();
    this.settings = new Map();
  }
  async init() { return this; }
  async listDives() { return [...this.dives.values()].map((d) => structuredClone(d)).sort(byStartDesc); }
  async getDive(id) { const d = this.dives.get(id); return d ? structuredClone(d) : undefined; }
  async putDives(dives) { for (const d of dives) { if (!d.id) throw new Error('dive without id'); this.dives.set(d.id, structuredClone(d)); } }
  async deleteDive(id) { this.dives.delete(id); }
  async clearAll() { this.dives.clear(); this.imports.clear(); }
  async putImport(rec) { if (!rec.id) throw new Error('import without id'); this.imports.set(rec.id, structuredClone(rec)); }
  async listImports() { return [...this.imports.values()].map((r) => structuredClone(r)).sort(byCreatedDesc); }
  async getSetting(key) { return this.settings.has(key) ? structuredClone(this.settings.get(key)) : undefined; }
  async setSetting(key, value) { this.settings.set(key, structuredClone(value)); }
}

const DB_NAME = 'diveszn-divelog';
const DB_VERSION = 1;

function req(r) {
  return new Promise((resolve, reject) => {
    r.onsuccess = () => resolve(r.result);
    r.onerror = () => reject(r.error);
  });
}

function txDone(tx) {
  return new Promise((resolve, reject) => {
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
    tx.onabort = () => reject(tx.error || new Error('transaction aborted'));
  });
}

export class IndexedDBStore {
  constructor(name = DB_NAME) { this.name = name; this.db = null; }

  async init() {
    if (this.db) return this;
    const open = indexedDB.open(this.name, DB_VERSION);
    open.onupgradeneeded = () => {
      const db = open.result;
      if (!db.objectStoreNames.contains('dives')) db.createObjectStore('dives', { keyPath: 'id' });
      if (!db.objectStoreNames.contains('imports')) db.createObjectStore('imports', { keyPath: 'id' });
      if (!db.objectStoreNames.contains('settings')) db.createObjectStore('settings', { keyPath: 'key' });
    };
    this.db = await req(open);
    return this;
  }

  _store(name, mode = 'readonly') { return this.db.transaction(name, mode).objectStore(name); }

  async listDives() { return (await req(this._store('dives').getAll())).sort(byStartDesc); }
  async getDive(id) { return req(this._store('dives').get(id)); }
  async putDives(dives) {
    const tx = this.db.transaction('dives', 'readwrite');
    const st = tx.objectStore('dives');
    for (const d of dives) { if (!d.id) throw new Error('dive without id'); st.put(d); }
    await txDone(tx);
  }
  async deleteDive(id) {
    const tx = this.db.transaction('dives', 'readwrite');
    tx.objectStore('dives').delete(id);
    await txDone(tx);
  }
  async clearAll() {
    const tx = this.db.transaction(['dives', 'imports'], 'readwrite');
    tx.objectStore('dives').clear();
    tx.objectStore('imports').clear();
    await txDone(tx);
  }
  async putImport(rec) {
    if (!rec.id) throw new Error('import without id');
    const tx = this.db.transaction('imports', 'readwrite');
    tx.objectStore('imports').put(rec);
    await txDone(tx);
  }
  async listImports() { return (await req(this._store('imports').getAll())).sort(byCreatedDesc); }
  async getSetting(key) {
    const row = await req(this._store('settings').get(key));
    return row ? row.value : undefined;
  }
  async setSetting(key, value) {
    const tx = this.db.transaction('settings', 'readwrite');
    tx.objectStore('settings').put({ key, value });
    await txDone(tx);
  }
}

/** The page's store: IndexedDB in the browser. */
export async function openDefaultStore() {
  return new IndexedDBStore().init();
}
