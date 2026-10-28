/* plan.js — rendert een versimpelde plattegrond (Lowlands-stijl) als SVG.
 *
 * Een zaal is een object:
 * {
 *   name: "Grote Zaal",
 *   outline: [[x,y], ...]        // polygon in een 0..100 grid (muren), of
 *   round: { cx, cy, r }          // ronde zaal
 *   features: [
 *     { t:"dj",     x,y,w,h, label? }   // dj-booth: wit kader met tekst
 *     { t:"stage",  x,y,w,h, label? }   // podium: wit kader met tekst
 *     { t:"bar",    a:[x,y], b:[x,y] }  // bar: dikke witte streep
 *     { t:"in",     a:[x,y], b:[x,y], label? } // ingang: gat in de muur
 *     { t:"wc",     x,y }                // toiletten (label)
 *     { t:"smoke",  x,y }                // rookruimte (label)
 *     { t:"stairs", x,y, label? }        // trap (label)
 *     { t:"pillar", x,y }                // paal
 *     { t:"line",   a,b }                // dunne lijn (balkon, verhoging, scheiding)
 *     { t:"poly",   pts:[[x,y],...] }    // dunne gesloten lijn (balkon, podium-verhoging)
 *     { t:"label",  x,y, text }          // vrije tekst
 *   ]
 * }
 */
