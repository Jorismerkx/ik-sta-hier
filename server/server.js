/* server.js — Ik sta hier: API voor vrienden, events en de feed, live updates (SSE), web-push, en de webapp zelf.

Start:  cd server && npm install && node server.js
Env:    PORT (8787), DATA_DIR (server/data), PUBLIC_URL (https-adres van de app, voor links en VAPID),
        VAPID_PUBLIC / VAPID_PRIVATE (anders gegenereerd en bewaard in DATA_DIR/vapid.json)
*/
'use strict';
const http = require('node:http');
const fs = require('node:fs');
const path = require('node:path');
const store = require('./db');
const push = require('./push');

const ROOT = path.resolve(__dirname, '..');
const PORT = +process.env.PORT || 8787;
const DATA = process.env.DATA_DIR || path.join(__dirname, 'data');
const PUBLIC_URL = process.env.PUBLIC_URL || 'https://jorismerkx.github.io/ik-sta-hier/';
fs.mkdirSync(DATA, { recursive: true });
const db = store.open(DATA);
const VAPID_PUBLIC = push.init(DATA, PUBLIC_URL.startsWith('https:') ? PUBLIC_URL : 'https://jorismerkx.github.io/ik-sta-hier/');

// venues: alleen naam en zalen, voor controle en voor de tekst van meldingen
const VENUES = new Map(JSON.parse(fs.readFileSync(path.join(ROOT, 'data', 'venues.json'), 'utf8'))
  .map(v => [v.id, { name: v.name, rooms: (v.rooms || []).map(r => r.name) }]));

// ---------- hulpjes ----------
class Fout extends Error { constructor(status, msg) { super(msg); this.status = status; } }
const tekst = (v, max) => String(v ?? '').replace(/\s+/g, ' ').trim().slice(0, max);
const DATUM = /^\d{4}-\d{2}-\d{2}$/, TIJD = /^\d{2}:\d{2}$/;
const datumNL = d => new Date(d + 'T12:00:00').toLocaleDateString('nl-NL', { weekday: 'short', day: 'numeric', month: 'short' });

function send(res, status, body, headers = {}) {
  res.writeHead(status, { 'content-type': 'application/json; charset=utf-8', 'cache-control': 'no-store', ...headers });
  res.end(JSON.stringify(body));
}
function readBody(req) {
  return new Promise((resolve, reject) => {
    let n = 0; const chunks = [];
    req.on('data', c => { n += c.length; if (n > 64 * 1024) { reject(new Fout(413, 'te groot')); req.destroy(); } else chunks.push(c); });
    req.on('end', () => { try { resolve(chunks.length ? JSON.parse(Buffer.concat(chunks)) : {}); } catch { reject(new Fout(400, 'geen geldige JSON')); } });
    req.on('error', reject);
  });
}
function auth(req, url) {
  const h = req.headers.authorization || '';
  const token = h.startsWith('Bearer ') ? h.slice(7) : url.searchParams.get('t');
  return token ? db.userByToken(token) : null;
}

// ---------- weergave ----------
const feedView = f => f && ({ id: f.id, event: f.event, user: { id: f.user, name: f.name }, kind: f.kind,
  room: f.room, x: f.x, y: f.y, label: f.label, at: f.created });
function eventView(id) {
  const e = db.event(id); if (!e) return null;
  const v = VENUES.get(e.venue);
  return { id: e.id, title: e.title, venue: e.venue, venueName: v ? v.name : e.venue, rooms: e.rooms, date: e.date, time: e.time,
    owner: e.owner, invite: e.invite, members: db.members(id), last: feedView(db.lastFeed(id)) };
}
const plek = (e, f) => { const v = VENUES.get(e.venue); return [v && v.rooms[f.room], f.label].filter(Boolean).join(' · '); };

// ---------- live: per gebruiker open SSE-verbindingen ----------
const streams = new Map();
function emit(userIds, type, data) {
  const msg = `event: ${type}\ndata: ${JSON.stringify(data)}\n\n`;
  for (const id of userIds) for (const res of streams.get(id) || []) res.write(msg);
}
setInterval(() => { for (const set of streams.values()) for (const res of set) res.write(': hou vast\n\n'); }, 25000).unref();

