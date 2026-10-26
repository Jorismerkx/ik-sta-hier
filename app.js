/* app.js — Ik sta hier */
(function () {
  const $ = s => document.querySelector(s);
  const $$ = s => Array.from(document.querySelectorAll(s));

  const FEEDBACK_MAIL = 'joris.merkx@agyle.nl';
  let VENUES = [];
  let current = { venue: null, room: null };
  let map, markers = [], selMarker = null, meMarker = null;
  let area = 'Alle';
  const AREAS = ['Alle', 'Centrum', 'Noord', 'West', 'Oost', 'Zuid', 'Zuidoost', 'Rand'];
  const AREA_MAP = { 'Sloterdijk': 'West', 'Westpoort': 'West', 'Nieuw-West': 'West', 'Houthavens': 'West', 'De Baarsjes': 'West', 'Zeeburgereiland': 'Oost', 'Overamstel': 'Oost', 'Zaandam': 'Rand', 'Halfweg': 'Rand', 'Amstelveen': 'Rand' };

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
  function swatch(v, cls = 'swatch') {
    const p = photoOf(v);
    return p ? `<div class="${cls} photo" style="background-image:url('${p}');background-color:${colorOf(v)}">${initials(v.name)}</div>`
             : `<div class="${cls}" style="background:${colorOf(v)}">${initials(v.name)}</div>`;
  }
  const roomsLabel = v => (v.rooms || []).length === 1 ? '1 zaal' : `${(v.rooms || []).length} zalen`;
  const areaGroup = v => AREA_MAP[v.area] || (v.area || '').split(' ')[0];
  const esc = s => String(s || '').replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

  // ---------- views ----------
  function show(id) {
    $$('.view').forEach(v => v.classList.toggle('active', v.id === 'view-' + id));
    if (id === 'home') { renderList(); renderFavs(); if (map) setTimeout(() => map.invalidateSize(), 50); }
    if (id !== 'venue' && id !== 'plan') history.replaceState(null, '', location.pathname);
  }
  $$('.back').forEach(b => b.addEventListener('click', () => show(b.dataset.back)));
  $('#info').addEventListener('click', () => show('about'));
  $('#about-mail').href = `mailto:${FEEDBACK_MAIL}?subject=${encodeURIComponent('Ik sta hier: feedback')}`;

  // ---------- welkom ----------
  function buildWall() {
    const withPhoto = VENUES.filter(v => v.photo);
    const pick = withPhoto.sort(() => Math.random() - 0.5).slice(0, 18);
    $('#wall').innerHTML = pick.map(v => `<div style="background-image:url('${photoOf(v)}')"></div>`).join('');
  }
  $('#start').addEventListener('click', () => { store.set('welcomed', true); show('home'); });

  // ---------- tabs (onderbalk) ----------
  $$('.tab').forEach(t => t.addEventListener('click', () => {
    $$('.tab').forEach(x => x.classList.toggle('active', x === t));
    $$('.pane').forEach(p => p.classList.toggle('active', p.id === 'pane-' + t.dataset.tab));
    $('#chips').classList.toggle('hidden', t.dataset.tab === 'favs');
    store.set('tab', t.dataset.tab);
    if (t.dataset.tab === 'map') { ensureMap(); setTimeout(() => map.invalidateSize(), 30); }
    if (t.dataset.tab === 'favs') renderFavs();
  }));

  // ---------- favorieten ----------
  const favs = () => store.get('favs', []);
  const isFav = v => favs().includes(v.id);
  function toggleFav(v) {
    if (!v) return;
    const f = favs().filter(id => id !== v.id);
    if (!isFav(v)) { f.unshift(v.id); toast('Opgeslagen bij favorieten'); if (navigator.vibrate) navigator.vibrate(15); }
    else toast('Uit favorieten gehaald');
    store.set('favs', f); syncFavButtons(); renderFavs();
  }
  function syncFavButtons() {
    const v = current.venue; if (!v) return;
    $$('#v-fav, #p-fav').forEach(b => b.classList.toggle('on', isFav(v)));
  }
  $('#v-fav').addEventListener('click', () => toggleFav(current.venue));
  $('#p-fav').addEventListener('click', () => toggleFav(current.venue));
  function renderFavs() {
    const el = $('#favs');
    const s = norm(q.value.trim());
    const items = favs().map(id => VENUES.find(v => v.id === id)).filter(Boolean).filter(v => !s || norm(v.name).includes(s) || norm(v.aka).includes(s));
    if (!items.length) {
      el.innerHTML = `<div class="empty"><svg viewBox="0 0 24 24"><path d="M12 3.5l2.6 5.4 5.9.8-4.3 4.1 1.1 5.9L12 16.9l-5.3 2.8 1.1-5.9-4.3-4.1 5.9-.8z" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/></svg><br>${s ? 'Niets gevonden in je favorieten.' : 'Nog geen favorieten.<br>Open een club en tik op de ster, dan staat hij hier de hele avond klaar.'}</div>`;
      return;
    }
    el.innerHTML = `<div class="letter">Favorieten</div>` + items.map(v => `
      <button class="row" data-id="${v.id}">
        ${swatch(v)}
        <div class="meta"><div class="name">${esc(v.name)}</div><div class="info">${esc(v.area || '')} · ${roomsLabel(v)}</div></div>
        <div class="chev">›</div>
      </button>`).join('');
    $$('#favs .row').forEach(r => r.addEventListener('click', () => openVenue(r.dataset.id)));
  }

  // ---------- chips ----------
  function renderChips() {
    const counts = {}; VENUES.forEach(v => { const g = areaGroup(v); counts[g] = (counts[g] || 0) + 1; });
    $('#chips').innerHTML = AREAS.filter(a => a === 'Alle' || counts[a]).map(a => `<button class="chip ${a === area ? 'active' : ''}" data-a="${a}">${a}</button>`).join('');
    $$('.chip').forEach(c => c.addEventListener('click', () => { area = c.dataset.a; renderChips(); renderList(); applyMapFilter(); }));
  }

  // ---------- search ----------
  const q = $('#q');
  q.addEventListener('input', () => { $('.search').classList.toggle('has-q', !!q.value); renderList(); applyMapFilter(); renderFavs(); });
  $('#q-clear').addEventListener('click', () => { q.value = ''; q.dispatchEvent(new Event('input')); q.blur(); });

  function filtered() {
    const s = norm(q.value.trim());
    return VENUES.filter(v => (area === 'Alle' || areaGroup(v) === area) &&
      (!s || norm(v.name).includes(s) || norm(v.aka).includes(s) || norm(v.area).includes(s) || norm(v.address).includes(s) || (v.rooms || []).some(r => norm(r.name).includes(s))));
  }

  // ---------- list ----------
  function renderList() {
    const list = $('#list');
    const items = filtered();
    let html = '';
    const recent = store.get('recent', []).map(id => VENUES.find(v => v.id === id)).filter(Boolean);
    if (recent.length && !q.value && area === 'Alle') {
      html += `<div class="letter">Recent</div><div class="recent-strip">${recent.map(v => `<button class="recent" data-id="${v.id}">${swatch(v)}<div class="name">${esc(v.name)}</div></button>`).join('')}</div>`;
    }
    if (!items.length) { list.innerHTML = html + '<div class="empty">Niets gevonden.</div>'; return; }
    const groups = {};
    items.forEach(v => { const L = norm(v.name)[0].toUpperCase(); const k = /[A-Z]/.test(L) ? L : '#'; (groups[k] = groups[k] || []).push(v); });
    const keys = Object.keys(groups).sort((a, b) => a === '#' ? 1 : b === '#' ? -1 : a.localeCompare(b));
    html += keys.map(k => `<div class="letter" id="L-${k}">${k}</div>` + groups[k].map(v => `
      <button class="row" data-id="${v.id}">
        ${swatch(v)}
        <div class="meta"><div class="name">${esc(v.name)}</div><div class="info">${esc(v.area || '')} · ${roomsLabel(v)}</div></div>
        <div class="chev">›</div>
      </button>`).join('')).join('');
    list.innerHTML = html;
    $$('#list .row, #list .recent').forEach(r => r.addEventListener('click', () => openVenue(r.dataset.id)));
  }

  // ---------- map ----------
  function ensureMap() {
    if (map) return;
    map = L.map('map', { zoomControl: false, attributionControl: true }).setView([52.3702, 4.8952], 12);
    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom: 19, attribution: '&copy; OpenStreetMap', className: 'dark-tiles' }).addTo(map);
    VENUES.forEach(v => {
      if (typeof v.lat !== 'number' || typeof v.lng !== 'number') return;
      const icon = L.divIcon({ className: '', html: `<div class="pin" style="background:${colorOf(v)}"></div>`, iconSize: [14, 14], iconAnchor: [7, 7] });
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
    card.innerHTML = `${swatch(v)}<div class="meta"><div class="name">${esc(v.name)}</div><div class="info">${esc(v.address || '')}</div></div><button class="go">Open</button>`;
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

  // ---------- venue ----------
  function remember(v) {
    const r = store.get('recent', []).filter(id => id !== v.id); r.unshift(v.id); store.set('recent', r.slice(0, 8));
  }
  function openVenue(id, opts = {}) {
    const v = VENUES.find(x => x.id === id); if (!v) return;
    current.venue = v; remember(v);
    const rooms = v.rooms || [];
    if (rooms.length === 1 && !opts.force) { openPlan(v, rooms[0], 'home'); return; }
    $('#v-name').textContent = v.name;
    $('#v-addr').textContent = v.address || '';
    const hero = $('#v-hero');
    hero.style.backgroundImage = v.photo ? `url('${photoOf(v)}')` : 'none';
    hero.style.backgroundColor = colorOf(v);
    const meta = [];
    meta.push(`<span class="pill">${roomsLabel(v)}</span>`);
    if (v.capacity) meta.push(`<span class="pill">${v.capacity} pers.</span>`);
    if (v.website) meta.push(`<a class="pill" href="${esc(v.website)}" target="_blank" rel="noopener">Website ↗</a>`);
    if (v.lat) meta.push(`<a class="pill" href="https://maps.apple.com/?q=${encodeURIComponent(v.name)}&ll=${v.lat},${v.lng}" target="_blank" rel="noopener">Route ↗</a>`);
    if (v.basis === 'plattegrond' || v.confidence === 'hoog') meta.push(`<span class="pill ok">Echte plattegrond</span>`);
    else if (v.confidence === 'laag') meta.push(`<span class="pill warn">Indicatief</span>`);
    $('#v-meta').innerHTML = meta.join('');
    const el = $('#v-rooms');
    el.innerHTML = `<h3>Zalen</h3>` + rooms.map((r, i) => `<button class="room-card" data-i="${i}"><div class="thumb">${Plan.render(v, r, { mini: true })}</div><div class="cap">${esc(r.name)}</div></button>`).join('')
      + (v.note || v.confidence === 'laag' ? `<div class="note">${v.confidence === 'laag' ? 'Indicatieve plattegrond, geen officiële tekening gevonden. ' : ''}${esc(v.note || '')}</div>` : '');
    $$('#v-rooms .room-card').forEach(b => b.addEventListener('click', () => openPlan(v, rooms[+b.dataset.i], 'venue')));
    $('.venue-body').scrollTop = 0;
    location.hash = v.id;
    syncFavButtons();
    show('venue');
  }

  // ---------- plan + tekenen ----------
  const ink = $('#plan-ink');
  const ctx = ink.getContext('2d');
  let tool = 'dot';
  let strokes = [];
  let drawing = null;

  function openPlan(v, r, backTo) {
    current.venue = v; current.room = r;
    $('.plan-top .back').dataset.back = backTo;
    $('#p-name').textContent = v.name;
    $('#p-room').textContent = r.name + (v.rooms.length > 1 ? ` · ${v.name}` : '') + (v.confidence === 'laag' ? ' · indicatief' : '');
    $('#plan-svg').innerHTML = Plan.render(v, r);
    strokes = []; $('#plan-hint').classList.remove('off');
    location.hash = v.id + '/' + v.rooms.indexOf(r);
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
  function drawStrokes(c, scale) {
    c.lineCap = 'round'; c.lineJoin = 'round';
    strokes.forEach(s => {
      if (s.type === 'dot') {
        c.beginPath(); c.arc(s.x * scale, s.y * scale, 14 * scale, 0, Math.PI * 2); c.fillStyle = '#fff'; c.fill();
        c.beginPath(); c.arc(s.x * scale, s.y * scale, 9 * scale, 0, Math.PI * 2); c.fillStyle = '#000'; c.fill();
        c.beginPath(); c.arc(s.x * scale, s.y * scale, 28 * scale, 0, Math.PI * 2); c.strokeStyle = '#fff'; c.lineWidth = 3 * scale; c.stroke();
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
      const body = `Venue: ${v.name}
Zaal: ${r.name}

Wat klopt er niet? (stuur ook een foto van de zaal als je die hebt)
`;
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
    drawStrokes(cc, scale);
    URL.revokeObjectURL(url);
    return new Promise(res => c.toBlob(res, 'image/png'));
  }
  $('#p-share').addEventListener('click', async () => {
    const v = current.venue, r = current.room;
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
    navigator.serviceWorker.register('sw.js').catch(e => console.warn('sw', e));
  }
  const isIOS = /iphone|ipad|ipod/i.test(navigator.userAgent);
  const standalone = window.matchMedia('(display-mode: standalone)').matches || navigator.standalone;
  if (isIOS && !standalone) $('#install-tip').classList.remove('hidden');

  // ---------- init ----------
  fetch('data/venues.json').then(r => r.json()).then(data => {
    VENUES = data.map(v => ({ ...v, id: v.id || norm(v.name).replace(/[^a-z0-9]+/g, '-') }))
      .sort((a, b) => norm(a.name).localeCompare(norm(b.name)));
    const nr = VENUES.reduce((a, v) => a + (v.rooms || []).length, 0);
    $('#welcome-count').textContent = `${VENUES.length} clubs en venues, ${nr} zalen`;
    $('#about-stats').textContent = `${VENUES.length} venues, ${nr} zalen. Gesloten clubs staan er niet in.`;
    renderChips(); renderList(); buildWall(); netState();
    const tab = store.get('tab', 'list');
    if (tab !== 'list') $(`.tab[data-tab="${tab}"]`).click();
    const hash = location.hash.slice(1);
    const [vid, ri] = hash.split('/');
    if (vid && VENUES.find(v => v.id === vid)) {
      const v = VENUES.find(x => x.id === vid);
      if (ri !== undefined && v.rooms[+ri]) openPlan(v, v.rooms[+ri], v.rooms.length > 1 ? 'venue' : 'home'); else openVenue(vid);
    } else show(store.get('welcomed') ? 'home' : 'welcome');
  }).catch(e => { console.error(e); show('home'); $('#list').innerHTML = '<div class="empty">Kon venues niet laden. Start via een lokale server (zie README).</div>'; });
})();
