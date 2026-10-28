/* app.js — Ik sta hier: onboarding, lijst, kaart, venuepagina en plattegrond. Vrienden en events staan in social.js. */
(function () {
  const $ = s => document.querySelector(s);
  const $$ = s => Array.from(document.querySelectorAll(s));

  const FEEDBACK_MAIL = 'joris.merkx@agyle.nl';
  let VENUES = [];
  let current = { venue: null, room: null, ctx: null };
  let map, markers = [], selMarker = null, meMarker = null;
  let area = 'Alle';
  const AREAS = ['Alle', 'Centrum', 'Noord', 'West', 'Oost', 'Zuid', 'Zuidoost', 'Rand'];
  const AREA_MAP = { 'Sloterdijk': 'West', 'Westpoort': 'West', 'Nieuw-West': 'West', 'Houthavens': 'West', 'De Baarsjes': 'West', 'Zeeburgereiland': 'Oost', 'Overamstel': 'Oost', 'Zaandam': 'Rand', 'Halfweg': 'Rand', 'Amstelveen': 'Rand' };
  const TYPES = { Clubs: v => v.type === 'club' || v.type === 'twijfel' || !v.type, Bars: v => v.type === 'bar', Podia: v => v.type === 'podium' };
  const KIND = { club: 'Club', twijfel: 'Club', bar: 'Bar', podium: 'Podium' };

  // ---------- helpers ----------
  const norm = s => (s || '').toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '');
  const store = { get(k, d) { try { return JSON.parse(localStorage.getItem(k)) ?? d; } catch { return d; } }, set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch {} } };
  function toast(msg) {
    const t = $('#toast'); t.textContent = msg; t.classList.add('show');
    clearTimeout(toast._h); toast._h = setTimeout(() => t.classList.remove('show'), 2200);
  }
  function initials(name) {
    const w = name.replace(/[^\p{L}\p{N} ]/gu, '').split(/\s+/).filter(Boolean);
    return (w.length > 1 ? w[0][0] + w[1][0] : (w[0] || '?').slice(0, 2)).toUpperCase();
  }
  const colorOf = v => v.color || Plan.colorFor(v.name);
  const photoOf = v => v.photo ? `img/venues/${v.id}.jpg` : null;
  const kindOf = v => KIND[v.type] || 'Club';
  const roomsLabel = v => (v.rooms || []).length === 1 ? '1 zaal' : `${(v.rooms || []).length} zalen`;
  const areaGroup = v => AREA_MAP[v.area] || (v.area || '').split(' ')[0];
  const esc = s => String(s || '').replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  const thumbs = new Map();
  /** Vlakje in de clubkleur met de mini-plattegrond van de eerste zaal. */
  function thumb(v, cls = 'thumb-sq') {
    if (!thumbs.has(v.id)) thumbs.set(v.id, (v.rooms || [])[0] ? Plan.render(v, v.rooms[0], { mini: true }) : '');
    return `<div class="${cls}" style="background:${colorOf(v)}">${thumbs.get(v.id)}</div>`;
  }
  const swatch = v => thumb(v);

  // programma per club (data/agenda.json, tools/agenda.py)
  let agenda = null;
  async function loadAgenda() {
    if (!agenda) { try { agenda = await fetch('data/agenda.json').then(r => (r.ok ? r.json() : {})); } catch { agenda = {}; } }
    return agenda;
  }
  const pad = n => String(n).padStart(2, '0');
  const todayStr = (d = new Date()) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
  /** Wit datumblok: dag en maand. */
  function datebox(date, live) {
    const d = new Date(date + 'T12:00:00');
    return `<span class="datebox ${live ? 'live' : ''}"><b>${d.getDate()}</b><i>${d.toLocaleDateString('nl-NL', { month: 'short' }).replace('.', '')}</i></span>`;
  }

  // ---------- views ----------
  function show(id) {
    $$('.view').forEach(v => v.classList.toggle('active', v.id === 'view-' + id));
    if (id === 'home') { renderList(); if (map) setTimeout(() => map.invalidateSize(), 50); }
    if (id !== 'venue' && id !== 'plan' && id !== 'event') history.replaceState(null, '', location.pathname);
    if (window.Social) Social.onShow(id);
  }
  $$('.back').forEach(b => b.addEventListener('click', () => show(b.dataset.back)));
  $('#info').addEventListener('click', () => show('about'));
  $('#about-mail').href = `mailto:${FEEDBACK_MAIL}?subject=${encodeURIComponent('Ik sta hier: feedback')}`;

  // ---------- onboarding: drie kleurvlakken ----------
  const OB = [
    { pick: ['paradiso', 'melkweg'], text: 'Zie waar je vrienden staan', sub: 'Elke club in Amsterdam als plattegrond. Je vrienden zijn de bolletjes.',
      dots: [{ x: 330, y: 720, initials: 'JM' }, { x: 560, y: 790, initials: 'SA' }, { x: 440, y: 1010, initials: 'MO' }] },
    { pick: ['shelter', 'bitterzoet'], text: 'Zet je puntje', sub: 'Tik op de plattegrond waar je staat. Je groep ziet het meteen, ook als je bereik slecht is.',
      dots: [{ x: 450, y: 860, initials: 'JIJ', color: '#ff2d2d', focus: true }] },
    { pick: ['melkweg', 'paradiso'], text: 'Ping zonder te typen', sub: 'Eén tik op "Waar zijn jullie?" en je hele groep trilt. Geen chat, geen gedoe.', ping: true,
      dots: [{ x: 380, y: 900, initials: 'JM', focus: true, name: 'JONAS' }] },
  ];
  let obIndex = 0;
  function buildOnboarding() {
    const slides = OB.map((s, i) => {
      const v = s.pick.map(id => VENUES.find(x => x.id === id)).find(Boolean) || VENUES.filter(x => x.basis === 'plattegrond')[i] || VENUES[i];
      if (!v || !v.rooms.length) return '';
      s.color = colorOf(v);
      const room = v.rooms.reduce((a, r) => ((r.features || []).length > (a.features || []).length ? r : a), v.rooms[0]);
      return `<div class="ob-slide" style="--c:${s.color}">
        <div class="ob-plan">${Plan.render(v, room, { noFooter: true, dots: s.dots })}
          ${s.ping ? '<div class="ob-ping"><span class="av" style="background:#000">JM</span><strong>Jonas: waar zijn jullie?</strong><span>Stuur mijn plek</span></div>' : ''}</div>
        <div class="ob-text"><h1 class="display">${esc(s.text)}</h1><p>${esc(s.sub)}</p></div></div>`;
    }).join('');
    $('#ob').innerHTML = slides;
    $('#ob-dots').innerHTML = OB.map((_, i) => `<i class="${i ? '' : 'on'}"></i>`).join('');
    obGo(0, false);
  }
  function obGo(i, scroll = true) {
    obIndex = Math.max(0, Math.min(OB.length - 1, i));
    $('#view-welcome').style.setProperty('--ob-c', OB[obIndex].color || '#ff1a1a');
    $$('#ob-dots i').forEach((d, j) => d.classList.toggle('on', j === obIndex));
    $('#ob-next').textContent = obIndex === OB.length - 1 ? 'Begin' : 'Volgende';
    if (scroll) $('#ob').scrollTo({ left: obIndex * $('#ob').clientWidth, behavior: 'smooth' });
  }
  $('#ob').addEventListener('scroll', () => {
    const i = Math.round($('#ob').scrollLeft / ($('#ob').clientWidth || 1));
    if (i !== obIndex) obGo(i, false);
  }, { passive: true });
  const begin = () => { store.set('welcomed', true); show('home'); };
  $('#ob-next').addEventListener('click', () => (obIndex === OB.length - 1 ? begin() : obGo(obIndex + 1)));
  $('#start').addEventListener('click', begin);

  // ---------- tabs (onderbalk) ----------
  function selectTab(tab) {
    $$('.tab').forEach(x => x.classList.toggle('active', x.dataset.tab === tab));
    $$('.pane').forEach(p => p.classList.toggle('active', p.id === 'pane-' + tab));
    const venues = tab === 'list' || tab === 'map';
    $('#chips').classList.toggle('hidden', !venues);
    $('.search').classList.toggle('hidden', !venues);
    store.set('tab', tab);
    if (tab === 'map') { ensureMap(); setTimeout(() => map.invalidateSize(), 30); }
    if (window.Social) Social.onTab(tab);
  }
  $$('.tab').forEach(t => t.addEventListener('click', () => selectTab(t.dataset.tab)));

  // ---------- favorieten ----------
  const FAV = 'Favorieten';
  const favs = () => store.get('favs', []);
  const isFav = v => favs().includes(v.id);
  function toggleFav(v) {
    if (!v) return;
    const f = favs().filter(id => id !== v.id);
    if (!isFav(v)) { f.unshift(v.id); toast('Opgeslagen bij favorieten'); if (navigator.vibrate) navigator.vibrate(15); }
    else toast('Uit favorieten gehaald');
    store.set('favs', f); syncFavButtons(); renderList();
  }
  function syncFavButtons() {
    const v = current.venue; if (!v) return;
    $$('#v-fav, #p-fav').forEach(b => b.classList.toggle('on', isFav(v)));
  }
  $('#v-fav').addEventListener('click', () => toggleFav(current.venue));
  $('#p-fav').addEventListener('click', () => toggleFav(current.venue));

  // ---------- chips: soort, favorieten, wijk ----------
  function renderChips() {
    const counts = {}; VENUES.forEach(v => { const g = areaGroup(v); counts[g] = (counts[g] || 0) + 1; });
    const chip = a => `<button class="chip ${a === area ? 'active' : ''} ${a === FAV ? 'fav-chip' : ''}" data-a="${a}">${a === FAV ? '★ ' : ''}${a}</button>`;
    const types = Object.keys(TYPES).filter(t => VENUES.some(TYPES[t]));
    $('#chips').innerHTML = ['Alle', FAV, ...types].map(chip).join('') + '<span class="chip-sep"></span>' + AREAS.slice(1).filter(a => counts[a]).map(chip).join('');
    $$('#chips .chip').forEach(c => c.addEventListener('click', () => { area = c.dataset.a; renderChips(); renderList(); applyMapFilter(); }));
  }

  // ---------- zoeken ----------
  const q = $('#q');
  q.addEventListener('input', () => { $('.search').classList.toggle('has-q', !!q.value); renderList(); applyMapFilter(); });
  $('#q-clear').addEventListener('click', () => { q.value = ''; q.dispatchEvent(new Event('input')); q.blur(); });

  function filtered() {
    const s = norm(q.value.trim());
    const fav = new Set(favs());
    const ok = v => area === 'Alle' || (area === FAV ? fav.has(v.id) : TYPES[area] ? TYPES[area](v) : areaGroup(v) === area);
    return VENUES.filter(v => ok(v) &&
      (!s || norm(v.name).includes(s) || norm(v.aka).includes(s) || norm(v.area).includes(s) || norm(v.address).includes(s) || (v.rooms || []).some(r => norm(r.name).includes(s))));
  }

  // ---------- lijst ----------
  function renderList() {
    const list = $('#list');
    const items = filtered();
    let html = '';
    const recent = store.get('recent', []).map(id => VENUES.find(v => v.id === id)).filter(Boolean);
    if (recent.length && !q.value && area === 'Alle') {
      html += `<div class="letter">Recent</div><div class="recent-strip">${recent.map(v => `<button class="recent" data-id="${v.id}" style="background:${colorOf(v)}"><span>${esc(v.name)}</span></button>`).join('')}</div>`;
    }
    if (!items.length) {
      list.innerHTML = html + (area === FAV && !q.value
        ? `<div class="empty fav-empty"><svg viewBox="0 0 24 24"><path d="M12 3.5l2.6 5.4 5.9.8-4.3 4.1 1.1 5.9L12 16.9l-5.3 2.8 1.1-5.9-4.3-4.1 5.9-.8z" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/></svg><br>Nog geen favorieten.<br>Open een club en tik op de ster.</div>`
        : '<div class="empty">Niets gevonden.</div>');
      return;
    }
    const groups = {};
    items.forEach(v => { const L = norm(v.name)[0].toUpperCase(); const k = /[A-Z]/.test(L) ? L : '#'; (groups[k] = groups[k] || []).push(v); });
    const keys = Object.keys(groups).sort((a, b) => a === '#' ? 1 : b === '#' ? -1 : a.localeCompare(b));
    html += keys.map(k => `<div class="letter" id="L-${k}">${k}</div>` + groups[k].map(v => `
      <button class="row" data-id="${v.id}">
        ${thumb(v)}
        <div class="meta"><div class="name">${esc(v.name)}</div><div class="info">${esc(v.area || '')} · ${roomsLabel(v)}</div></div>
        ${v.type === 'bar' || v.type === 'podium' ? `<span class="tag">${kindOf(v)}</span>` : ''}
        <div class="chev">›</div>
      </button>`).join('')).join('');
    list.innerHTML = html;
    $$('#list .row, #list .recent').forEach(r => r.addEventListener('click', () => openVenue(r.dataset.id)));
  }

  // ---------- kaart ----------
  function ensureMap() {
    if (map) return;
    map = L.map('map', { zoomControl: false, attributionControl: true }).setView([52.3702, 4.8952], 12);
    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom: 19, attribution: '&copy; OpenStreetMap', className: 'dark-tiles' }).addTo(map);
    VENUES.forEach(v => {
      if (typeof v.lat !== 'number' || typeof v.lng !== 'number') return;
      const icon = L.divIcon({ className: '', html: `<div class="pin" style="background:${colorOf(v)}"></div>`, iconSize: [16, 16], iconAnchor: [8, 8] });
      const mk = L.marker([v.lat, v.lng], { icon }).addTo(map);
      mk.venue = v;
      mk.on('click', () => selectMarker(mk));
      markers.push(mk);
    });
    map.on('click', () => { $('#map-card').classList.add('hidden'); if (selMarker) { selMarker.getElement().firstChild.classList.remove('sel'); selMarker = null; } });
    applyMapFilter();
  }
  function selectMarker(mk) {
    if (selMarker) selMarker.getElement().firstChild.classList.remove('sel');
    selMarker = mk; mk.getElement().firstChild.classList.add('sel');
    const v = mk.venue;
    const card = $('#map-card');
    card.innerHTML = `${thumb(v)}<div class="meta"><div class="name">${esc(v.name)}</div><div class="info">${esc(v.address || '')}</div></div><button class="go">Open</button>`;
    card.classList.remove('hidden');
    card.querySelector('.go').addEventListener('click', () => openVenue(v.id));
    map.panTo(mk.getLatLng());
  }
  function applyMapFilter() {
    if (!map) return;
    const ids = new Set(filtered().map(v => v.id));
    markers.forEach(mk => { const on = ids.has(mk.venue.id); if (on && !map.hasLayer(mk)) mk.addTo(map); if (!on && map.hasLayer(mk)) map.removeLayer(mk); });
  }
  $('#locate').addEventListener('click', () => {
    if (!navigator.geolocation) { toast('Geen locatie beschikbaar'); return; }
    navigator.geolocation.getCurrentPosition(p => {
      const ll = [p.coords.latitude, p.coords.longitude];
      if (!meMarker) meMarker = L.marker(ll, { icon: L.divIcon({ className: '', html: '<div class="me"></div>', iconSize: [16, 16], iconAnchor: [8, 8] }), zIndexOffset: 1000 }).addTo(map);
      else meMarker.setLatLng(ll);
      map.setView(ll, 15);
    }, () => toast('Locatie niet beschikbaar'), { enableHighAccuracy: true, timeout: 8000 });
  });

  // ---------- venuepagina ----------
  function remember(v) {
    const r = store.get('recent', []).filter(id => id !== v.id); r.unshift(v.id); store.set('recent', r.slice(0, 8));
  }
  function openVenue(id) {
    const v = VENUES.find(x => x.id === id); if (!v) return;
    current.venue = v; remember(v);
    const rooms = v.rooms || [];
    $('#v-hero').style.setProperty('--c', colorOf(v));
    $('#v-kind').textContent = [kindOf(v), v.area].filter(Boolean).join(' · ');
    $('#v-name').textContent = v.name;
    $('#v-name').classList.toggle('long', v.name.length > 14 || v.name.split(' ').some(w => w.length > 9));
    $('#v-addr').textContent = v.address || '';

    const meta = [`<span class="pill">${roomsLabel(v)}</span>`];
    if (v.capacity) meta.push(`<span class="pill">${v.capacity} pers.</span>`);
    if (v.verified) meta.push('<span class="pill ok">✓ Van de club zelf</span>');
    else if (v.basis === 'plattegrond' || v.confidence === 'hoog') meta.push('<span class="pill ok">Echte plattegrond</span>');
    else if (v.confidence === 'laag') meta.push('<span class="pill warn">Indicatief</span>');
    if (v.website) meta.push(`<a class="pill" href="${esc(v.website)}" target="_blank" rel="noopener">Website ↗</a>`);
    if (v.lat) meta.push(`<a class="pill" href="https://maps.apple.com/?q=${encodeURIComponent(v.name)}&ll=${v.lat},${v.lng}" target="_blank" rel="noopener">Route ↗</a>`);
    $('#v-meta').innerHTML = meta.join('');

    // jouw event vanavond in deze club
    const ev = window.Social && Social.tonightAt(v.id);
    const tn = $('#v-tonight');
    tn.classList.toggle('hidden', !ev);
    if (ev) {
      tn.innerHTML = `<button class="tonight">${datebox(ev.date, true)}<div class="meta"><strong>${esc(ev.title)}</strong><span>Jouw event vanavond · ${ev.members.length} ${ev.members.length === 1 ? 'persoon' : 'personen'}</span></div><em>Open</em></button>`;
      tn.querySelector('button').onclick = () => Social.open(ev.id);
    }

    const el = $('#v-rooms');
    el.innerHTML = rooms.map((r, i) => `<button class="room-card ${rooms.length === 1 ? 'one' : ''}" data-i="${i}"><div class="thumb" style="background:${colorOf(v)}">${Plan.render(v, r, { mini: true })}</div><div class="cap">${esc(r.name)}</div></button>`).join('');
    $$('#v-rooms .room-card').forEach(b => b.addEventListener('click', () => openPlan(v, rooms[+b.dataset.i], 'venue')));
    const note = (v.confidence === 'laag' ? 'Indicatieve plattegrond, geen officiële tekening gevonden. ' : '') + (v.note || '');
    $('#v-note').textContent = note; $('#v-note').classList.toggle('hidden', !note);

    $('#v-agenda-wrap').classList.add('hidden');
    loadAgenda().then(a => {
      if (current.venue !== v) return;
      const list = ((a || {})[v.id] || []).filter(e => e.date >= todayStr()).slice(0, 4);
      $('#v-agenda-wrap').classList.toggle('hidden', !list.length);
      $('#v-agenda').innerHTML = list.map(e => `<a class="ag-item" href="${esc(e.url)}" target="_blank" rel="noopener">${datebox(e.date)}<div class="meta"><strong>${esc(e.title)}</strong><span>${new Date(e.date + 'T12:00:00').toLocaleDateString('nl-NL', { weekday: 'long' })}${e.time ? ' · ' + e.time : ''}</span></div></a>`).join('');
    });

    const p = photoOf(v);
    $('#v-photo-wrap').classList.toggle('hidden', !p);
    if (p) $('#v-photo').src = p;

    $('#v-scroll').scrollTop = 0;
    location.hash = v.id;
    syncFavButtons();
    show('venue');
  }
  $('#v-here').addEventListener('click', () => {
    const v = current.venue; if (!v) return;
    const ev = window.Social && Social.tonightAt(v.id);
    if (ev) { Social.here(ev); return; }
    openPlan(v, v.rooms[0], 'venue');
  });
  $('#v-new').addEventListener('click', () => { if (current.venue && window.Social) Social.newEvent(current.venue.id); });

  // ---------- plattegrond + tekenen ----------
  const ink = $('#plan-ink');
  const ctx = ink.getContext('2d');
  let tool = 'dot';
  let strokes = [];
  let drawing = null;

  /** ctx (optioneel, vanuit een event): { dots, hint, onSend({room, x, y, label}) } — dan wordt "Deel" "Stuur" naar de groep. */
  function openPlan(v, r, backTo, ctx = null) {
    current.venue = v; current.room = r; current.ctx = ctx;
    $('#view-plan .back').dataset.back = backTo;
    $('#p-name').textContent = v.name;
    $('#p-room').textContent = r.name + (v.confidence === 'laag' ? ' · indicatief' : '');
    $('#plan-svg').innerHTML = Plan.render(v, r, ctx ? { dots: ctx.dots || [] } : {});
    strokes = []; $('#plan-hint').classList.remove('off');
    $('#plan-hint').textContent = ctx ? (ctx.hint || 'Tik waar je staat, dan Stuur') : 'Tik waar je staat';
    $('#p-share').textContent = ctx ? 'Stuur' : 'Deel';
    $('#p-share').classList.toggle('send', !!ctx);
    // andere zalen van deze club (alleen buiten een event)
    const multi = !ctx && v.rooms.length > 1;
    $('#p-rooms').classList.toggle('hidden', !multi);
    if (multi) {
      $('#p-rooms').innerHTML = v.rooms.map((x, i) => `<button class="chip ${x === r ? 'active' : ''}" data-i="${i}">${esc(x.name)}</button>`).join('');
      $$('#p-rooms .chip').forEach(b => b.onclick = () => openPlan(v, v.rooms[+b.dataset.i], backTo));
    }
    if (!ctx) location.hash = v.id + '/' + v.rooms.indexOf(r);
    syncFavButtons();
    show('plan');
    sizeInk(); setTimeout(sizeInk, 30);
  }
  function sizeInk() {
    const card = $('#plan-card');
    const wrap = $('#plan-wrap').getBoundingClientRect();
    const aw = wrap.width - 32, ah = wrap.height - 8;
    let w = aw, h = w * 16 / 9;
    if (h > ah) { h = ah; w = h * 9 / 16; }
    card.style.width = Math.floor(w) + 'px'; card.style.height = Math.floor(h) + 'px';
    const rect = card.getBoundingClientRect();
    const dpr = Math.min(window.devicePixelRatio || 1, 3);
    ink.width = Math.round(rect.width * dpr); ink.height = Math.round(rect.height * dpr);
    ink.style.width = rect.width + 'px'; ink.style.height = rect.height + 'px';
    redraw();
  }
  window.addEventListener('resize', () => { if ($('#view-plan').classList.contains('active')) sizeInk(); });

  function toCanvas(e) {
    const rect = ink.getBoundingClientRect();
    return [(e.clientX - rect.left) / rect.width * Plan.W, (e.clientY - rect.top) / rect.height * Plan.H];
  }
  /** Jouw puntje: rood met witte rand en een label erboven ("JIJ" in de app, "IK" op het gedeelde plaatje). */
  function drawStrokes(c, scale, label = 'JIJ') {
    c.lineCap = 'round'; c.lineJoin = 'round';
    strokes.forEach(s => {
      if (s.type === 'dot') {
        const x = s.x * scale, y = s.y * scale;
        c.beginPath(); c.arc(x, y, 34 * scale, 0, Math.PI * 2); c.strokeStyle = 'rgba(255,255,255,.85)'; c.lineWidth = 4 * scale; c.stroke();
        c.beginPath(); c.arc(x, y, 20 * scale, 0, Math.PI * 2); c.fillStyle = '#ff2d2d'; c.fill(); c.strokeStyle = '#fff'; c.lineWidth = 6 * scale; c.stroke();
        c.font = `900 ${28 * scale}px -apple-system,BlinkMacSystemFont,'Helvetica Neue',Arial,sans-serif`; c.textAlign = 'center'; c.fillStyle = '#fff';
        c.fillText(label, x, y - 48 * scale);
      } else {
        c.beginPath(); c.strokeStyle = '#000'; c.lineWidth = 12 * scale;
        s.pts.forEach((p, i) => i ? c.lineTo(p[0] * scale, p[1] * scale) : c.moveTo(p[0] * scale, p[1] * scale));
        if (s.pts.length === 1) c.lineTo(s.pts[0][0] * scale + 0.1, s.pts[0][1] * scale);
        c.stroke();
        c.strokeStyle = '#fff'; c.lineWidth = 7 * scale; c.stroke();
      }
    });
  }
  function redraw() { ctx.clearRect(0, 0, ink.width, ink.height); drawStrokes(ctx, ink.width / Plan.W); }

  ink.addEventListener('pointerdown', e => {
    e.preventDefault(); ink.setPointerCapture(e.pointerId);
    $('#plan-hint').classList.add('off');
    const [x, y] = toCanvas(e);
    if (tool === 'dot') { strokes = strokes.filter(s => s.type !== 'dot'); strokes.push({ type: 'dot', x, y }); redraw(); if (navigator.vibrate) navigator.vibrate(10); }
    else if (tool === 'pen') { drawing = { type: 'path', pts: [[x, y]] }; strokes.push(drawing); redraw(); }
  });
  ink.addEventListener('pointermove', e => {
    if (!drawing) return;
    const [x, y] = toCanvas(e);
    const last = drawing.pts[drawing.pts.length - 1];
    if (Math.hypot(x - last[0], y - last[1]) > 3) { drawing.pts.push([x, y]); redraw(); }
  });
  const endStroke = () => { drawing = null; };
  ink.addEventListener('pointerup', endStroke); ink.addEventListener('pointercancel', endStroke);

  $$('.tool').forEach(b => b.addEventListener('click', () => {
    const t = b.dataset.tool;
    if (t === 'undo') { strokes.pop(); redraw(); return; }
    if (t === 'clear') { strokes = []; redraw(); return; }
    if (t === 'report') {
      const v = current.venue, r = current.room;
      const body = `Venue: ${v.name}\nZaal: ${r.name}\n\nWat klopt er niet? (stuur ook een foto van de zaal als je die hebt)\n`;
      location.href = `mailto:${FEEDBACK_MAIL}?subject=${encodeURIComponent('Ik sta hier: ' + v.name + ' / ' + r.name)}&body=${encodeURIComponent(body)}`;
      return;
    }
    tool = t; $$('.tool').forEach(x => x.classList.toggle('active', x === b));
  }));

  // ---------- delen ----------
  async function composeImage() {
    const svg = $('#plan-svg svg');
    const xml = new XMLSerializer().serializeToString(svg);
    const url = URL.createObjectURL(new Blob([xml], { type: 'image/svg+xml;charset=utf-8' }));
    const img = new Image();
    await new Promise((res, rej) => { img.onload = res; img.onerror = rej; img.src = url; });
    const c = document.createElement('canvas');
    const scale = 1242 / Plan.W;
    c.width = Plan.W * scale; c.height = Plan.H * scale;
    const cc = c.getContext('2d');
    cc.drawImage(img, 0, 0, c.width, c.height);
    drawStrokes(cc, scale, 'IK');
    URL.revokeObjectURL(url);
    return new Promise(res => c.toBlob(res, 'image/png'));
  }
  $('#p-share').addEventListener('click', async () => {
    const v = current.venue, r = current.room;
    if (current.ctx) {
      const dot = strokes.find(s => s.type === 'dot');
      if (!dot) { toast('Tik eerst waar je staat'); return; }
      current.ctx.onSend({ room: v.rooms.indexOf(r), x: Math.round(dot.x), y: Math.round(dot.y), label: Plan.where(r, dot.x, dot.y) });
      return;
    }
    if (!strokes.length) { toast('Zet eerst je puntje'); return; }
    try {
      const blob = await composeImage();
      const file = new File([blob], `ik-sta-hier-${v.id}.png`, { type: 'image/png' });
      const text = `Ik sta hier: ${v.name} · ${r.name}`;
      const cap = window.Capacitor && window.Capacitor.isNativePlatform && window.Capacitor.isNativePlatform() ? window.Capacitor.Plugins : null;
      if (cap && cap.Share && cap.Filesystem) {
        // native app: PNG naar cache schrijven en via het systeem-deelvenster (WhatsApp enz.) delen
        const b64 = await new Promise(res => { const fr = new FileReader(); fr.onload = () => res(fr.result.split(',')[1]); fr.readAsDataURL(blob); });
        const w = await cap.Filesystem.writeFile({ path: file.name, data: b64, directory: 'CACHE' });
        await cap.Share.share({ title: text, text, files: [w.uri], dialogTitle: 'Deel je plek' });
      } else if (navigator.canShare && navigator.canShare({ files: [file] })) {
        await navigator.share({ files: [file], title: text, text });
      } else {
        const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = file.name; a.click();
        toast('Plaatje gedownload');
      }
    } catch (e) {
      if (e && e.name === 'AbortError') return;
      console.error(e); toast('Delen mislukt');
    }
  });

  // ---------- offline / pwa ----------
  function netState() { $('#offline').classList.toggle('hidden', navigator.onLine !== false); }
  window.addEventListener('online', netState); window.addEventListener('offline', netState);
  if ('serviceWorker' in navigator && location.protocol.startsWith('http')) {
    // nieuwe versie actief? één keer herladen, anders blijft de oude schil (css/js) staan tot de volgende start
    const hadSW = !!navigator.serviceWorker.controller;
    navigator.serviceWorker.addEventListener('controllerchange', () => { if (hadSW && !netState.reloaded) { netState.reloaded = true; location.reload(); } });
    navigator.serviceWorker.register('sw.js').catch(e => console.warn('sw', e));
  }
  const isIOS = /iphone|ipad|ipod/i.test(navigator.userAgent);
  const standalone = window.matchMedia('(display-mode: standalone)').matches || navigator.standalone;
  if (isIOS && !standalone) $('#install-tip').classList.remove('hidden');

  // ---------- gedeeld met social.js ----------
  window.App = {
    $, $$, esc, toast, store, show, swatch, thumb, datebox, colorOf, initials, openPlan, openVenue, selectTab, loadAgenda,
    venues: () => VENUES, venue: id => VENUES.find(v => v.id === id),
    welcomed: () => { store.set('welcomed', true); },
  };

  function route(hash) {
    if (window.Social && Social.route(hash)) return;
    const [vid, ri] = hash.split('/');
    if (vid && VENUES.find(v => v.id === vid)) {
      const v = VENUES.find(x => x.id === vid);
      if (ri !== undefined && v.rooms[+ri]) { openVenue(vid); openPlan(v, v.rooms[+ri], 'venue'); } else openVenue(vid);
    } else show(store.get('welcomed') ? 'home' : 'welcome');
  }

  // ---------- init ----------
  fetch('data/venues.json').then(r => r.json()).then(data => {
    VENUES = data.map(v => ({ ...v, id: v.id || norm(v.name).replace(/[^a-z0-9]+/g, '-') }))
      .sort((a, b) => norm(a.name).localeCompare(norm(b.name)));
    const nr = VENUES.reduce((a, v) => a + (v.rooms || []).length, 0);
    $('#welcome-count').textContent = `${VENUES.length} clubs, bars en podia · ${nr} zalen`;
    $('#about-stats').textContent = `${VENUES.length} venues, ${nr} zalen. Gesloten clubs en losse eventlocaties staan er niet in.`;
    renderChips(); renderList(); buildOnboarding(); netState();
    if (window.Social) Social.init();
    const tab = store.get('tab', 'list');
    selectTab(['list', 'map', 'friends', 'events'].includes(tab) ? tab : 'list');
    route(location.hash.slice(1));
    // links uit meldingen en uitnodigingen terwijl de app al open is
    window.addEventListener('hashchange', () => { if (window.Social && Social.route(location.hash.slice(1))) return; });
  }).catch(e => { console.error(e); show('home'); $('#list').innerHTML = '<div class="empty">Kon venues niet laden. Start via een lokale server (zie README).</div>'; });
})();
