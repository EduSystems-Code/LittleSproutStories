/* LittleSprout service worker.
   Strategy:
     - shell (all top-level pages, manifest, icons) precached on install
     - everything else (books, games, sprites) cached the first time it is opened,
       so a book a child has read once will still open with no connection.
   Bump CACHE_VERSION whenever site files change, so old copies are cleared. */

const CACHE_VERSION = 'littlesprout-v17';

const SHELL = [
  './',
  './index.html',
  './characters.html',
  './privacy.html',
  './grants.html',
  './stats.html',
  './rewards.html',
  './manifest.json',
  './assets/icons/icon-192.png',
  './assets/icons/icon-512.png'
];

self.addEventListener('install', function (event) {
  event.waitUntil(
    caches.open(CACHE_VERSION)
      .then(function (cache) {
        // addAll is all-or-nothing; add individually so one miss can't break install
        return Promise.all(SHELL.map(function (url) {
          return cache.add(url).catch(function () { return null; });
        }));
      })
      .then(function () { return self.skipWaiting(); })
  );
});

self.addEventListener('activate', function (event) {
  event.waitUntil(
    caches.keys().then(function (keys) {
      return Promise.all(keys.map(function (k) {
        if (k !== CACHE_VERSION) return caches.delete(k);
      }));
    }).then(function () { return self.clients.claim(); })
  );
});

function putInCache(req, res) {
  if (res && res.status === 200 && res.type === 'basic') {
    var copy = res.clone();
    caches.open(CACHE_VERSION).then(function (cache) { cache.put(req, copy); });
  }
  return res;
}

self.addEventListener('fetch', function (event) {
  var req = event.request;

  // only handle same-origin GETs; let fonts/CDNs go straight to network
  if (req.method !== 'GET') return;
  if (new URL(req.url).origin !== self.location.origin) return;

  // HTML pages (navigations): network-first. A page that's already cached
  // used to be served instantly and stale -- CACHE_VERSION bumping only
  // helps from the SECOND visit onward, since the first post-deploy load
  // still hit the old cache entry before the background refresh finished.
  // Network-first means anyone online always sees the current page; the
  // cache is only the fallback when there's no connection at all.
  if (req.mode === 'navigate' || (req.headers.get('accept') || '').indexOf('text/html') !== -1) {
    event.respondWith(
      // 'reload' bypasses the browser's own HTTP cache, not just the SW
      // cache above it -- fetch(req) alone can still return a
      // browser-cached response for a page with no explicit Cache-Control
      // header (GitHub Pages doesn't set one), which would silently
      // defeat network-first the same way cache-first did.
      fetch(req, { cache: 'reload' }).then(function (res) {
        return putInCache(req, res);
      }).catch(function () {
        return caches.match(req).then(function (cached) {
          return cached || caches.match('./index.html');
        });
      })
    );
    return;
  }

  // Everything else (sprites, backgrounds, icons, manifest): cache-first
  // with a background refresh. These are content-addressed by filename
  // and change rarely relative to page markup, so instant-from-cache is
  // the right tradeoff -- especially for offline reading of a book a
  // child has already opened once.
  event.respondWith(
    caches.match(req).then(function (cached) {
      var network = fetch(req).then(function (res) {
        return putInCache(req, res);
      }).catch(function () {
        return cached;
      });
      return cached || network;
    })
  );
});