(function (global) {
  const W = 900, H = 1600;           // canvasformaat van het kaartje (9:16)
  const BOX = { x: 90, y: 330, w: 720, h: 1000 }; // gebied waar de zaal in past

  const PALETTE = ['#ff1a1a', '#0a2bff', '#00a651', '#ff6a00', '#7b2cff', '#ff2f8e', '#00a3a3', '#e5b800', '#2e5bff', '#d6006e', '#00b36b', '#ff4d00'];

  function colorFor(key) {
    let h = 0;
    for (let i = 0; i < key.length; i++) h = (h * 31 + key.charCodeAt(i)) >>> 0;
    return PALETTE[h % PALETTE.length];
  }

  function esc(s) { return String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c])); }

  function bounds(room) {
    if (room.round) {
      const { cx, cy, r } = room.round;
      return { minx: cx - r, miny: cy - r, maxx: cx + r, maxy: cy + r };
    }
    let minx = Infinity, miny = Infinity, maxx = -Infinity, maxy = -Infinity;
    const pts = (room.outline || []).slice();
    (room.features || []).forEach(f => {
      if (f.pts) pts.push(...f.pts);
      if (f.a) pts.push(f.a, f.b);
      if (typeof f.x === 'number' && typeof f.w === 'number') pts.push([f.x, f.y], [f.x + f.w, f.y + f.h]);
    });
    pts.forEach(([x, y]) => { minx = Math.min(minx, x); miny = Math.min(miny, y); maxx = Math.max(maxx, x); maxy = Math.max(maxy, y); });
    if (!isFinite(minx)) return { minx: 0, miny: 0, maxx: 100, maxy: 100 };
    return { minx, miny, maxx, maxy };
  }

  function makeMapper(room, box) {
    const b = bounds(room);
    const pad = Math.max(b.maxx - b.minx, b.maxy - b.miny) * 0.06 || 6;
    const bw = (b.maxx - b.minx) + pad * 2, bh = (b.maxy - b.miny) + pad * 2;
    const s = Math.min(box.w / bw, box.h / bh);
    const ox = box.x + (box.w - bw * s) / 2 - (b.minx - pad) * s;
    const oy = box.y + (box.h - bh * s) / 2 - (b.miny - pad) * s;
    const m = ([x, y]) => [ox + x * s, oy + y * s];
    m.s = s;
    return m;
  }

  function render(venue, room, opts = {}) {
    const color = room.color || venue.color || colorFor(venue.name);
    const mini = !!opts.mini;
    const H2 = mini ? 1200 : H;
    const m = makeMapper(room, mini ? { x: 80, y: 80, w: 740, h: 1040 } : BOX);
    const sw = 7;      // muurdikte
    const out = [];
    const T = (x, y, text, size, weight = 800, anchor = 'middle', extra = '') =>
      `<text x="${anchor === 'middle' ? Math.max(30 + String(text).length * size * 0.3, Math.min(W - 30 - String(text).length * size * 0.3, x)) : x}" y="${y}" fill="#fff" font-size="${size}" font-weight="${weight}" text-anchor="${anchor}" font-family="-apple-system,BlinkMacSystemFont,'Helvetica Neue',Arial,sans-serif" ${extra}>${esc(text)}</text>`;

    out.push(`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${W} ${H2}" width="${W}" height="${H2}">`);
    out.push(`<rect width="${W}" height="${H2}" fill="${color}"/>`);

    // kop
    const vn = (venue.name || '').toUpperCase();
    if (mini) { /* geen kop in miniatuur */ } else {
    const maxW = W - 180;
    const fit = (s, max) => Math.max(26, Math.min(max, maxW / (s.length * 0.66)));
    let vsize = fit(vn, 64);
    if (vsize < 40 && vn.includes(' ')) {
      // twee regels
      const words = vn.split(' '); let l1 = '', l2 = '';
      words.forEach(w => { if ((l1 + ' ' + w).trim().length <= Math.ceil(vn.length / 2) || !l1) l1 = (l1 + ' ' + w).trim(); else l2 = (l2 + ' ' + w).trim(); });
      vsize = Math.min(fit(l1, 54), fit(l2, 54));
      out.push(T(90, 110, l1, vsize, 900, 'start', 'letter-spacing="-0.02em"'));
      out.push(T(90, 110 + vsize * 1.05, l2, vsize, 900, 'start', 'letter-spacing="-0.02em"'));
    } else {
      out.push(T(90, 150, vn, vsize, 900, 'start', 'letter-spacing="-0.02em"'));
    }
    const rn = room.name || '';
    out.push(T(90, 215, rn, fit(rn, 40), 400, 'start'));
    }

    // muren
    if (room.round) {
      const [cx, cy] = m([room.round.cx, room.round.cy]);
      out.push(`<circle cx="${cx}" cy="${cy}" r="${room.round.r * m.s}" fill="none" stroke="#fff" stroke-width="${sw}"/>`);
    } else if (room.outline && room.outline.length) {
      out.push(`<polygon points="${room.outline.map(p => m(p).join(',')).join(' ')}" fill="none" stroke="#fff" stroke-width="${sw}" stroke-linejoin="miter"/>`);
    }

    // features
    (room.features || []).forEach(f => {
      switch (f.t) {
        case 'in': {
          const [ax, ay] = m(f.a), [bx, by] = m(f.b);
          // gat in de muur + korte stompjes
          out.push(`<line x1="${ax}" y1="${ay}" x2="${bx}" y2="${by}" stroke="${color}" stroke-width="${sw + 2}"/>`);
          const dx = bx - ax, dy = by - ay, len = Math.hypot(dx, dy) || 1;
          const nx = -dy / len, ny = dx / len; // normaal
          const tick = 16;
          out.push(`<line x1="${ax}" y1="${ay}" x2="${ax + nx * tick}" y2="${ay + ny * tick}" stroke="#fff" stroke-width="${sw}"/>`);
          out.push(`<line x1="${ax}" y1="${ay}" x2="${ax - nx * tick}" y2="${ay - ny * tick}" stroke="#fff" stroke-width="${sw}"/>`);
          out.push(`<line x1="${bx}" y1="${by}" x2="${bx + nx * tick}" y2="${by + ny * tick}" stroke="#fff" stroke-width="${sw}"/>`);
          out.push(`<line x1="${bx}" y1="${by}" x2="${bx - nx * tick}" y2="${by - ny * tick}" stroke="#fff" stroke-width="${sw}"/>`);
          const lx = (ax + bx) / 2, ly = (ay + by) / 2;
          const side = f.side === -1 ? -1 : 1; // label aan buitenkant
          out.push(T(lx + nx * 40 * side, ly + ny * 40 * side + 9, f.label || 'IN', 26, 800));
          break;
        }
        case 'bar': {
          const [ax, ay] = m(f.a), [bx, by] = m(f.b);
          out.push(`<line x1="${ax}" y1="${ay}" x2="${bx}" y2="${by}" stroke="#fff" stroke-width="${sw * 3.2}" stroke-linecap="butt"/>`);
          const lx = (ax + bx) / 2, ly = (ay + by) / 2;
          const dx = bx - ax, dy = by - ay, len = Math.hypot(dx, dy) || 1;
          const nx = -dy / len, ny = dx / len;
          const side = f.side === -1 ? -1 : 1;
          const horiz = Math.abs(dx) > Math.abs(dy);
          const lxx = lx + nx * 36 * side, lyy = ly + ny * 36 * side + 9;
          if (horiz) out.push(T(lxx, lyy, f.label || 'BAR', 24, 800));
          else out.push(T(lxx, lyy, f.label || 'BAR', 24, 800, 'middle', `transform="rotate(-90 ${lxx} ${lyy - 9})"`));
          break;
        }
        case 'dj':
        case 'stage': {
          const [x, y] = m([f.x, f.y]);
          const w = f.w * m.s, h = f.h * m.s;
          out.push(`<rect x="${x}" y="${y}" width="${w}" height="${h}" fill="none" stroke="#fff" stroke-width="${sw}"/>`);
          const label = f.label || (f.t === 'dj' ? 'DJ' : 'PODIUM');
          const size = Math.max(20, Math.min(w / (label.length * 0.7), h * 0.6, 60));
          out.push(T(x + w / 2, y + h / 2 + size * 0.36, label, size, 900));
          break;
        }
        case 'wc': case 'smoke': case 'stairs': case 'label': case 'lift': case 'cloak': {
          const [x, y] = m([f.x, f.y]);
          const text = f.text || f.label || { wc: 'WC', smoke: 'ROKEN', stairs: 'TRAP', lift: 'LIFT', cloak: 'GARDEROBE' }[f.t];
          out.push(T(x, y + 8, text, f.size || 22, 700));
          break;
        }
        case 'pillar': {
          const [x, y] = m([f.x, f.y]);
          out.push(`<rect x="${x - 7}" y="${y - 7}" width="14" height="14" fill="#fff"/>`);
          break;
        }
        case 'line': {
          const [ax, ay] = m(f.a), [bx, by] = m(f.b);
          out.push(`<line x1="${ax}" y1="${ay}" x2="${bx}" y2="${by}" stroke="#fff" stroke-width="${f.w || 2.5}" opacity="${f.o || 0.7}" ${f.dash ? 'stroke-dasharray="10 10"' : ''}/>`);
          break;
        }
        case 'poly': {
          out.push(`<polygon points="${f.pts.map(p => m(p).join(',')).join(' ')}" fill="none" stroke="#fff" stroke-width="${f.w || 2.5}" opacity="${f.o || 0.7}" ${f.dash ? 'stroke-dasharray="10 10"' : ''}/>`);
          if (f.text) { const c = f.pts.reduce((a, p) => [a[0] + p[0] / f.pts.length, a[1] + p[1] / f.pts.length], [0, 0]); const [x, y] = m(c); out.push(T(x, y + 8, f.text, 22, 700)); }
          break;
        }
      }
    });

    // puntjes van vrienden (canvascoördinaten 900x1600, alleen op de grote kaart)
    if (!mini) (opts.dots || []).forEach(d => {
      if (d.small) { out.push(`<circle cx="${d.x}" cy="${d.y}" r="11" fill="#fff" stroke="#000" stroke-width="3" opacity=".75"/>`); return; }
      const r = d.focus ? 30 : 24;
      if (d.focus) out.push(`<circle cx="${d.x}" cy="${d.y}" r="${r + 18}" fill="none" stroke="#fff" stroke-width="4" opacity=".8"/>`);
      out.push(`<circle cx="${d.x}" cy="${d.y}" r="${r}" fill="${d.color || '#fff'}" stroke="${d.color ? '#fff' : '#000'}" stroke-width="${d.color ? 6 : 4}"/>`);
      const ini = d.initials || '';
      out.push(`<text x="${d.x}" y="${d.y + r * 0.36}" fill="${d.color ? '#fff' : '#000'}" font-size="${r * (ini.length > 2 ? 0.66 : 0.9)}" font-weight="900" text-anchor="middle" font-family="-apple-system,BlinkMacSystemFont,'Helvetica Neue',Arial,sans-serif">${esc(ini)}</text>`);
      if (d.name) out.push(T(d.x, d.y - r - (d.focus ? 30 : 14), d.name, d.focus ? 30 : 22, 800));
    });

    // voet
    if (!opts.noFooter && !mini) {
      out.push(T(W / 2, H - 100, 'IK STA HIER', 28, 800));
    }
    out.push('</svg>');
    return out.join('');
  }

  /** Plek in woorden, vanuit de zaal gezien met DJ/podium boven: "rechts voor, bij de bar". */
  function where(room, x, y) {
    const m = makeMapper(room, BOX), b = bounds(room);
    const [x0, y0] = m([b.minx, b.miny]), [x1, y1] = m([b.maxx, b.maxy]);
    const u = (x - x0) / ((x1 - x0) || 1), v = (y - y0) / ((y1 - y0) || 1);
    const hor = u < 0.36 ? 'links' : u > 0.64 ? 'rechts' : '';
    const ver = v < 0.36 ? 'voor' : v > 0.64 ? 'achter' : 'midden';
    let deel = hor ? `${hor} ${ver}` : (ver === 'midden' ? 'in het midden' : ver);
    if (u < -0.05 || u > 1.05 || v < -0.05 || v > 1.05) deel = 'buiten de zaal';
    const NAMEN = { bar: 'de bar', dj: 'de DJ', stage: 'het podium', in: 'de ingang', wc: 'de wc', smoke: 'de rookruimte', stairs: 'de trap', cloak: 'de garderobe', lift: 'de lift' };
    let best = null;
    (room.features || []).forEach(f => {
      if (!NAMEN[f.t] || (f.t === 'in' && f.label && f.label !== 'IN')) return; // doorgang naar een andere zaal: geen ingang
      let p;
      if (f.a) { // dichtstbijzijnde punt op de lijn
        const [ax, ay] = m(f.a), [bx, by] = m(f.b), dx = bx - ax, dy = by - ay;
        const t = Math.max(0, Math.min(1, ((x - ax) * dx + (y - ay) * dy) / ((dx * dx + dy * dy) || 1)));
        p = [ax + t * dx, ay + t * dy];
      } else if (typeof f.w === 'number') {
        const [rx, ry] = m([f.x, f.y]); p = [Math.max(rx, Math.min(rx + f.w * m.s, x)), Math.max(ry, Math.min(ry + f.h * m.s, y))];
      } else p = m([f.x, f.y]);
      const d = Math.hypot(p[0] - x, p[1] - y);
      if (!best || d < best.d) best = { d, naam: NAMEN[f.t] };
    });
    return best && best.d < 110 ? `${deel}, bij ${best.naam}` : deel;
  }

  global.Plan = { render, where, colorFor, W, H, PALETTE };
})(window);
