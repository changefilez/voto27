/* Cache exact responses only. Poll dates and figures are generated together. */
const CACHE = 'voto27-v1-586228b95ac2';
const BASE = new URL('./', self.registration.scope);
const asset = path => new URL(path, BASE).href;
const ASSETS = ['index.html', 'assets/app.js', 'assets/enhancements.css',
  'manifest.webmanifest', 'icons/voto27-icon.svg', 'icons/icon-192.png',
  'icons/icon-512.png', 'icons/apple-touch-icon.png'].map(asset);
self.addEventListener('install', event => {
  event.waitUntil((async () => {
    const cache = await caches.open(CACHE);
    await cache.addAll(ASSETS);
    await self.skipWaiting();
  })());
});
self.addEventListener('activate', event => {
  event.waitUntil((async () => {
    await Promise.all((await caches.keys()).filter(key => key.startsWith('voto27-') && key !== CACHE).map(key => caches.delete(key)));
    await self.clients.claim();
  })());
});
self.addEventListener('fetch', event => {
  const url = new URL(event.request.url);
  if (event.request.method !== 'GET' || url.origin !== BASE.origin || !url.pathname.startsWith(BASE.pathname)) return;
  const home = event.request.mode === 'navigate' && (url.pathname === BASE.pathname || url.pathname === new URL('index.html', BASE).pathname);
  // Do not cache arbitrary URLs or replace real 404s with the homepage.
  const key = home ? asset('index.html') : url.href;
  if (!home && !ASSETS.includes(key)) return;
  const network = (async () => {
    const response = await fetch(event.request, {cache: 'no-store'});
    if (response.ok) await (await caches.open(CACHE)).put(key, response.clone());
    return response;
  })();
  // A background refresh must remain alive even if the offline fallback wins.
  event.waitUntil(network.catch(() => {}));
  event.respondWith((async () => {
    let timer;
    try {
      // Prefer the latest server version; a slow connection may use the saved copy.
      const response = await Promise.race([network, new Promise((_, reject) => {
        timer = setTimeout(() => reject(new Error('Network timeout')), 4500);
      })]);
      return response;
    } catch (_) {
      const cached = await (await caches.open(CACHE)).match(key);
      return cached || network.catch(() => Response.error());
    } finally { clearTimeout(timer); }
  })());
});

