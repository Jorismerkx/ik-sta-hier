/* demo.js — demostand zonder server: dezelfde API als server/server.js, maar alles in de browser (localStorage).
 * Bedoeld om de app op één telefoon door te klikken zolang de server nog niet online staat. Er zitten nepvrienden
 * in (Jonas, Sanne, Mo) die op "Waar zijn jullie?" antwoorden met een puntje. Niets gaat naar andere toestellen.
 */
(function () {
  const KEY = 'demo-db';
  const NEP = [{ id: 'demo-jonas', name: 'Jonas' }, { id: 'demo-sanne', name: 'Sanne' }, { id: 'demo-mo', name: 'Mo' }];
  const rid = () => Math.random().toString(36).slice(2, 11);
  const load = () => { try { return JSON.parse(localStorage.getItem(KEY)) || null; } catch { return null; } };
  let db = load() || { users: {}, sessions: {}, events: {}, feed: [], ratings: {}, seq: 0 };
  const save = () => { try { localStorage.setItem(KEY, JSON.stringify(db)); } catch {} };
  const fout = (status, msg) => Object.assign(new Error(msg), { status });
  const vandaag = () => new Date().toLocaleDateString('sv-SE');
  let listener = null;

  const userView = u => u && { id: u.id, username: u.username, name: u.name, code: u.code };
  function feedAdd(event, user, kind, extra = {}) {
    const u = db.users[user] || NEP.find(n => n.id === user);
    const item = { id: ++db.seq, event, user: { id: user, name: u ? u.name : '?' }, kind, room: null, x: null, y: null, label: null, at: Date.now(), ...extra };
    db.feed.push(item); save();
    return item;
  }
  function eventView(id, me) {
    const e = db.events[id]; if (!e) return null;
    const v = App.venue(e.venue);
    const members = e.members.map(uid => { const u = db.users[uid] || NEP.find(n => n.id === uid); return { id: uid, name: u ? u.name : '?' }; });
    const r = Object.entries(db.ratings[id] || {});
    const last = db.feed.filter(f => f.event === id).slice(-1)[0] || null;
    return { ...e, venueName: v ? v.name : e.venue, members, last,
      rating: { avg: r.length ? Math.round(r.reduce((a, [, s]) => a + s, 0) / r.length * 10) / 10 : null, n: r.length, mine: (db.ratings[id] || {})[me] || null } };
  }
  // nepvriend antwoordt na een paar seconden met een puntje ergens in de zaal
  function antwoord(e) {
    const v = App.venue(e.venue); if (!v) return;
    const rooms = e.rooms.length ? e.rooms : v.rooms.map((_, i) => i);
    const wie = NEP.filter(n => e.members.includes(n.id));
    wie.slice(0, 2).forEach((n, k) => setTimeout(() => {
      const room = rooms[Math.floor(Math.random() * rooms.length)], x = 250 + Math.random() * 400, y = 520 + Math.random() * 600;
      const item = feedAdd(e.id, n.id, 'pin', { room, x: Math.round(x), y: Math.round(y), label: Plan.where(v.rooms[room], x, y) });
      if (listener) listener({ event: e.id, item });
    }, 2500 + k * 2000));
  }

  const routes = [
    ['POST', /^\/register$/, false, ({ body }) => {
      const username = String(body.username || '').trim();
      if (!/^[A-Za-z0-9._-]{3,20}$/.test(username)) throw fout(400, 'Gebruikersnaam: 3 tot 20 letters of cijfers');
      if (String(body.password || '').length < 4) throw fout(400, 'Wachtwoord: minstens 4 tekens');
      if (Object.values(db.users).some(u => u.username.toLowerCase() === username.toLowerCase())) throw fout(409, 'Die gebruikersnaam is al bezet');
      const u = { id: rid(), username, name: username, code: rid().slice(0, 6).toUpperCase(), pass: body.password, friends: NEP.map(n => n.id) };
      db.users[u.id] = u; const token = rid() + rid(); db.sessions[token] = u.id; save();
      return { ...userView(u), token };
    }],
    ['POST', /^\/login$/, false, ({ body }) => {
      const u = Object.values(db.users).find(x => x.username.toLowerCase() === String(body.username || '').toLowerCase() && x.pass === body.password);
      if (!u) throw fout(401, 'Gebruikersnaam of wachtwoord klopt niet');
      const token = rid() + rid(); db.sessions[token] = u.id; save();
      return { ...userView(u), token };
    }],
    ['POST', /^\/logout$/, true, ({ token }) => { delete db.sessions[token]; save(); return { ok: true }; }],
    ['GET', /^\/me$/, true, ({ me }) => userView(me)],
    ['PATCH', /^\/me$/, true, ({ me, body }) => { me.name = String(body.name || me.name).slice(0, 30); save(); return userView(me); }],
    ['GET', /^\/friend\/(\w+)$/, false, () => { throw fout(404, 'In de demo werken vriendlinks niet'); }],
    ['GET', /^\/friends$/, true, ({ me }) => me.friends.map(id => { const u = db.users[id] || NEP.find(n => n.id === id); return u && { id, name: u.name }; }).filter(Boolean)],
    ['POST', /^\/friends$/, true, () => { throw fout(400, 'In de demo kun je geen echte vrienden toevoegen'); }],
    ['DELETE', /^\/friends\/([\w-]+)$/, true, ({ me, m }) => { me.friends = me.friends.filter(f => f !== m[1]); save(); return { ok: true }; }],
    ['GET', /^\/events$/, true, ({ me }) => Object.values(db.events).filter(e => e.members.includes(me.id))
      .sort((a, b) => (b.date + (b.time || '')).localeCompare(a.date + (a.time || ''))).map(e => eventView(e.id, me.id))],
    ['POST', /^\/events$/, true, ({ me, body }) => {
      const v = App.venue(body.venue); if (!v) throw fout(400, 'onbekende club');
      const e = { id: rid(), owner: me.id, title: String(body.title || '').trim() || `Avond in ${v.name}`, venue: body.venue, rooms: body.rooms || [],
        date: body.date, time: body.time || null, link: body.link || null, invite: rid(), members: [me.id, ...(body.friends || []).filter(f => me.friends.includes(f))] };
      db.events[e.id] = e; feedAdd(e.id, me.id, 'create');
      e.members.slice(1).forEach(f => feedAdd(e.id, f, 'join'));
      return eventView(e.id, me.id);
    }],
    ['GET', /^\/events\/([\w-]+)$/, true, ({ me, m }) => {
      const e = db.events[m[1]]; if (!e || !e.members.includes(me.id)) throw fout(404, 'event niet gevonden');
      return { ...eventView(e.id, me.id), feed: db.feed.filter(f => f.event === e.id) };
    }],
    ['DELETE', /^\/events\/([\w-]+)$/, true, ({ m }) => { delete db.events[m[1]]; db.feed = db.feed.filter(f => f.event !== m[1]); save(); return { deleted: true }; }],
    ['POST', /^\/events\/([\w-]+)\/members$/, true, ({ me, m, body }) => {
      const e = db.events[m[1]];
      (body.friends || []).filter(f => !e.members.includes(f)).forEach(f => { e.members.push(f); feedAdd(e.id, f, 'join'); });
      return eventView(e.id, me.id);
    }],
    ['POST', /^\/events\/([\w-]+)\/ping$/, true, ({ me, m }) => { const e = db.events[m[1]]; const item = feedAdd(e.id, me.id, 'ping'); antwoord(e); return item; }],
    ['POST', /^\/events\/([\w-]+)\/pin$/, true, ({ me, m, body }) => feedAdd(m[1], me.id, 'pin', { room: body.room, x: body.x, y: body.y, label: body.label || null })],
    ['POST', /^\/events\/([\w-]+)\/rating$/, true, ({ me, m, body }) => {
      const e = db.events[m[1]];
      if (e.date > vandaag()) throw fout(400, 'Beoordelen kan vanaf de avond zelf');
      const eerste = !(db.ratings[e.id] || {})[me.id];
      db.ratings[e.id] = { ...(db.ratings[e.id] || {}), [me.id]: Number(body.score) };
      if (eerste) feedAdd(e.id, me.id, 'rate', { label: String(body.score) });
      save(); return eventView(e.id, me.id);
    }],
    ['GET', /^\/invite\/([\w-]+)$/, false, () => { throw fout(404, 'In de demo werken uitnodigingslinks niet'); }],
    ['GET', /^\/push$/, false, () => { throw fout(400, 'Geen meldingen in de demo'); }],
  ];

  window.DemoApi = {
    async request(method, path, body, token) {
      await new Promise(r => setTimeout(r, 120)); // voelt als een echte server
      const me = token ? db.users[db.sessions[token]] : null;
      for (const [mt, re, needAuth, fn] of routes) {
        const m = path.match(re);
        if (!m || mt !== method) continue;
        if (needAuth && !me) throw fout(401, 'niet ingelogd');
        return JSON.parse(JSON.stringify(fn({ me, m, body: body || {}, token })));
      }
      throw fout(404, 'onbekend pad');
    },
    listen(fn) { listener = fn; },
  };
})();
