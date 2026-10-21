const CACHE = 'voto27-v1-8aabc458266a';
const ASSETS = ['/', '/index.html', '/manifest.webmanifest', '/icons/voto27-icon.svg'];
self.addEventListener('install', event => {
  event.waitUntil(caches.open(CACHE).then(cache => cache.addAll(ASSETS)));
  self.skipWaiting();
});
self.addEventListener('activate', event => {
  event.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(key => key.startsWith('voto27-') && key !== CACHE).map(key => caches.delete(key)))));
  self.clients.claim();
});

async function fixHomepageDate(response) {
  const contentType = response.headers.get('content-type') || '';
  if (!contentType.includes('text/html')) return response;
  let html = await response.text();
  html = html.replace(
    /<div class="kicker">Media VOTO27 • \d{1,2} [^<]+ 2026<\/div>/,
    '<div class="kicker">Aggiornato al <time id="todayDate"></time></div>'
  );
  const headers = new Headers(response.headers);
  headers.set('Cache-Control', 'no-cache, no-store, must-revalidate');
  return new Response(html, {status: response.status, statusText: response.statusText, headers});
}

self.addEventListener('fetch', event => {
  if (event.request.method !== 'GET' || new URL(event.request.url).origin !== self.location.origin) return;
  event.respondWith((async () => {
    try {
      const response = await fetch(event.request, {cache:'no-store'});
      if (response.ok) {
        const copy = response.clone();
        event.waitUntil(caches.open(CACHE).then(cache => cache.put(event.request, copy)));
      }
      if (event.request.mode === 'navigate' || new URL(event.request.url).pathname.endsWith('/index.html')) return fixHomepageDate(response);
      return response;
    } catch(e) {
      const cached = await caches.match(event.request) || (event.request.mode === 'navigate' ? await caches.match('/index.html') : null);
      if (!cached) return Response.error();
      if (event.request.mode === 'navigate' || new URL(event.request.url).pathname.endsWith('/index.html')) return fixHomepageDate(cached);
      return cached;
    }
  })());
});

