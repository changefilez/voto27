const CACHE = 'voto27-v1-supermedia-20261029';
const ASSETS = ['/', '/index.html', '/manifest.webmanifest', '/icons/voto27-icon.svg', '/data/supermedia.json'];
self.addEventListener('install', event => {
  event.waitUntil(caches.open(CACHE).then(cache => cache.addAll(ASSETS)));
  self.skipWaiting();
});
self.addEventListener('activate', event => {
  event.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(key => key.startsWith('voto27-') && key !== CACHE).map(key => caches.delete(key)))));
  self.clients.claim();
});

function itDate(iso) {
  const m = ['gennaio','febbraio','marzo','aprile','maggio','giugno','luglio','agosto','settembre','ottobre','novembre','dicembre'];
  const p = iso.split('-').map(Number);
  return `${p[2]} ${m[p[1]-1]} ${p[0]}`;
}

async function supermediaCard() {
  try {
    let r;
    try { r = await fetch('/data/supermedia.json', {cache:'no-store'}); } catch(e) { r = await caches.match('/data/supermedia.json'); }
    if (!r || !r.ok) return '';
    const s = await r.json();
    const labels = {fdi:'Fratelli d’Italia',pd:'Partito Democratico',m5s:'Movimento 5 Stelle',fi:'Forza Italia',fn:'Futuro Nazionale',avs:'Alleanza Verdi e Sinistra',lega:'Lega',azione:'Azione',iv:'Italia Viva',europa:'+Europa',nm:'Noi Moderati'};
    const rows = Object.entries(s.values).map(([k,v]) => `<div class="single-row party-${k}"><div class="single-head"><span class="single-name"><i class="party-dot"></i>${labels[k] || k}</span><b>${String(v).replace('.',',')}%</b></div></div>`).join('');
    return `<section class="card" id="supermedia-youtrend"><div class="kicker">Benchmark esterno • ${itDate(s.updated)}</div><h2>Supermedia YouTrend</h2><p class="sub">Confronto indipendente con la media VOTO27. Non entra nel calcolo VOTO27, nella copertura o negli snapshot, per evitare il doppio conteggio dei sondaggi sottostanti.</p><div class="single-poll-chart">${rows}</div><div class="sourcebox"><b>Supermedia YouTrend</b> · ${itDate(s.updated)}. Benchmark esterno, non un nuovo sondaggio VOTO27. <a href="${s.source_url}" target="_blank" rel="noopener noreferrer">Fonte YouTrend ↗</a></div></section>`;
  } catch(e) { return ''; }
}

async function fixHomepageDate(response) {
  const contentType = response.headers.get('content-type') || '';
  if (!contentType.includes('text/html')) return response;
  let html = await response.text();
  html = html.replace(
    /<div class="kicker">Media VOTO27 • \d{1,2} [^<]+ 2026<\/div>/,
    '<div class="kicker">Aggiornato al <time id="todayDate"></time></div>'
  );
  if (!html.includes('id="supermedia-youtrend"')) {
    const card = await supermediaCard();
    if (card) html = html.replace('<section class="card" id="rilevazioni-recenti">', card + '<section class="card" id="rilevazioni-recenti">');
  }
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
