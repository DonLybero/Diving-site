// Dive log service worker: makes divelog.html work offline after the first
// visit. Deliberately narrow — it only ever answers for the dive log's own
// assets (whitelist below); every other request on the site is untouched
// (no respondWith → browser default), so the SPA/static pages can't be
// affected by a stale cache. Strategy is network-first with cache fallback:
// deploys are picked up immediately when online, the cache only serves when
// the network is gone.

const CACHE = 'diveszn-divelog-v1';

const ASSETS = [
  'divelog.html',
  'divelog.js',
  'divelog.webmanifest',
  'assets/divelog-icon.svg',
  'assets/divelog-icon-192.png',
  'assets/divelog-icon-512.png',
  'vendor/fxp.esm.min.js',
  'vendor/fitsdk.esm.min.js',
  'lib/divelog/types.js',
  'lib/divelog/encoding.js',
  'lib/divelog/values.js',
  'lib/divelog/xml.js',
  'lib/divelog/units.js',
  'lib/divelog/dedupe.js',
  'lib/divelog/store.js',
  'lib/divelog/pipeline.js',
  'lib/divelog/export-uddf.js',
  'lib/divelog/parsers/index.js',
  'lib/divelog/parsers/uddf.js',
  'lib/divelog/parsers/subsurface.js',
  'lib/divelog/parsers/suunto-sml.js',
  'lib/divelog/parsers/garmin-fit.js',
  'lib/divelog/parsers/csv.js',
];

const BASE = new URL('.', self.location).href; // works at / and at /Diving-site/
const CACHEABLE = new Set(ASSETS.map((p) => BASE + p));

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE)
      .then((cache) => cache.addAll(ASSETS))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k.startsWith('diveszn-divelog-') && k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (event) => {
  if (event.request.method !== 'GET') return;
  // normalize: hash-router navigations arrive as 'divelog.html#…'
  const u = new URL(event.request.url);
  const clean = u.origin + u.pathname;
  if (!CACHEABLE.has(clean)) return; // everything else: hands off

  event.respondWith(
    fetch(event.request)
      .then((response) => {
        if (response && response.ok) {
          const copy = response.clone();
          caches.open(CACHE).then((cache) => cache.put(clean, copy));
        }
        return response;
      })
      .catch(() => caches.match(clean))
  );
});
