/* LittleSprout service worker.
   Strategy:
     - shell (home, characters, privacy, manifest, icons) precached on install
     - everything else (books, games, sprites) cached the first time it is opened,
       so a book a child has read once will still open with no connection.
   Bump CACHE_VERSION whenever site files change, so old copies are cleared. */

const CACHE_VERSION = 'littlesprout-v8';

const SHELL = [
  './',
  './index.html',
  './characters.html',
  './privacy.html',
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

self.addEventListener('fetch', function (event) {
  var req = event.request;

  // only handle same-origin GETs; let fonts/CDNs go straight to network
  if (req.method !== 'GET') return;
  if (new URL(req.url).origin !== self.location.origin) return;

  event.respondWith(
    caches.match(req).then(function (cached) {
      var network = fetch(req).then(function (res) {
        if (res && res.status === 200 && res.type === 'basic') {
          var copy = res.clone();
          caches.open(CACHE_VERSION).then(function (cache) {
            cache.put(req, copy);
          });
        }
        return res;
      }).catch(function () {
        // offline and not cached: fall back to the home page for navigations
        if (req.mode === 'navigate') return caches.match('./index.html');
        return cached;
      });

      // serve cache immediately when we have it, refresh in background
      return cached || network;
    })
  );
});