function feedNaarGroep(e, item, pushMsg) {
  const ids = db.members(e.id).map(m => m.id);
  emit(ids, 'feed', { event: e.id, item });
  if (pushMsg) push.send(db, ids.filter(id => id !== item.user.id), pushMsg).catch(err => console.warn('push', err.message));
}

// ---------- API ----------
const pingRust = new Map(); // niet vaker dan eens per 8 s "waar zijn jullie" per persoon per event

const routes = [
  ['GET', /^\/api\/health$/, false, () => ({ ok: true })],
  ['GET', /^\/api\/push$/, false, () => ({ key: VAPID_PUBLIC })],

  // account op dit toestel: alleen een naam, geen wachtwoord
  ['POST', /^\/api\/me$/, false, async ({ body }) => {
    const name = tekst(body.name, 30);
    if (name.length < 1) throw new Fout(400, 'naam ontbreekt');
    return db.createUser(name);
  }],
  ['GET', /^\/api\/me$/, true, ({ me }) => me],
  ['PATCH', /^\/api\/me$/, true, ({ me, body }) => {
    const name = tekst(body.name, 30); if (!name) throw new Fout(400, 'naam ontbreekt');
    db.rename(me.id, name); return { ...me, name };
  }],

  // vrienden
  ['GET', /^\/api\/friend\/(\w+)$/, false, ({ m }) => {
    const u = db.userByCode(m[1]); if (!u) throw new Fout(404, 'code onbekend'); return { name: u.name, code: u.code };
  }],
  ['GET', /^\/api\/friends$/, true, ({ me }) => db.friends(me.id)],
  ['POST', /^\/api\/friends$/, true, ({ me, body }) => {
    const u = db.userByCode(tekst(body.code, 12)); if (!u) throw new Fout(404, 'code onbekend');
    if (u.id === me.id) throw new Fout(400, 'dat is je eigen code');
    const nieuw = !db.areFriends(me.id, u.id);
    db.befriend(me.id, u.id);
    if (nieuw) {
      emit([u.id], 'friend', { id: me.id, name: me.name });
      push.send(db, [u.id], { title: `${me.name} heeft je toegevoegd`, body: 'Jullie zijn nu vrienden in Ik sta hier', url: '#vrienden', tag: 'vriend' }).catch(() => {});
    }
    return { id: u.id, name: u.name };
  }],
  ['DELETE', /^\/api\/friends\/([\w-]+)$/, true, ({ me, m }) => { db.unfriend(me.id, m[1]); return { ok: true }; }],

  // events
  ['GET', /^\/api\/events$/, true, ({ me }) => db.eventsOf(me.id).map(eventView)],
  ['POST', /^\/api\/events$/, true, ({ me, body }) => {
    const v = VENUES.get(body.venue); if (!v) throw new Fout(400, 'onbekende club');
    const rooms = (Array.isArray(body.rooms) ? body.rooms : []).map(Number).filter(i => Number.isInteger(i) && i >= 0 && i < v.rooms.length);
    if (!DATUM.test(body.date || '')) throw new Fout(400, 'datum ontbreekt');
    const time = TIJD.test(body.time || '') ? body.time : null;
    const id = db.createEvent({ owner: me.id, title: tekst(body.title, 60) || `Avond in ${v.name}`, venue: body.venue,
      rooms: [...new Set(rooms)].sort((a, b) => a - b), date: body.date, time });
    db.addMember(id, me.id);
    db.addFeed({ event: id, user: me.id, kind: 'create' });
    const vrienden = new Set(db.friends(me.id).map(f => f.id));
    for (const uid of (body.friends || []).filter(u => vrienden.has(u))) uitnodigen(id, me, uid);
    return eventView(id);
  }],
  ['GET', /^\/api\/events\/([\w-]+)$/, true, ({ me, m }) => {
    if (!db.isMember(m[1], me.id)) throw new Fout(404, 'event niet gevonden');
    return { ...eventView(m[1]), feed: db.feed(m[1]).map(feedView) };
  }],
  ['DELETE', /^\/api\/events\/([\w-]+)$/, true, ({ me, m }) => {
    const e = db.event(m[1]); if (!e || !db.isMember(e.id, me.id)) throw new Fout(404, 'event niet gevonden');
    const ids = db.members(e.id).map(x => x.id);
    if (e.owner === me.id) { db.deleteEvent(e.id); emit(ids, 'gone', { event: e.id }); return { deleted: true }; }
    db.removeMember(e.id, me.id);
    emit([me.id], 'gone', { event: e.id });
    feedNaarGroep(e, feedView(db.addFeed({ event: e.id, user: me.id, kind: 'leave' })));
    return { left: true };
  }],
  ['POST', /^\/api\/events\/([\w-]+)\/members$/, true, ({ me, m, body }) => {
    if (!db.isMember(m[1], me.id)) throw new Fout(404, 'event niet gevonden');
    const vrienden = new Set(db.friends(me.id).map(f => f.id));
    for (const uid of (body.friends || []).filter(u => vrienden.has(u))) uitnodigen(m[1], me, uid);
    return eventView(m[1]);
  }],
  ['POST', /^\/api\/events\/([\w-]+)\/ping$/, true, ({ me, m }) => {
    const e = db.event(m[1]); if (!e || !db.isMember(e.id, me.id)) throw new Fout(404, 'event niet gevonden');
    const k = me.id + e.id;
    if (Date.now() - (pingRust.get(k) || 0) < 8000) throw new Fout(429, 'even wachten');
    pingRust.set(k, Date.now());
    const item = feedView(db.addFeed({ event: e.id, user: me.id, kind: 'ping' }));
    feedNaarGroep(e, item, { title: `${me.name} zoekt jullie`, body: 'Waar staan jullie? Tik en zet je puntje.', url: `#event/${e.id}/antwoord`,
      tag: `ping-${e.id}`, urgent: true });
    return item;
  }],
  ['POST', /^\/api\/events\/([\w-]+)\/pin$/, true, ({ me, m, body }) => {
    const e = db.event(m[1]); if (!e || !db.isMember(e.id, me.id)) throw new Fout(404, 'event niet gevonden');
    const v = VENUES.get(e.venue), room = Number(body.room), x = Number(body.x), y = Number(body.y);
    if (!v || !Number.isInteger(room) || room < 0 || room >= v.rooms.length) throw new Fout(400, 'onbekende zaal');
    if (!(x >= 0 && x <= 900 && y >= 0 && y <= 1600)) throw new Fout(400, 'plek buiten de kaart');
    const item = feedView(db.addFeed({ event: e.id, user: me.id, kind: 'pin', room, x, y, label: tekst(body.label, 80) || null }));
    feedNaarGroep(e, item, { title: `${me.name} staat hier`, body: plek(e, item) || v.name, url: `#event/${e.id}/pin/${item.id}`, tag: `pin-${e.id}-${me.id}` });
    return item;
  }],

  // meedoen via een WhatsApp-link
  ['GET', /^\/api\/invite\/([\w-]+)$/, false, ({ m }) => {
    const e = db.eventByInvite(m[1]); if (!e) throw new Fout(404, 'uitnodiging verlopen');
    const v = eventView(e.id); const host = db.user(e.owner);
    return { title: v.title, venue: v.venue, venueName: v.venueName, date: v.date, time: v.time, host: host && host.name, members: v.members.length };
  }],
  ['POST', /^\/api\/invite\/([\w-]+)$/, true, ({ me, m }) => {
    const e = db.eventByInvite(m[1]); if (!e) throw new Fout(404, 'uitnodiging verlopen');
    if (db.addMember(e.id, me.id)) {
      db.befriend(me.id, e.owner);
      feedNaarGroep(e, feedView(db.addFeed({ event: e.id, user: me.id, kind: 'join' })));
    }
    return eventView(e.id);
  }],

  // meldingen
  ['POST', /^\/api\/push$/, true, ({ me, body }) => {
    const s = body.subscription;
    if (!s || typeof s.endpoint !== 'string' || !/^https:\/\//.test(s.endpoint) || !s.keys) throw new Fout(400, 'ongeldig abonnement');
    db.addSub(me.id, { endpoint: s.endpoint, keys: { p256dh: s.keys.p256dh, auth: s.keys.auth } });
    return { ok: true };
  }],
];

function uitnodigen(eventId, door, uid) {
  if (!db.addMember(eventId, uid)) return;
  const e = db.event(eventId);
  feedNaarGroep(e, feedView(db.addFeed({ event: e.id, user: uid, kind: 'join' })));
  emit([uid], 'event', eventView(eventId));
  push.send(db, [uid], { title: `${door.name} nodigt je uit`, body: `${eventView(eventId).venueName}, ${datumNL(e.date)}${e.time ? ' ' + e.time : ''}`,
    url: `#event/${eventId}`, tag: `uitnodiging-${eventId}` }).catch(() => {});
}

function stream(req, res, me) {
  res.writeHead(200, { 'content-type': 'text/event-stream', 'cache-control': 'no-store', connection: 'keep-alive', 'x-accel-buffering': 'no',
    'access-control-allow-origin': '*' });
  res.write('retry: 3000\n\n');
  if (!streams.has(me.id)) streams.set(me.id, new Set());
  streams.get(me.id).add(res);
  req.on('close', () => { const s = streams.get(me.id); s.delete(res); if (!s.size) streams.delete(me.id); });
}

async function api(req, res, url) {
  const cors = { 'access-control-allow-origin': '*' };
  if (req.method === 'OPTIONS') {
    res.writeHead(204, { ...cors, 'access-control-allow-methods': 'GET,POST,PATCH,DELETE', 'access-control-allow-headers': 'authorization,content-type', 'access-control-max-age': '86400' });
    return res.end();
  }
  try {
    if (url.pathname === '/api/stream') {
      const me = auth(req, url); if (!me) throw new Fout(401, 'niet ingelogd');
      return stream(req, res, me);
    }
    for (const [method, re, needAuth, fn] of routes) {
      const m = url.pathname.match(re);
      if (!m || method !== req.method) continue;
      const me = auth(req, url);
      if (needAuth && !me) throw new Fout(401, 'niet ingelogd');
      const body = ['POST', 'PATCH'].includes(method) ? await readBody(req) : {};
      return send(res, 200, await fn({ me, m, body }), cors);
    }
    throw new Fout(404, 'onbekend pad');
  } catch (e) {
    if (!e.status) console.error(e);
    send(res, e.status || 500, { error: e.status ? e.message : 'serverfout' }, cors);
  }
}

// ---------- de webapp zelf (alleen wat de app nodig heeft) ----------
const TYPES = { '.html': 'text/html; charset=utf-8', '.css': 'text/css; charset=utf-8', '.js': 'text/javascript; charset=utf-8',
  '.json': 'application/json; charset=utf-8', '.webmanifest': 'application/manifest+json', '.png': 'image/png', '.jpg': 'image/jpeg', '.svg': 'image/svg+xml' };
const OPEN = /^\/(index\.html|style\.css|app\.js|plan\.js|social\.js|config\.js|sw\.js|manifest\.webmanifest|data\/venues\.json|img\/[\w\-./]+\.(png|jpg|svg))$/;
function statisch(req, res, url) {
  const p = url.pathname === '/' ? '/index.html' : decodeURIComponent(url.pathname);
  if (!OPEN.test(p) || p.includes('..')) { res.writeHead(404); return res.end('niet gevonden'); }
  const file = path.join(ROOT, p);
  fs.stat(file, (err, st) => {
    if (err || !st.isFile()) { res.writeHead(404); return res.end('niet gevonden'); }
    const vers = /\.(html|css|js|json|webmanifest)$/.test(p); // app-schil altijd verversen; foto's mogen een dag in de cache
    res.writeHead(200, { 'content-type': TYPES[path.extname(p)] || 'application/octet-stream', 'content-length': st.size,
      'cache-control': vers ? 'no-cache' : 'public, max-age=86400' });
    fs.createReadStream(file).pipe(res);
  });
}

const server = http.createServer((req, res) => {
  const url = new URL(req.url, 'http://x');
  if (url.pathname.startsWith('/api/')) return api(req, res, url);
  if (req.method !== 'GET' && req.method !== 'HEAD') { res.writeHead(405); return res.end(); }
  statisch(req, res, url);
});
server.listen(PORT, () => console.log(`Ik sta hier draait op http://localhost:${PORT}  (data: ${DATA})`));
