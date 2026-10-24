// Service worker: the app works offline with the last data it saw.
//  · Page and data (same origin): network first, so new data shows up at once; the cache is the fallback.
//  · Libraries, fonts and the municipalities map (CDNs, versioned URLs): cache first.
//  · Crests (CloudFront) and the calendars (cal/*.ics) are not cached: offline the badges show initials.
const VERSION = 'cadet-v2';
const CORE = ['./', 'index.html', 'data/cadet-data.js', 'data/cadet-box.js', 'manifest.webmanifest', 'icons/icon.svg', 'icons/icon-192.png'];
const CDN = /^https:\/\/(cdnjs\.cloudflare\.com|cdn\.jsdelivr\.net|fonts\.googleapis\.com|fonts\.gstatic\.com)\//;

self.addEventListener('install', e => {
  e.waitUntil(caches.open(VERSION).then(c => c.addAll(CORE)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', e => {
  e.waitUntil(caches.keys()
    .then(keys => Promise.all(keys.filter(k => k !== VERSION).map(k => caches.delete(k))))
    .then(() => self.clients.claim()));
});

self.addEventListener('fetch', e => {
  const req = e.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  if (url.origin === location.origin) {
    if (url.pathname.endsWith('.ics')) return;
    e.respondWith(networkFirst(req));
  } else if (CDN.test(req.url)) {
    e.respondWith(cacheFirst(req));
  }
});

async function networkFirst(req) {
  const cache = await caches.open(VERSION);
  try {
    const res = await fetch(req);
    if (res.ok) cache.put(req, res.clone());
    return res;
  } catch (err) {
    // The URL may carry ?v=… or a different path to the page: fall back to the cached page
    return (await cache.match(req, { ignoreSearch: true }))
        || (req.mode === 'navigate' && await cache.match('index.html'))
        || Response.error();
  }
}

async function cacheFirst(req) {
  const cache = await caches.open(VERSION);
  const hit = await cache.match(req);
  if (hit) return hit;
  const res = await fetch(req);
  if (res.ok || res.type === 'opaque') cache.put(req, res.clone());
  return res;
}
