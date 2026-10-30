/* Service worker: app-schil + data + foto's offline. Kaarttegels worden gecachet zodra ze gezien zijn. */
const VERSION = 'ish-e5e6e86a20';
const SHELL = ['./', 'index.html', 'style.css', 'config.js', 'app.js', 'plan.js', 'qr.js', 'social.js', 'data/venues.json', 'data/agenda.json', 'manifest.webmanifest',
  'img/icon-192.png', 'img/icon-512.png',
  'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css', 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js'];
const TILE_LIMIT = 600;

self.addEventListener('install', e => {
  // cache: 'reload': altijd vers van de server, niet de oude versie uit de browsercache
  e.waitUntil(caches.open(VERSION).then(c => c.addAll(SHELL.map(u => new Request(u, { cache: 'reload' })))).then(() => self.skipWaiting()));
});
self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== VERSION && k !== 'tiles' && k !== 'photos').map(k => caches.delete(k)))).then(() => self.clients.claim()));
});

async function trimCache(name, limit) {
  const c = await caches.open(name); const keys = await c.keys();
  if (keys.length > limit) await Promise.all(keys.slice(0, keys.length - limit).map(k => c.delete(k)));
}

// meldingen: "Jonas zoekt jullie" (SOS-trilling), "Sanne staat hier", uitnodigingen
self.addEventListener('push', e => {
  let m = {};
  try { m = e.data ? e.data.json() : {}; } catch { m = { title: 'Ik sta hier', body: e.data && e.data.text() }; }
  e.waitUntil(self.registration.showNotification(m.title || 'Ik sta hier', {
    body: m.body || '', icon: 'img/icon-192.png', badge: 'img/icon-192.png', tag: m.tag, renotify: !!m.tag,
    vibrate: m.vibrate, requireInteraction: !!m.urgent, data: { url: m.url || '' },
  }));
});
self.addEventListener('notificationclick', e => {
  e.notification.close();
  const hash = (e.notification.data && e.notification.data.url) || '';
  e.waitUntil(self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then(list => {
    const c = list.find(w => new URL(w.url).pathname.startsWith(new URL(self.registration.scope).pathname));
    if (c) { c.postMessage({ open: hash }); return c.focus(); }
    return self.clients.openWindow(self.registration.scope + hash);
  }));
});

self.addEventListener('fetch', e => {
  const url = new URL(e.request.url);
  if (e.request.method !== 'GET' || url.pathname.includes('/api/')) return; // server-API nooit cachen
  // kaarttegels: cache first, bijvullen
  if (url.hostname.endsWith('openstreetmap.org')) {
    e.respondWith(caches.open('tiles').then(async c => {
      const hit = await c.match(e.request); if (hit) return hit;
      try { const r = await fetch(e.request); if (r.ok) { c.put(e.request, r.clone()); trimCache('tiles', TILE_LIMIT); } return r; }
      catch { return new Response('', { status: 503 }); }
    }));
    return;
  }
  // venue-foto's: cache first
  if (url.pathname.includes('/img/venues/')) {
    e.respondWith(caches.open('photos').then(async c => {
      const hit = await c.match(e.request); if (hit) return hit;
      try { const r = await fetch(e.request); if (r.ok) c.put(e.request, r.clone()); return r; }
      catch { return new Response('', { status: 503 }); }
    }));
    return;
  }
  // data: network first (verse plattegronden), anders cache
  if (url.pathname.endsWith('venues.json') || url.pathname.endsWith('agenda.json')) {
    e.respondWith(fetch(e.request).then(r => { caches.open(VERSION).then(c => c.put(e.request, r.clone())); return r; }).catch(() => caches.match(e.request)));
    return;
  }
  // schil: cache first, anders netwerk (en bewaren)
  e.respondWith(caches.match(e.request).then(hit => hit || fetch(e.request).then(r => {
    if (r.ok && (url.origin === location.origin || url.hostname === 'unpkg.com')) caches.open(VERSION).then(c => c.put(e.request, r.clone()));
    return r;
  }).catch(() => caches.match('index.html'))));
});
