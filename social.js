/* social.js — vrienden, events en de feed: "Waar zijn jullie?" en "Ik sta hier" naar je groep.
 *
 * Profiel = alleen een naam; de server geeft een token terug dat op dit toestel blijft (localStorage).
 * De feed van een event is geen chat: je kunt alleen pingen ("Waar zijn jullie?") of je puntje sturen.
 * Zonder bereik gaan pings en puntjes in een wachtrij en worden ze verstuurd zodra er weer verbinding is.
 */
(function () {
  const { $, $$, esc, toast, store } = App;
  const CFG = window.ISH_CONFIG || {};
  const API = CFG.api ? CFG.api.replace(/\/$/, '') + '/api' : 'api'; // relatief: werkt ook als de app in een submap staat
  const WEB = (CFG.web || (location.protocol.startsWith('http') ? location.origin + location.pathname : '')).replace(/#.*$/, '');
  const SOS = [90, 60, 90, 60, 90, 180, 260, 80, 260, 80, 260, 180, 90, 60, 90, 60, 90];
  const native = () => !!(window.Capacitor && Capacitor.isNativePlatform && Capacitor.isNativePlatform());

  let me = store.get('me', null);            // { id, name, code, token }
  let friends = store.get('friends', []);
  let events = store.get('events', []);      // samenvattingen, nieuwste eerst
  let outbox = store.get('outbox', []);      // pings en puntjes die nog moeten
  let open = null;                           // het event dat nu open staat, met feed
  let reachable = true;
  let es = null;

  // ---------- server ----------
  async function api(method, path, body) {
    let r;
    try {
      r = await fetch(API + path, {
        method, headers: { 'content-type': 'application/json', ...(me ? { authorization: 'Bearer ' + me.token } : {}) },
        body: body ? JSON.stringify(body) : undefined,
      });
    } catch (e) { reachable = false; throw Object.assign(new Error('Geen verbinding'), { offline: true }); }
    if (!(r.headers.get('content-type') || '').includes('json')) { // geen server achter dit adres (bv. alleen GitHub Pages)
      reachable = false; throw Object.assign(new Error('Server niet bereikbaar'), { offline: true });
    }
    reachable = true;
    const data = await r.json().catch(() => ({}));
    if (r.status === 401 && me && path !== '/me') { forget(); }
    if (!r.ok) throw Object.assign(new Error(data.error || 'Er ging iets mis'), { status: r.status });
    return data;
  }
  function forget() { me = null; friends = []; events = []; store.set('me', null); save(); if (es) { es.close(); es = null; } renderAll(); }
  function save() { store.set('friends', friends); store.set('events', events); }

  // ---------- kleine helpers ----------
  const initials = name => App.initials(name || '?');
  const AV = ['#2e5bff', '#00a651', '#ff6a00', '#7b2cff', '#ff2f8e', '#00a3a3', '#c99a00', '#d6006e', '#0a8cff', '#8a5cff', '#00b36b', '#e0442a'];
  const avColor = key => {
    const i = open && open.members ? open.members.findIndex(m => m.id === key) : -1; // binnen een event: iedereen een eigen kleur
    if (i >= 0) return AV[i % AV.length];
    let h = 7; for (const c of String(key)) h = (h * 33 + c.charCodeAt(0)) >>> 0; return AV[h % AV.length];
  };
  const avatar = (u, cls = 'av') => `<span class="${cls}" style="background:${avColor(u.id || u.name)}">${esc(initials(u.name))}</span>`;
  const pad = n => String(n).padStart(2, '0');
  const today = (d = new Date()) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
  const clock = ts => { const d = new Date(ts); return `${pad(d.getHours())}:${pad(d.getMinutes())}`; };
  function isActive(ev, now = Date.now()) {
    const start = new Date(ev.date + 'T12:00:00').getTime();
    return now >= start && now < start + 20 * 3600e3; // van 12:00 tot 08:00 de ochtend erna
  }
  function dayLabel(ev) {
    if (isActive(ev)) return 'Vanavond';
    const d = new Date(ev.date + 'T12:00:00'), t = new Date(today() + 'T12:00:00');
    const diff = Math.round((d - t) / 864e5);
    if (diff === 1) return 'Morgen';
    return d.toLocaleDateString('nl-NL', { weekday: 'short', day: 'numeric', month: 'short' });
  }
  const whenLabel = ev => dayLabel(ev) + (ev.time ? ' ' + ev.time : '');
  function buzz(pattern) { try { if (navigator.vibrate) navigator.vibrate(pattern); } catch {} }
  function beep() { // korte, herkenbare ping (twee tonen omhoog)
    try {
      const ac = beep.ac || (beep.ac = new (window.AudioContext || window.webkitAudioContext)());
      [[880, 0], [1320, 0.13]].forEach(([f, t]) => {
        const o = ac.createOscillator(), g = ac.createGain();
        o.frequency.value = f; o.type = 'sine';
        g.gain.setValueAtTime(0.0001, ac.currentTime + t); g.gain.exponentialRampToValueAtTime(0.35, ac.currentTime + t + 0.02);
        g.gain.exponentialRampToValueAtTime(0.0001, ac.currentTime + t + 0.22);
        o.connect(g).connect(ac.destination); o.start(ac.currentTime + t); o.stop(ac.currentTime + t + 0.25);
      });
    } catch {}
  }
  const venueOf = ev => App.venue(ev.venue);
  const roomsOf = ev => { const v = venueOf(ev); return v ? (ev.rooms.length ? ev.rooms : v.rooms.map((_, i) => i)) : []; };
  function upsert(ev) {
    const i = events.findIndex(x => x.id === ev.id);
    if (i >= 0) events[i] = { ...events[i], ...ev }; else events.unshift(ev);
    events.sort((a, b) => (b.date + (b.time || '')).localeCompare(a.date + (a.time || '')));
    save();
  }
  const activeEvents = () => events.filter(e => isActive(e)).sort((a, b) => (b.id === store.get('lastEvent') ? 1 : 0) - (a.id === store.get('lastEvent') ? 1 : 0));

  // ---------- onderblad (sheet) ----------
  function sheet(html, mount) {
    $('#sheet-body').innerHTML = html;
    $('#sheet').classList.remove('hidden');
    requestAnimationFrame(() => $('#sheet').classList.add('open'));
    if (mount) mount($('#sheet-body'));
  }
  function closeSheet() { $('#sheet').classList.remove('open'); setTimeout(() => $('#sheet').classList.add('hidden'), 200); }
  $('#sheet .sheet-bg').addEventListener('click', closeSheet);

  // ---------- profiel ----------
  function ensureMe(reason) {
    if (me) return Promise.resolve(me);
    return new Promise(resolve => {
      sheet(`<h3>Hoe heet je?</h3><p class="sheet-sub">${esc(reason || 'Zo zien je vrienden wie er zoekt of waar je staat. Alleen een naam, geen wachtwoord.')}</p>
        <form class="name-form"><input id="me-name" maxlength="30" placeholder="Je naam" autocomplete="nickname" required><button class="cta">Verder</button></form>`, el => {
        const f = el.querySelector('form'), inp = el.querySelector('input');
        setTimeout(() => inp.focus(), 250);
        f.addEventListener('submit', async e => {
          e.preventDefault();
          try {
            me = await api('POST', '/me', { name: inp.value });
            store.set('me', me); closeSheet(); connect(); loadAll(); renderAll(); resolve(me);
          } catch (err) { toast(err.offline ? 'Geen verbinding met de server' : err.message); }
        });
      });
    });
  }

  // ---------- laden + live ----------
  let lastLoad = 0;
  async function loadAll(force) {
    if (!me || (!force && Date.now() - lastLoad < 4000)) return;
    lastLoad = Date.now();
    try {
      const [u, fr, evs] = await Promise.all([api('GET', '/me'), api('GET', '/friends'), api('GET', '/events')]);
      me = { ...me, ...u }; store.set('me', me);
      friends = fr; events = evs; save();
    } catch (e) { /* offline: we houden wat we hadden */ }
    renderAll();
  }
  async function loadFriends() { try { friends = await api('GET', '/friends'); save(); renderFriends(); } catch {} }

  function connect() {
    if (!me || es || typeof EventSource === 'undefined') return;
    es = new EventSource(`${API}/stream?t=${encodeURIComponent(me.token)}`);
    es.addEventListener('feed', e => onFeed(JSON.parse(e.data)));
    es.addEventListener('event', e => {
      const ev = JSON.parse(e.data); upsert(ev); renderEvents(); buzz([120, 60, 120]);
      const host = ev.members.find(m => m.id === ev.owner);
      toast(`${host ? host.name : 'Iemand'} nodigt je uit: ${ev.venueName}`);
    });
    es.addEventListener('gone', e => {
      const { event } = JSON.parse(e.data);
      events = events.filter(x => x.id !== event); save();
      if (open && open.id === event) { open = null; App.show('home'); App.selectTab('events'); }
      renderEvents();
    });
    es.addEventListener('friend', e => { const f = JSON.parse(e.data); toast(`${f.name} heeft je toegevoegd`); loadFriends(); });
    es.onopen = () => { reachable = true; flush(); };
  }

  function onFeed({ event, item }) {
    const ev = events.find(x => x.id === event);
    if (ev) { ev.last = item; if (item.kind === 'join' || item.kind === 'leave') refreshEvent(event); save(); }
    if (open && open.id === event) addItem(item);
    const mine = me && item.user.id === me.id;
    if (!mine && item.kind === 'ping') alarm(ev || open, item);
    if (!mine && item.kind === 'pin' && !(open && open.id === event && $('#view-event').classList.contains('active'))) {
      toast(`${item.user.name} staat hier`); buzz([60]);
    }
    renderEvents();
  }
  async function refreshEvent(id) { try { const ev = await api('GET', `/events/${id}`); delete ev.feed; upsert(ev); renderEvents(); if (open && open.id === id) { open = { ...open, ...ev }; renderEvent(); } } catch {} }

  // "Jonas zoekt jullie": opvallend, met één tik naar de plattegrond
  function alarm(ev, item) {
    if (!ev) return;
    buzz(SOS); beep();
    const el = $('#alert');
    el.innerHTML = `${avatar(item.user)}<div class="al-text"><strong>${esc(item.user.name)} zoekt jullie</strong><span>${esc(ev.venueName || '')}</span></div>
      <button class="al-go">Stuur mijn plek</button><button class="al-x" aria-label="Sluit">×</button>`;
    el.classList.remove('hidden'); el.classList.add('show');
    el.querySelector('.al-go').onclick = () => { hideAlarm(); openEvent(ev.id, { then: 'antwoord' }); };
    el.querySelector('.al-x').onclick = hideAlarm;
    clearTimeout(alarm.t); alarm.t = setTimeout(hideAlarm, 25000);
  }
  function hideAlarm() { $('#alert').classList.remove('show'); setTimeout(() => $('#alert').classList.add('hidden'), 250); }

  // ---------- wachtrij: versturen ook als het netwerk hapert ----------
  function queue(path, body, meta) {
    outbox.push({ id: 'o' + Date.now().toString(36) + Math.random().toString(36).slice(2, 6), path, body, ...meta, at: Date.now() });
    store.set('outbox', outbox);
    renderEvent();
    return flush();
  }
  async function flush() {
    if (flush.busy || !outbox.length || !me) return;
    flush.busy = true;
    try {
      while (outbox.length) {
        const job = outbox[0];
        try {
          const item = await api('POST', job.path, job.body);
          outbox.shift(); store.set('outbox', outbox);
          if (item && item.id) onFeed({ event: job.event, item });
        } catch (e) {
          if (e.offline) break;
          outbox.shift(); store.set('outbox', outbox);
          toast(e.status === 429 ? 'Je groep heeft het net gehoord, even wachten' : e.message);
        }
      }
    } finally { flush.busy = false; renderEvent(); }
  }
  window.addEventListener('online', flush);
  setInterval(flush, 8000);

  // ---------- acties ----------
  function ping(ev) {
    queue(`/events/${ev.id}/ping`, {}, { event: ev.id, kind: 'ping' });
    buzz(20); toast(navigator.onLine === false ? 'Gaat zodra je bereik hebt' : 'Je groep krijgt een seintje');
  }
  function iAmHere(ev) {
    const v = venueOf(ev); if (!v) { toast('Club niet gevonden'); return; }
    const rooms = roomsOf(ev);
    if (rooms.length === 1) return planFor(ev, rooms[0]);
    sheet(`<h3>In welke zaal sta je?</h3><div class="room-pick">${rooms.map(i => `<button class="room-card" data-i="${i}"><div class="thumb">${Plan.render(v, v.rooms[i], { mini: true })}</div><div class="cap">${esc(v.rooms[i].name)}</div></button>`).join('')}</div>`,
      el => el.querySelectorAll('.room-card').forEach(b => b.addEventListener('click', () => { closeSheet(); planFor(ev, +b.dataset.i); })));
  }
  function planFor(ev, i, focus) {
    const v = venueOf(ev); const r = v && v.rooms[i]; if (!r) return;
    store.set('lastEvent', ev.id);
    // laatste puntje van iedereen (behalve jijzelf) in deze zaal
    const latest = new Map();
    ((open && open.id === ev.id && open.feed) || []).forEach(f => { if (f.kind === 'pin') latest.set(f.user.id, f); });
    if (focus) latest.set(focus.user.id, focus);
    const dots = [...latest.values()].filter(f => f.room === i && (f.user.id !== me.id || (focus && f.id === focus.id)))
      .map(f => ({ x: f.x, y: f.y, initials: initials(f.user.name), name: focus && f.id === focus.id ? `${f.user.name} · ${clock(f.at)}` : f.user.name, focus: !!(focus && f.id === focus.id) }));
    App.openPlan(v, r, 'event', {
      dots, hint: dots.length ? 'Tik waar jij staat, dan Stuur' : 'Tik waar je staat, dan Stuur',
      onSend: p => sendPin(ev, p),
    });
  }
  function sendPin(ev, p) {
    queue(`/events/${ev.id}/pin`, p, { event: ev.id, kind: 'pin' });
    buzz(20);
    openEvent(ev.id, { quiet: true });
    if (navigator.onLine === false) {
      const v = venueOf(ev), r = v.rooms[p.room];
      const text = `Ik sta hier: ${v.name} · ${r.name}, ${p.label}`;
      sheet(`<h3>Geen bereik</h3><p class="sheet-sub">Je puntje wacht en gaat vanzelf zodra je verbinding hebt. Sms komt vaak wel door:</p>
        <a class="cta as-link" href="sms:?&body=${encodeURIComponent(text)}">Stuur als sms</a><p class="sheet-sub center">${esc(text)}</p>`);
    } else toast('Verstuurd naar je groep');
  }

  async function share(text, url) {
    if (native() && Capacitor.Plugins.Share) { try { await Capacitor.Plugins.Share.share({ text: `${text} ${url}`, dialogTitle: 'Uitnodigen' }); } catch {} return; }
    window.open(`https://wa.me/?text=${encodeURIComponent(`${text} ${url}`)}`, '_blank', 'noopener');
  }
  const inviteEvent = ev => share(`Ga je mee? ${ev.title}: ${ev.venueName}, ${whenLabel(ev).toLowerCase()}. Doe mee in Ik sta hier, dan vinden we elkaar binnen:`, `${WEB}#e/${ev.invite}`);
  const inviteFriend = () => share(`Voeg me toe in Ik sta hier, dan vinden we elkaar in de club:`, `${WEB}#vriend/${me.code}`);

  // ---------- meldingen (web-push) ----------
  const isIOS = /iphone|ipad|ipod/i.test(navigator.userAgent);
  const pushable = () => 'serviceWorker' in navigator && 'PushManager' in window && 'Notification' in window && location.protocol !== 'file:';
  const pushOn = () => pushable() && Notification.permission === 'granted' && store.get('push') === (me && me.id);
  function b64u8(s) { const p = '='.repeat((4 - s.length % 4) % 4), b = atob((s + p).replace(/-/g, '+').replace(/_/g, '/')); return Uint8Array.from(b, c => c.charCodeAt(0)); }
  async function enablePush(silent) {
    if (!pushable()) { if (!silent) toast(isIOS ? 'Zet de app eerst op je beginscherm' : 'Meldingen werken niet in deze browser'); return; }
    try {
      if (Notification.permission !== 'granted' && (silent || (await Notification.requestPermission()) !== 'granted')) { if (!silent) toast('Meldingen staan uit'); return; }
      const reg = await navigator.serviceWorker.ready;
      const { key } = await api('GET', '/push');
      const sub = (await reg.pushManager.getSubscription()) || await reg.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: b64u8(key) });
      await api('POST', '/push', { subscription: sub.toJSON() });
      store.set('push', me.id);
      if (!silent) { toast('Meldingen staan aan'); buzz(SOS); }
    } catch (e) { if (!silent) toast('Meldingen aanzetten lukte niet'); }
    renderFriends(); renderEvent();
  }
  function pushBanner() {
    if (pushOn()) return '';
    if (pushable()) return `<div class="notify-in"><span>Krijg een seintje als je groep je zoekt</span><button class="mini-btn" data-act="push">Zet aan</button></div>`;
    if (isIOS && !native()) return `<div class="notify-in"><span>Meldingen op iPhone: zet de app op je beginscherm (deel-knop, "Zet op beginscherm")</span></div>`;
    return '';
  }
  if ('serviceWorker' in navigator) navigator.serviceWorker.addEventListener('message', e => { if (e.data && e.data.open) route(e.data.open.replace(/^#/, '')); });

  // ---------- vrienden ----------
  function intro(title, text) {
    return `<div class="hello"><div class="hello-dot"></div><h3>${title}</h3><p>${text}</p><button class="cta" data-act="profiel">Maak je profiel</button>
      <p class="fine">Alleen een naam. Geen wachtwoord, geen telefoonnummer, geen GPS.</p></div>`;
  }
  function renderFriends() {
    const el = $('#friends'); if (!el) return;
    if (!me) { el.innerHTML = intro('Vind elkaar in de club', 'Voeg je vrienden toe, maak een event voor je avond en zie op de plattegrond waar iedereen staat.'); return bind(el); }
    el.innerHTML = `
      ${reachable ? '' : '<div class="offline-note">Geen verbinding met de server. Je lijst ververst zodra je weer online bent.</div>'}
      <div class="me-card">
        ${avatar(me, 'av big')}
        <div class="me-meta"><button class="me-name" data-act="rename">${esc(me.name)}</button><div class="me-code">Jouw code <strong>${esc(me.code)}</strong></div></div>
      </div>
      <div class="btn-row">
        <button class="pill-btn wa" data-act="invite-friend">${waIcon()}Stuur je link via WhatsApp</button>
      </div>
      <form class="add-friend" data-act="add">
        <input name="code" maxlength="6" placeholder="Code van een vriend" autocapitalize="characters" autocomplete="off">
        <button class="mini-btn">Voeg toe</button>
      </form>
      ${pushBanner() ? `<div class="notify">${pushBanner()}</div>` : ''}
      <div class="letter">Vrienden${friends.length ? ` · ${friends.length}` : ''}</div>
      ${friends.length ? friends.map(f => `<div class="row friend">${avatar(f)}<div class="meta"><div class="name">${esc(f.name)}</div></div><button class="x" data-del="${f.id}" aria-label="Verwijder">×</button></div>`).join('')
        : `<div class="empty small">Nog geen vrienden. Stuur je link via WhatsApp: wie hem opent, staat meteen in je lijst. Of vul hun code hierboven in.</div>`}`;
    bind(el);
  }

  // ---------- events ----------
  function renderEvents() {
    const el = $('#events'); if (!el) return;
    const act = events.filter(e => isActive(e));
    const badge = $('#events-badge'); badge.textContent = act.length || ''; badge.classList.toggle('hidden', !act.length);
    $('#here').classList.toggle('live', !!act.length);
    if (!me) { el.innerHTML = intro('Je avond met je groep', 'Maak een event voor de club waar je heen gaat. Je vrienden krijgen hem meteen, en in de club tik je op <em>Waar sta je?</em>.'); return bind(el); }
    const t = today();
    const komend = events.filter(e => !isActive(e) && e.date >= t).reverse();
    const geweest = events.filter(e => !isActive(e) && e.date < t).slice(0, 6);
    const card = ev => {
      const v = venueOf(ev);
      const last = ev.last ? lastLine(ev.last) : '';
      return `<button class="ev-card ${isActive(ev) ? 'live' : ''}" data-ev="${ev.id}">
        ${v ? App.swatch(v) : '<div class="swatch"></div>'}
        <div class="meta"><div class="name">${esc(ev.title)}</div><div class="info">${esc(whenLabel(ev))} · ${esc(ev.venueName)}</div>
        <div class="faces">${ev.members.slice(0, 6).map(m => avatar(m, 'av tiny')).join('')}${ev.members.length > 6 ? `<span class="more">+${ev.members.length - 6}</span>` : ''}${last ? `<span class="last">${esc(last)}</span>` : ''}</div></div>
        <div class="chev">›</div></button>`;
    };
    el.innerHTML = `
      ${reachable ? '' : '<div class="offline-note">Geen verbinding met de server. Je ziet de laatst bekende stand.</div>'}
      <button class="new-ev" data-act="new"><span>+</span>Nieuw event</button>
      ${act.length ? `<div class="letter">Vanavond</div>${act.map(card).join('')}` : ''}
      ${komend.length ? `<div class="letter">Komend</div>${komend.map(card).join('')}` : ''}
      ${geweest.length ? `<div class="letter">Geweest</div>${geweest.map(card).join('')}` : ''}
      ${!events.length ? '<div class="empty small">Nog geen events. Maak er een voor je volgende avond uit: kies de club, de datum en wie er meegaan.</div>' : ''}`;
    bind(el);
  }
  function lastLine(f) {
    const n = f.user.name;
    return { ping: `${n} zoekt jullie`, pin: `${n} staat hier`, join: `${n} doet mee`, create: `${n} maakte het event`, leave: `${n} is weg` }[f.kind] || '';
  }

  async function openEvent(id, opts = {}) {
    if (!me) { await ensureMe('Maak eerst je profiel, dan zie je je events.'); }
    const cached = events.find(e => e.id === id);
    if (!open || open.id !== id) open = cached ? { ...cached, feed: [] } : null;
    store.set('lastEvent', id);
    history.replaceState(null, '', '#event/' + id);
    if (open && !opts.quiet) { renderEvent(); App.show('event'); }
    try {
      const ev = await api('GET', `/events/${id}`);
      open = ev; const sum = { ...ev }; delete sum.feed; upsert(sum);
    } catch (e) {
      if (!open) { toast(e.offline ? 'Geen verbinding' : 'Event niet gevonden'); App.show('home'); return; }
    }
    renderEvent(); App.show('event');
    if (opts.then === 'antwoord') iAmHere(open);
    if (opts.then && opts.then.pin) { const f = open.feed.find(x => x.id === +opts.then.pin); if (f) planFor(open, f.room, f); }
  }

  function renderEvent() {
    if (!open) return;
    const ev = open, v = venueOf(ev);
    $('#e-title').textContent = ev.title;
    const zalen = ev.rooms.length && v ? ' · ' + ev.rooms.map(i => v.rooms[i] && v.rooms[i].name).filter(Boolean).join(', ') : '';
    $('#e-sub').textContent = `${whenLabel(ev)} · ${ev.venueName}${zalen}`;
    $('#e-members').innerHTML = ev.members.map(m => `<div class="mem">${avatar(m)}<span>${esc(m.id === me.id ? 'Jij' : m.name)}</span></div>`).join('')
      + `<button class="mem add" data-act="invite"><span class="av plus">+</span><span>Uitnodigen</span></button>`;
    const nb = pushBanner(); $('#e-notify').innerHTML = nb; $('#e-notify').classList.toggle('hidden', !nb);
    renderOpenFeed();
    bind($('#view-event'));
  }
  function itemHtml(f, pending) {
    const mine = me && f.user.id === me.id, who = mine ? 'Jij' : f.user.name;
    const time = pending ? 'wacht op bereik…' : clock(f.at);
    if (['create', 'join', 'leave'].includes(f.kind)) {
      const t = { create: `${who} maakte het event`, join: `${who} doet mee`, leave: `${who} is weg` }[f.kind];
      return `<div class="sys">${esc(t)} · ${time}</div>`;
    }
    const head = `<div class="b-head">${mine ? '' : avatar(f.user, 'av tiny')}<span>${esc(who)}</span><time>${time}</time></div>`;
    if (f.kind === 'ping') {
      return `<div class="bubble ping ${mine ? 'mine' : ''} ${pending ? 'pending' : ''}">${head}<div class="b-text">Waar zijn jullie?</div>
        ${mine ? '' : '<button class="b-act" data-act="here">Stuur mijn plek</button>'}</div>`;
    }
    const v = venueOf(open), r = v && v.rooms[f.room];
    if (!r) return '';
    const dot = [{ x: f.x, y: f.y, initials: initials(f.user.name), focus: true }];
    return `<button class="bubble spot ${mine ? 'mine' : ''} ${pending ? 'pending' : ''}" ${pending ? '' : `data-pin="${f.id}"`}>${head}
      <div class="b-pin"><div class="b-map">${Plan.render(v, r, { noFooter: true, dots: dot })}</div>
      <div class="b-where"><strong>${esc(r.name)}</strong><span>${esc(f.label || '')}</span><em>${pending ? '' : 'Tik om te zien'}</em></div></div></button>`;
  }
  function renderOpenFeed() {
    if (!open || !$('#e-feed')) return;
    const pend = outbox.filter(o => o.event === open.id).map(o => ({ id: o.id, user: me, kind: o.kind, room: o.body.room, x: o.body.x, y: o.body.y, label: o.body.label, at: o.at }));
    const items = (open.feed || []).map(f => itemHtml(f, false)).concat(pend.map(f => itemHtml(f, true)));
    const el = $('#e-feed');
    const atEnd = el.scrollHeight - el.scrollTop - el.clientHeight < 80;
    el.innerHTML = items.length ? items.join('') : '<div class="empty small">Nog niets. Tik in de club op <em>Ik sta hier</em> of vraag <em>Waar zijn jullie?</em></div>';
    if (atEnd || renderOpenFeed.first !== open.id) el.scrollTop = el.scrollHeight;
    renderOpenFeed.first = open.id;
    bind(el);
  }
  function addItem(item) {
    if (!open || !open.feed || open.feed.some(f => f.id === item.id)) return;
    open.feed.push(item);
    if (item.kind === 'join' || item.kind === 'leave') refreshEvent(open.id);
    if ($('#view-event').classList.contains('active')) renderOpenFeed();
  }

  function moreSheet() {
    const ev = open, owner = ev.owner === me.id;
    sheet(`<h3>${esc(ev.title)}</h3>
      <button class="sheet-row" data-s="wa">${waIcon()}Uitnodigen via WhatsApp</button>
      ${friends.length ? '<button class="sheet-row" data-s="friends">Vrienden toevoegen</button>' : ''}
      <button class="sheet-row" data-s="club">Plattegronden van ${esc(ev.venueName)}</button>
      <button class="sheet-row danger" data-s="del">${owner ? 'Event verwijderen' : 'Event verlaten'}</button>`, el => {
      el.querySelector('[data-s="wa"]').onclick = () => { closeSheet(); inviteEvent(ev); };
      const fb = el.querySelector('[data-s="friends"]'); if (fb) fb.onclick = () => friendsSheet(ev);
      el.querySelector('[data-s="club"]').onclick = () => { closeSheet(); App.openVenue(ev.venue, { force: true }); };
      el.querySelector('[data-s="del"]').onclick = async () => {
        if (!confirm(owner ? 'Event voor iedereen verwijderen?' : 'Dit event verlaten?')) return;
        try { await api('DELETE', `/events/${ev.id}`); events = events.filter(x => x.id !== ev.id); save(); open = null; closeSheet(); App.show('home'); App.selectTab('events'); }
        catch (e) { toast(e.message); }
      };
    });
  }
  function friendsSheet(ev) {
    const inEv = new Set(ev.members.map(m => m.id));
    const opts = friends.filter(f => !inEv.has(f.id));
    if (!opts.length) { toast('Al je vrienden doen al mee'); return; }
    sheet(`<h3>Wie gaan er mee?</h3><div class="choice">${opts.map(f => `<button class="opt" data-id="${f.id}">${avatar(f, 'av tiny')}${esc(f.name)}</button>`).join('')}</div>
      <button class="cta" data-s="go">Toevoegen</button>`, el => {
      el.querySelectorAll('.opt').forEach(b => b.onclick = () => b.classList.toggle('on'));
      el.querySelector('[data-s="go"]').onclick = async () => {
        const ids = [...el.querySelectorAll('.opt.on')].map(b => b.dataset.id);
        if (!ids.length) return closeSheet();
        try { const upd = await api('POST', `/events/${ev.id}/members`, { friends: ids }); upsert(upd); closeSheet(); openEvent(ev.id); toast('Toegevoegd'); }
        catch (e) { toast(e.message); }
      };
    });
  }

  // ---------- nieuw event ----------
  const form = { venue: null, rooms: [], friends: new Set() };
  async function openNew(venueId) {
    await ensureMe('Maak eerst je profiel, dan kun je je vrienden uitnodigen.');
    form.venue = venueId || null; form.rooms = []; form.friends = new Set();
    $('#ne-date').value = today(); $('#ne-date').min = today();
    $('#ne-time').value = '23:00'; $('#ne-title').value = '';
    renderNew(); App.show('event-new');
  }
  function renderNew() {
    const v = form.venue && App.venue(form.venue);
    $('#ne-venue').innerHTML = v ? `${App.swatch(v)}<span>${esc(v.name)}</span>` : '<span class="ph">Kies een club</span>';
    $('#ne-venue').classList.toggle('chosen', !!v);
    $('#ne-title').placeholder = v ? `Avond in ${v.name}` : 'Avond in …';
    const multi = v && v.rooms.length > 1;
    $('#ne-rooms-wrap').classList.toggle('hidden', !multi);
    if (multi) {
      $('#ne-rooms').innerHTML = `<button type="button" class="opt ${form.rooms.length ? '' : 'on'}" data-r="all">Alle zalen</button>`
        + v.rooms.map((r, i) => `<button type="button" class="opt ${form.rooms.includes(i) ? 'on' : ''}" data-r="${i}">${esc(r.name)}</button>`).join('');
      $$('#ne-rooms .opt').forEach(b => b.onclick = () => {
        if (b.dataset.r === 'all') form.rooms = [];
        else { const i = +b.dataset.r; form.rooms = form.rooms.includes(i) ? form.rooms.filter(x => x !== i) : [...form.rooms, i]; if (form.rooms.length === v.rooms.length) form.rooms = []; }
        renderNew();
      });
    }
    $('#ne-friends').innerHTML = friends.length
      ? friends.map(f => `<button type="button" class="opt ${form.friends.has(f.id) ? 'on' : ''}" data-id="${f.id}">${avatar(f, 'av tiny')}${esc(f.name)}</button>`).join('')
      : '<p class="fine">Nog geen vrienden in de app. Na het aanmaken stuur je de uitnodiging via WhatsApp.</p>';
    $$('#ne-friends .opt').forEach(b => b.onclick = () => { const id = b.dataset.id; form.friends.has(id) ? form.friends.delete(id) : form.friends.add(id); b.classList.toggle('on'); });
  }
  function venueSheet() {
    const all = App.venues();
    const list = s => {
      const n = x => (x || '').toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '');
      const hits = all.filter(v => !s || n(v.name).includes(n(s)) || n(v.aka).includes(n(s))).slice(0, 60);
      return hits.map(v => `<button class="row" data-id="${v.id}">${App.swatch(v)}<div class="meta"><div class="name">${esc(v.name)}</div><div class="info">${esc(v.area || '')}</div></div></button>`).join('');
    };
    sheet(`<h3>Welke club?</h3><div class="search sheet-search"><input id="vs-q" type="search" placeholder="Zoek een club" autocomplete="off"></div><div class="vs-list">${list('')}</div>`, el => {
      const q = el.querySelector('#vs-q'), box = el.querySelector('.vs-list');
      const wire = () => box.querySelectorAll('.row').forEach(r => r.onclick = () => { form.venue = r.dataset.id; form.rooms = []; closeSheet(); renderNew(); });
      q.addEventListener('input', () => { box.innerHTML = list(q.value); wire(); });
      wire();
    });
  }
  $('#ne-venue').addEventListener('click', venueSheet);
  $('#ne-form').addEventListener('submit', async e => {
    e.preventDefault();
    if (!form.venue) { toast('Kies eerst een club'); venueSheet(); return; }
    if (!$('#ne-date').value) { toast('Kies een datum'); return; }
    $('#ne-save').disabled = true;
    try {
      const ev = await api('POST', '/events', { venue: form.venue, rooms: form.rooms, date: $('#ne-date').value, time: $('#ne-time').value,
        title: $('#ne-title').value, friends: [...form.friends] });
      upsert(ev); renderEvents();
      await openEvent(ev.id);
      sheet(`<h3>Event staat klaar</h3><p class="sheet-sub">${form.friends.size ? 'Je vrienden zien hem al in hun Events. ' : ''}Stuur de uitnodiging naar de rest van je groep: wie de link opent, doet meteen mee.</p>
        <button class="cta wa-cta" data-s="wa">${waIcon()}Uitnodigen via WhatsApp</button><button class="sheet-row center" data-s="later">Later</button>`, el => {
        el.querySelector('[data-s="wa"]').onclick = () => { closeSheet(); inviteEvent(ev); };
        el.querySelector('[data-s="later"]').onclick = closeSheet;
      });
    } catch (err) { toast(err.offline ? 'Geen verbinding met de server' : err.message); }
    finally { $('#ne-save').disabled = false; }
  });

  // ---------- de grote knop: Waar sta je? ----------
  async function here() {
    await ensureMe();
    const act = activeEvents();
    if (!act.length) {
      const t = today(), komend = events.filter(e => e.date >= t && !isActive(e)).reverse().slice(0, 3);
      sheet(`<h3>Geen event vanavond</h3><p class="sheet-sub">Maak een event voor je avond, dan kan je groep elkaar vinden.</p>
        <button class="cta" data-s="new">Maak een event</button>
        ${komend.map(e => `<button class="sheet-row" data-ev="${e.id}">${esc(e.title)} <span class="dim">· ${esc(whenLabel(e))}</span></button>`).join('')}
        <button class="sheet-row center" data-s="solo">Alleen mijn plek delen als plaatje</button>`, el => {
        el.querySelector('[data-s="new"]').onclick = () => { closeSheet(); openNew(); };
        el.querySelector('[data-s="solo"]').onclick = () => { closeSheet(); App.selectTab('list'); toast('Kies je club en zaal'); };
        el.querySelectorAll('[data-ev]').forEach(b => b.onclick = () => { closeSheet(); openEvent(b.dataset.ev); });
      });
      return;
    }
    const ev = act[0];
    sheet(`<div class="here-sheet">
        <p class="eyebrow">Vanavond · ${esc(ev.venueName)}</p><h3>${esc(ev.title)}</h3>
        <button class="big-act hot" data-s="pin"><svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="4" fill="currentColor"/><circle cx="12" cy="12" r="8.5" fill="none" stroke="currentColor" stroke-width="2.2"/></svg><span><strong>Ik sta hier</strong><em>Zet je puntje, je groep ziet het</em></span></button>
        <button class="big-act" data-s="ping"><svg viewBox="0 0 24 24"><path d="M12 3a6 6 0 0 0-6 6v3.5L4 16h16l-2-3.5V9a6 6 0 0 0-6-6zM9.5 19a2.5 2.5 0 0 0 5 0" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/></svg><span><strong>Waar zijn jullie?</strong><em>Iedereen krijgt een seintje</em></span></button>
        <button class="sheet-row center" data-s="open">Open het event${act.length > 1 ? ` <span class="dim">(${act.length} vanavond)</span>` : ''}</button></div>`, async el => {
      el.querySelector('[data-s="pin"]').onclick = async () => { closeSheet(); await openEvent(ev.id, { quiet: true }); iAmHere(open); };
      el.querySelector('[data-s="ping"]').onclick = async () => { closeSheet(); ping(ev); openEvent(ev.id); };
      el.querySelector('[data-s="open"]').onclick = () => { closeSheet(); if (act.length > 1) { App.selectTab('events'); App.show('home'); } else openEvent(ev.id); };
    });
  }
  $('#here').addEventListener('click', () => { buzz(10); here(); });
  $('#e-ping').addEventListener('click', () => open && ping(open));
  $('#e-pin').addEventListener('click', () => open && iAmHere(open));
  $('#e-more').addEventListener('click', () => open && moreSheet());

  // ---------- klikken in de lijsten ----------
  function bind(root) {
    root.querySelectorAll('[data-act]').forEach(b => {
      if (b._bound) return; b._bound = true;
      const act = b.dataset.act;
      if (act === 'add') return b.addEventListener('submit', addFriend);
      b.addEventListener('click', () => ({
        profiel: () => ensureMe(), new: () => openNew(), push: () => enablePush(), 'invite-friend': inviteFriend,
        invite: () => open && (friends.some(f => !open.members.find(m => m.id === f.id)) ? inviteChoice() : inviteEvent(open)),
        here: () => open && iAmHere(open), rename,
      }[act] || (() => {}))());
    });
    root.querySelectorAll('[data-del]').forEach(b => b.onclick = async () => {
      const f = friends.find(x => x.id === b.dataset.del);
      if (!f || !confirm(`${f.name} verwijderen uit je vrienden?`)) return;
      try { await api('DELETE', `/friends/${f.id}`); friends = friends.filter(x => x.id !== f.id); save(); renderFriends(); } catch (e) { toast(e.message); }
    });
    root.querySelectorAll('[data-ev]').forEach(b => { if (!b._bound) { b._bound = true; b.addEventListener('click', () => openEvent(b.dataset.ev)); } });
    root.querySelectorAll('[data-pin]').forEach(b => b.onclick = () => { const f = open.feed.find(x => x.id === +b.dataset.pin); if (f) planFor(open, f.room, f); });
  }
  function inviteChoice() {
    sheet(`<h3>Uitnodigen</h3><button class="sheet-row" data-s="friends">Vrienden uit de app</button><button class="sheet-row" data-s="wa">${waIcon()}Via WhatsApp</button>`, el => {
      el.querySelector('[data-s="friends"]').onclick = () => friendsSheet(open);
      el.querySelector('[data-s="wa"]').onclick = () => { closeSheet(); inviteEvent(open); };
    });
  }
  async function addFriend(e) {
    e.preventDefault();
    const code = e.target.code.value.trim().toUpperCase();
    if (code.length < 6) { toast('Een code heeft 6 tekens'); return; }
    try { const f = await api('POST', '/friends', { code }); toast(`${f.name} staat in je vrienden`); e.target.reset(); loadFriends(); }
    catch (err) { toast(err.status === 404 ? 'Die code kennen we niet' : err.message); }
  }
  function rename() {
    sheet(`<h3>Je naam</h3><form class="name-form"><input maxlength="30" value="${esc(me.name)}" required><button class="cta">Bewaar</button></form>`, el => {
      el.querySelector('form').onsubmit = async e => {
        e.preventDefault();
        try { const u = await api('PATCH', '/me', { name: el.querySelector('input').value }); me = { ...me, ...u }; store.set('me', me); closeSheet(); renderFriends(); }
        catch (err) { toast(err.message); }
      };
    });
  }
  function waIcon() { return '<svg class="wa-ic" viewBox="0 0 24 24"><path d="M12 2.5a9.5 9.5 0 0 0-8.2 14.3L2.5 21.5l4.8-1.3A9.5 9.5 0 1 0 12 2.5z" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/><path d="M8.6 7.8c.3-.6.6-.6.9-.6h.6c.2 0 .4 0 .6.5l.8 1.9c.1.2.1.4 0 .6l-.5.7c-.1.2-.2.4 0 .6.6 1.1 1.6 2.1 2.8 2.7.2.1.4.1.6-.1l.7-.8c.2-.2.4-.2.6-.1l1.9.9c.2.1.4.2.4.4 0 .5-.2 1.4-1 1.8-.7.4-1.6.5-3.3-.2-2-.9-3.5-2.6-4.2-3.7-.6-1-.8-2.2-.4-3z" fill="currentColor"/></svg>'; }

  function renderAll() { renderFriends(); renderEvents(); if (open && $('#view-event').classList.contains('active')) renderEvent(); }

  // ---------- links: #vriend/CODE, #e/UITNODIGING, #event/ID[/antwoord|/pin/N], #vrienden ----------
  function route(hash) {
    const [kind, a, b, c] = (hash || '').split('/');
    if (kind === 'vriend' && a) { App.welcomed(); viaFriendLink(a); return true; }
    if (kind === 'e' && a) { App.welcomed(); viaInvite(a); return true; }
    if (kind === 'event' && a) { App.welcomed(); openEvent(a, { then: b === 'antwoord' ? 'antwoord' : b === 'pin' ? { pin: c } : null }); return true; }
    if (kind === 'vrienden') { App.welcomed(); App.show('home'); App.selectTab('friends'); return true; }
    return false;
  }
  async function viaFriendLink(code) {
    App.show('home'); App.selectTab('friends'); history.replaceState(null, '', location.pathname);
    let who = null; try { who = await api('GET', `/friend/${code}`); } catch {}
    if (!who) { toast('Deze vriendlink werkt niet (meer)'); return; }
    if (me && me.code === who.code) { toast('Dit is je eigen link'); return; }
    await ensureMe(`Dan word je meteen vrienden met ${who.name}.`);
    try { const f = await api('POST', '/friends', { code }); toast(`Je bent nu vrienden met ${f.name}`); loadFriends(); } catch (e) { toast(e.message); }
  }
  async function viaInvite(invite) {
    App.show('home'); App.selectTab('events'); history.replaceState(null, '', location.pathname);
    let info; try { info = await api('GET', `/invite/${invite}`); } catch (e) { toast(e.offline ? 'Geen verbinding' : 'Deze uitnodiging werkt niet (meer)'); return; }
    const v = App.venue(info.venue);
    sheet(`<div class="invite">${v ? App.swatch(v, 'swatch big') : ''}<p class="eyebrow">${esc(info.host || 'Iemand')} nodigt je uit</p><h3>${esc(info.title)}</h3>
      <p class="sheet-sub">${esc(info.venueName)} · ${esc(whenLabel(info))} · ${info.members} ${info.members === 1 ? 'persoon' : 'personen'}</p>
      <button class="cta" data-s="join">Doe mee</button></div>`, el => {
      el.querySelector('[data-s="join"]').onclick = async () => {
        closeSheet();
        await ensureMe(`Zo ziet ${info.host || 'de groep'} dat jij het bent.`);
        try { const ev = await api('POST', `/invite/${invite}`); upsert(ev); renderEvents(); loadFriends(); openEvent(ev.id); toast('Je doet mee'); }
        catch (e) { toast(e.message); }
      };
    });
  }

  window.Social = {
    init() {
      renderAll();
      if (me) { connect(); loadAll(true); flush(); if (pushOn()) enablePush(true); }
    },
    route,
    onShow(id) { if (id === 'home') { renderFriends(); renderEvents(); } if (id === 'event') renderEvent(); },
    onTab(tab) { if (tab === 'friends' || tab === 'events') { renderAll(); loadAll(); } },
  };
})();
