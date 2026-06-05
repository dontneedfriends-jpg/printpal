var CACHE = 'printpal-v4';
var STATIC_URLS = [
  '/',
  '/static/style.css',
  '/static/app.js',
  '/static/bulk-actions.js',
  '/static/icons/icon.svg',
  '/about',
];

self.addEventListener('install', function(e) {
  e.waitUntil(
    caches.open(CACHE).then(function(cache) {
      return cache.addAll(STATIC_URLS);
    }).then(function() {
      return self.skipWaiting();
    })
  );
});

self.addEventListener('activate', function(e) {
  e.waitUntil(
    caches.keys().then(function(keys) {
      return Promise.all(
        keys.filter(function(k) { return k !== CACHE; }).map(function(k) { return caches.delete(k); })
      );
    }).then(function() {
      return self.clients.claim();
    })
  );
});

self.addEventListener('fetch', function(e) {
  var url = new URL(e.request.url);
  if (url.pathname === '/sw.js' || url.pathname === '/manifest.json') {
    e.respondWith(fetch(e.request));
    return;
  }
  if (url.pathname.startsWith('/theme.css') || url.pathname.startsWith('/printers/') || url.pathname.startsWith('/filaments/') || url.pathname.startsWith('/shpoolken/') || url.pathname.startsWith('/history/') || url.pathname.startsWith('/calculator/')) {
    e.respondWith(networkFirst(e.request));
    return;
  }
  e.respondWith(cacheFirst(e.request));
});

function networkFirst(request) {
  return fetch(request).then(function(resp) {
    if (resp && resp.ok) {
      var clone = resp.clone();
      caches.open(CACHE).then(function(cache) { cache.put(request, clone); });
    }
    return resp;
  }).catch(function() {
    return caches.match(request);
  });
}

function cacheFirst(request) {
  return caches.match(request).then(function(resp) {
    return resp || fetch(request).then(function(netResp) {
      var clone = netResp.clone();
      caches.open(CACHE).then(function(cache) { cache.put(request, clone); });
      return netResp;
    });
  });
}