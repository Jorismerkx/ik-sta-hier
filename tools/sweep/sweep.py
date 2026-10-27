"""Documentensweep: zoek per venue automatisch in openbare overheidsbronnen naar documenten met de indeling.

Gebruik: python -X utf8 tools/sweep/sweep.py              (alle venues die nog geen resultaat hebben; --opnieuw = alles)
         python -X utf8 tools/sweep/sweep.py id1 id2 ...   (alleen deze)
         python -X utf8 tools/sweep/sweep.py --bekendmakingen  (alleen vergunningen opnieuw, op alle adressen van het pand)
Vooraf:  python -X utf8 tools/sweep/plannen.py <map met de PDOK-bulkbestanden>  (maakt data/sweep/plannen-0363.json)

Bronnen (alle openbaar, zonder sleutel):
  bouwdossiers   bouwdossiers.amsterdam.nl/iiif-metadata   alleen metadata; scans worden niet geopend (voorwaarden Stadsarchief)
  bekendmakingen repository.overheid.nl/sru                 vergunningen per adres, met zaaknummer uit metadata.xml
  plannen        ruimtelijkeplannen.nl/documents           toelichting en bijlagen van elk plan waarin het pand ligt
  woo            open.overheid.nl API                       openbaar gemaakte Woo-documenten die het adres noemen

Schrijft: data/sweep/<id>.json (alles wat gevonden is, plus kandidaatpagina's)
          data/sources/<id>/sweep/*.png (kandidaatpagina's om te bekijken; niet in git)
          data/sources/_sweep_cache/ (gedownloade PDF's, gedeeld tussen venues; niet in git)
"""
import sys, os, re, json, html, hashlib, time, threading
from concurrent.futures import ProcessPoolExecutor
import requests, fitz

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import footprint

OUT = os.path.join(ROOT, 'data', 'sweep')
CACHE = os.path.join(ROOT, 'data', 'sources', '_sweep_cache')
os.makedirs(OUT, exist_ok=True); os.makedirs(CACHE, exist_ok=True)
UA = {'User-Agent': 'ik-sta-hier/0.3 (prive project; documentensweep)'}
VENUES = {v['id']: v for v in json.load(open(os.path.join(ROOT, 'data', 'venues.json'), encoding='utf-8'))}
PLANS = json.load(open(os.path.join(OUT, 'plannen-0363.json'), encoding='utf-8'))
for p in PLANS:
    xs = [q[0] for r in p['rings'] for q in r]; ys = [q[1] for r in p['rings'] for q in r]
    p['bbox'] = (min(xs), min(ys), max(xs), max(ys)) if xs else (0, 0, 0, 0)

MAX_PLAN = 5_000_000      # m²; grotere (stadsbrede thema-)plannen bevatten geen tekeningen van één pand
KLEIN_PLAN = 50_000          # m²; kleiner plan = waarschijnlijk over dit pand: alle bijlagen doorzoeken
MAX_PDF = 120 * 2 ** 20
MAX_KANDIDATEN = 14
INDELING = re.compile(r'plattegrond|begane\s*grond|verdieping|indeling|situatietekening|vluchtweg|ontruiming|gebruiksplan|'
                      r'inrichtingstekening|dansvloer|podium|garderobe|nooduitgang|toiletten|schaal\s*1\s*:\s*\d+|1\s*:\s*(50|100|200)\b|'
                      r'zaal|foyer|kelder|floor\s*plan|ground\s*floor|stage', re.I)
STERK = re.compile(r'plattegrond|begane\s*grond|indeling|vluchtweg|gebruiksplan|inrichtingstekening|plattegronden|floor\s*plan', re.I)
THEMA = re.compile(r'kennisgeving|vaststellingsbesluit|verkeer|lucht|archeolog|natuur|ecolog|flora|fauna|externe veiligheid|water|bodem|'
                   r'mobiliteit|parkeer|staat van|lijst|verbeelding|printversie regels|cultuurhistor|stikstof|windhinder|bezonning|schaduw|explosie', re.I)
lock = threading.Lock()

_tl = threading.local()
def sessie():
    # één sessie per thread: hergebruikt verbindingen en laadt de certificaten maar één keer
    if not hasattr(_tl, 's'):
        _tl.s = requests.Session(); _tl.s.headers.update(UA)
    return _tl.s

def get(url, **kw):
    timeout = kw.pop('timeout', 45)
    for i in range(3):
        try:
            r = sessie().get(url, timeout=timeout, **kw)
            if r.status_code in (429, 502, 503, 504): time.sleep(3 + 5 * i); continue
            return r
        except requests.RequestException:
            time.sleep(2 + 3 * i)
    return None

# ---------- adres en termen ----------
def adres(v):
    for a in (v.get('address') or '').split(','):
        m = re.match(r"^(.*?)\s+(\d+)\s*([A-Za-z]?)(?:\s*[-/]\s*(\d+))?\b.*$", a.strip())
        if m and not re.match(r'^\d{4}$', m.group(2)): break
    else: return None
    straat, nr, lt, nr2 = m.groups()
    nrs = [nr] + ([nr2] if nr2 and nr2 != nr and int(nr2) - int(nr) <= 12 else [])
    if lt: nrs += [nr + lt.upper(), f'{nr} {lt.upper()}']
    pc = re.search(r'\b(\d{4})\s?([A-Z]{2})\b', v.get('address') or '')
    return {'straat': straat.strip(), 'nrs': nrs, 'postcode': (pc.group(1) + pc.group(2)) if pc else None}

def termen(v, ad):
    """Woorden waaraan je het pand in een document herkent."""
    t = []
    if ad:
        t += [f"{ad['straat']} {n}" for n in ad['nrs']]
        if ad['postcode']: t += [ad['postcode'], ad['postcode'][:4] + ' ' + ad['postcode'][4:]]
    for n in [v['name']] + ([v['aka']] if v.get('aka') else []):
        n = re.sub(r'\s*\(.*?\)', '', n).strip()
        if len(n) >= 6 and n.lower() not in ('amsterdam', 'club', 'cafe', 'café'): t.append(n)
    return t

def plat(s):
    return re.sub(r'[^0-9a-z]', '', s.lower())

def treffers(text, ts):
    """Termen die in de tekst staan. Spaties tellen niet mee (OCR en PDF's plakken woorden aan elkaar)."""
    low = plat(text)
    out = []
    for x in ts:
        k = plat(x)
        if k and re.search(re.escape(k) + (r'(?![0-9])' if k[-1].isdigit() else ''), low): out.append(x)
    return out

# ---------- RD ----------
def rd(lat, lon):
    dp, dl = 0.36 * (lat - 52.15517440), 0.36 * (lon - 5.38720621)
    R = {(0, 1): 190094.945, (1, 1): -11832.228, (2, 1): -114.221, (0, 3): -32.391, (1, 0): -0.705, (3, 1): -2.340, (1, 3): -0.608, (0, 2): -0.008, (2, 3): 0.148}
    S = {(1, 0): 309056.544, (0, 2): 3638.893, (2, 0): 73.077, (1, 2): -157.984, (3, 0): 59.788, (0, 1): 0.433, (2, 2): -6.439, (1, 1): -0.032, (0, 4): 0.092, (1, 4): -0.054}
    return (155000 + sum(c * dp ** p * dl ** q for (p, q), c in R.items()), 463000 + sum(c * dp ** p * dl ** q for (p, q), c in S.items()))

def pip(pt, ring):
    x, y = pt; ins = False
    for i in range(len(ring)):
        (x1, y1), (x2, y2) = ring[i - 1], ring[i]
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1: ins = not ins
    return ins

# ---------- bronnen ----------
def pand_van(v):
    fp = os.path.join(ROOT, 'data', 'footprints', v['id'] + '.json')
    if os.path.exists(fp):
        d = json.load(open(fp, encoding='utf-8'))
        return d['pand']['bag_id'], (v['lat'], v['lng'])
    try:
        lat, lon, _ = footprint.locate(v)
        for f in footprint.panden(lat, lon, 40):
            if footprint.inside((lon, lat), footprint.ring(f)):
                return f['properties']['identificatie'], (lat, lon)
        return None, (lat, lon)
    except Exception:
        return None, (v.get('lat'), v.get('lng'))

def bouwdossiers(pand):
    if not pand: return {'fout': 'geen pand'}
    url, out = f'https://bouwdossiers.amsterdam.nl/iiif-metadata/bouwdossier/?pand={pand}', []
    while url:
        r = get(url)
        if not r or r.status_code != 200: return {'fout': f'http {r.status_code if r else "-"}', 'dossiers': out}
        d = r.json()
        for x in d.get('results', []):
            docs = x.get('documenten') or []
            out.append({'dossier': f"{x.get('stadsdeel')}_{x.get('dossiernr')}", 'titel': x.get('titel'), 'datum': x.get('datering'),
                        'soort': x.get('dossier_type'), 'toegang': x.get('access'), 'olo': x.get('olo_liaan_nummer'),
                        'bestanden': sum(len(doc.get('bestanden') or []) for doc in docs),
                        'omschrijving': sorted({doc.get('document_omschrijving') for doc in docs if doc.get('document_omschrijving')})[:8],
                        'url': f"https://bouwdossiers.amsterdam.nl/bouwdossier/{x.get('stadsdeel')}_{x.get('dossiernr')}"})
        url = (d.get('_links', {}).get('next') or {}).get('href')
    out.sort(key=lambda x: x['datum'] or '', reverse=True)
    return {'n': len(out), 'openbaar': sum(1 for x in out if x['toegang'] == 'PUBLIC'),
            'laatste': out[0]['datum'] if out else None, 'dossiers': out}

TEKENING_SOORT = re.compile(r'omgevingsvergunning|bouw|verbouw|wijzig|indeling|brandveilig|gebruik|vergro|constructie|interne|afwijk|aanpassen|realiseren|transformeren', re.I)

def pand_adressen(pand, maxn=12):
    """Alle BAG-adressen in het pand: vergunningen staan vaak op een ander adres van hetzelfde gebouw (hoekpanden)."""
    if not pand: return []
    flt = ('<Filter xmlns="http://www.opengis.net/fes/2.0"><PropertyIsEqualTo><ValueReference>pandidentificatie</ValueReference>'
           f'<Literal>{pand}</Literal></PropertyIsEqualTo></Filter>')
    r = get('https://service.pdok.nl/lv/bag/wfs/v2_0', params={'service': 'WFS', 'version': '2.0.0', 'request': 'GetFeature',
            'typeNames': 'bag:verblijfsobject', 'outputFormat': 'application/json', 'count': 500, 'FILTER': flt}, timeout=60)
    if not r or r.status_code != 200: return []
    out = []
    for f in r.json().get('features', []):
        p = f['properties']
        a = f"{p.get('openbare_ruimte')} {p.get('huisnummer')}{(p.get('huisletter') or '').upper()}"
        if a not in out: out.append(a)
    return sorted(out)[:maxn]

def bekendmakingen(ad, extra=()):
    if not ad and not extra: return {'fout': 'geen adres'}
    recs = {}
    zoek = [f'{ad["straat"]} {n}' for n in ad['nrs']] if ad else []
    zoek += [a for a in extra if a not in zoek]
    for term in zoek:
        q = f'c.product-area==officielepublicaties and cql.textAndIndexes="{term}"'
        r = get('https://repository.overheid.nl/sru', params={'query': q, 'maximumRecords': 200}, timeout=60)
        if not r or r.status_code != 200: continue
        for rec in r.text.split('<sru:record>')[1:]:
            f = lambda tag: (re.findall(rf'<{tag}[^>]*>(.*?)</{tag}>', rec, re.S) or [''])[0]
            i = f('dcterms:identifier')
            if not i or i in recs: continue
            meta = re.findall(r'<gzd:itemUrl manifestation="metadata">([^<]+)', rec)
            recs[i] = {'id': i, 'titel': html.unescape(f('dcterms:title')), 'soort': f('dcterms:type'), 'datum': f('dcterms:available') or f('dcterms:modified'),
                       'onderwerp': html.unescape(f('dcterms:abstract')), 'activiteit': f('overheidwetgeving:activiteit'),
                       'url': f'https://zoek.officielebekendmakingen.nl/{i}.html', '_meta': meta[0] if meta else None}
    lijst = sorted(recs.values(), key=lambda x: x['datum'], reverse=True)
    verg = [x for x in lijst if re.search(r'omgevingsvergunning|bouwvergunning|beschikking', x['titel'] + ' ' + x['soort'], re.I)
            and not re.search(r'verkeersbesluit|kapvergunning|watervergunning', x['titel'], re.I)]
    for x in verg[:60]:
        if x['_meta']:
            m = get(x['_meta'], timeout=30)
            if m and m.status_code == 200:
                z = re.findall(r'name="OVERHEIDop\.referentienummer"[^>]*content="([^"]+)"', m.text)
                if z: x['zaak'] = z[0]
    for x in lijst: x.pop('_meta', None)
    tek = [x for x in verg if TEKENING_SOORT.search(x['onderwerp'] + ' ' + x['activiteit'] + ' ' + x['titel']) and re.search(r'besluit|aanvraag', x['titel'], re.I)]
    plan = [x for x in lijst if re.search(r'bestemmingsplan|omgevingsplan|wijzigingsplan|projectbesluit|ruimtelijke onderbouwing|afwijken', x['titel'] + ' ' + x['soort'], re.I)]
    return {'n': len(lijst), 'gezocht': zoek, 'vergunningen': verg, 'met_tekeningen': [x['id'] for x in tek],
            'zaaknummers': sorted({x['zaak'] for x in tek if x.get('zaak')}), 'plannen': plan,
            'overig': [x for x in lijst if x not in verg and x not in plan][:30]}

_html = {}
_bezig = {}
def plan_html(u):
    with lock:
        if u in _html: return _html[u]
        ul = _bezig.setdefault(u, threading.Lock())
    with ul:  # niet twee threads tegelijk dezelfde pagina laten ophalen
        return _plan_html(u)

def _plan_html(u):
    with lock:
        if u in _html: return _html[u]
    fn = os.path.join(CACHE, 'html', hashlib.sha1(u.encode()).hexdigest()[:16] + '.html')
    if os.path.exists(fn):
        t = open(fn, encoding='utf-8').read()
    else:
        r = get(u, timeout=60)
        t = r.text if r is not None and r.status_code == 200 else ''
        if r is not None and r.status_code in (200, 404):
            os.makedirs(os.path.dirname(fn), exist_ok=True); open(fn, 'w', encoding='utf-8').write(t)
    with lock: _html[u] = t
    return t

def plan_pdfs(plan, ts):
    """PDF-bijlagen en figuren van een plan die over dit pand gaan."""
    docs, keuze, figuren, noemingen = plan['docs'], {}, [], []
    if not docs: return [], [], []
    base = docs[0].rsplit('/', 1)[0] + '/'
    pid = plan['id']
    todo = [d for d in docs if d.endswith('.html')] + [base + x for x in (f'b_{pid}_tb.html', f'b_{pid}_rb.html', f't_{pid}.html')]
    seen, alle_pdf, pat = set(), {}, '|'.join(re.escape(x) for x in ts)
    while todo and len(seen) < 90:
        u = todo.pop(0)
        if u in seen: continue
        seen.add(u)
        t = plan_html(u)
        if not t: continue
        for m in re.finditer(r'href="([^"#:]+\.html)"', t):
            if m.group(1).split('_')[0] in ('t', 'tb', 'b', 'bijlagen') and not m.group(1).endswith('_rb.html'): todo.append(base + m.group(1))
        for m in re.finditer(r'<a [^>]*href="([^"#]+\.pdf)"[^>]*>(.*?)</a>', t, re.S):
            alle_pdf.setdefault(base + m.group(1), re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', m.group(2)))).strip())
        if not pat or os.path.basename(u).split('_')[0] not in ('t', 'tb', 'b'): continue
        for m in re.finditer(pat, t, re.I):
            win = t[max(0, m.start() - 700): m.end() + 900]
            tekst = re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', t[max(0, m.start() - 300): m.end() + 400])))
            if len(noemingen) < 12: noemingen.append({'doc': u, 'tekst': tekst[:700]})
            for bm in re.finditer(r'[Bb]ijlage\s+(\d+)', re.sub(r'<[^>]+>', ' ', win)):
                keuze.setdefault(('bijlage', bm.group(1)), 'genoemd bij het adres: bijlage ' + bm.group(1))
            for hm in re.finditer(r'href="([^"#]+\.pdf)"', win):
                keuze.setdefault(base + hm.group(1), 'link bij het adres')
            for im in re.finditer(r'<img [^>]*src="([^"]+)"', win):
                figuren.append(base + im.group(1))
    # "bijlage 2" koppelen aan een PDF: via de titel ("Bijlage 2 ...", "2 ...") of de bestandsnaam (..._tb2.pdf)
    for k in [k for k in keuze if isinstance(k, tuple)]:
        n, w = k[1], keuze.pop(k)
        for u, titel in alle_pdf.items():
            if re.match(rf'^\s*(bijlage\s*)?{n}\b', titel, re.I) or re.search(rf'_tb_?{n}\.pdf$', u):
                keuze.setdefault(u, w)
    klein = plan['opp_m2'] <= KLEIN_PLAN
    for u in [u for u in keuze if '/vb_' in u or (THEMA.search(alle_pdf.get(u, '')) and not treffers(alle_pdf.get(u, ''), ts))]:
        keuze.pop(u)
    for u, titel in alle_pdf.items():
        if '/vb_' in u or (THEMA.search(titel) and not treffers(titel, ts)): continue
        if klein: keuze.setdefault(u, 'klein plan: alle bijlagen')
        elif treffers(titel, ts): keuze.setdefault(u, 'titel noemt het pand')
    return [{'url': u, 'titel': alle_pdf.get(u, ''), 'waarom': w} for u, w in keuze.items()], sorted(set(figuren))[:12], noemingen

def plannen(pt, ts):
    hits = [p for p in PLANS if p['opp_m2'] <= MAX_PLAN and p['bbox'][0] <= pt[0] <= p['bbox'][2] and p['bbox'][1] <= pt[1] <= p['bbox'][3]
            and any(pip(pt, r) for r in p['rings'])]
    hits.sort(key=lambda p: p['opp_m2'])
    out = []
    for p in hits[:25]:
        pdfs, fig, noem = plan_pdfs(p, ts)
        out.append({'id': p['id'], 'naam': p['naam'], 'type': p['type'], 'status': p['status'], 'datum': p['datum'], 'opp_m2': p['opp_m2'],
                    'pdfs': pdfs, 'figuren': fig, 'noemingen': noem})
    return out

def woo(ad, ts):
    if not ad: return []
    out = []
    for n in ad['nrs'][:1]:
        r = get('https://open.overheid.nl/overheid/openbaarmakingen/api/v0/zoek',
                params={'zoektekst': f'{ad["straat"]} {n} Amsterdam', 'start': 0, 'aantalResultaten': 50}, timeout=60)
        if not r or r.status_code != 200: continue
        for x in r.json().get('resultaten', []):
            d, hl = x['document'], re.sub(r'<[^>]+>', '', x.get('highlightedText') or '')
            if treffers(hl + ' ' + d.get('titel', ''), ts[:len(ad['nrs'])]):
                out.append({'titel': d.get('titel'), 'datum': d.get('openbaarmakingsdatum'), 'door': d.get('publisher'),
                            'url': d.get('weblocatie') or d.get('pid'), 'fragment': hl[:400]})
    return out

# ---------- PDF's doorzoeken ----------
def download(url):
    fn = os.path.join(CACHE, hashlib.sha1(url.encode()).hexdigest()[:16] + '.pdf')
    if os.path.exists(fn): return fn if os.path.getsize(fn) > 0 else None
    try:
        with sessie().get(url, timeout=120, stream=True) as r:
            if r.status_code != 200 or int(r.headers.get('content-length') or 0) > MAX_PDF:
                open(fn, 'wb').close(); return None
            with open(fn + '.part', 'wb') as f:
                n = 0
                for chunk in r.iter_content(1 << 16):
                    f.write(chunk); n += len(chunk)
                    if n > MAX_PDF: break
        if n > MAX_PDF: os.remove(fn + '.part'); open(fn, 'wb').close(); return None
        os.replace(fn + '.part', fn); return fn
    except Exception:
        open(fn, 'wb').close(); return None

def tekeningachtig(page):
    try:
        imgs = page.get_image_info()
        area = page.rect.width * page.rect.height
        img_cov = max((abs((i['bbox'][2] - i['bbox'][0]) * (i['bbox'][3] - i['bbox'][1])) for i in imgs), default=0) / area
    except Exception: img_cov = 0
    try: vec = len(page.get_cdrawings())
    except Exception: vec = 0
    return vec > 400 or img_cov > 0.45, vec, round(img_cov, 2)

def contactvel(v, path, n_pages, tag):
    """Scan zonder tekstlaag: miniaturen van alle pagina's op vellen van 20, met paginanummer, om te laten bekijken."""
    from PIL import Image, ImageDraw
    d = os.path.join(ROOT, 'data', 'sources', v['id'], 'sweep'); os.makedirs(d, exist_ok=True)
    doc, out, W, H = fitz.open(path), [], 300, 300
    for s0 in range(0, min(n_pages, 100), 20):
        vel = Image.new('RGB', (5 * W, 4 * H), 'white'); dr = ImageDraw.Draw(vel)
        for j, i in enumerate(range(s0, min(s0 + 20, n_pages))):
            pg = doc[i]; z = (W - 10) / max(pg.rect.width, pg.rect.height)
            pm = pg.get_pixmap(matrix=fitz.Matrix(z, z), alpha=False)
            im = Image.frombytes('RGB', (pm.w, pm.h), pm.samples)
            x, y = (j % 5) * W + 5, (j // 5) * H + 5
            vel.paste(im, (x, y)); dr.rectangle([x, y, x + 34, y + 16], fill='black'); dr.text((x + 3, y + 2), str(i + 1), fill='white')
        fn = os.path.join(d, f'vel-{tag}-{s0 + 1}.png'); vel.save(fn)
        out.append(os.path.relpath(fn, ROOT).replace('\\', '/'))
    return out

def scan_pdf(v, path, ts, bron, gericht):
    """Kandidaatpagina's met (waarschijnlijk) de indeling. Gericht = het document hoort bij dit adres."""
    try: doc = fitz.open(path)
    except Exception: return [], 0, []
    tc = path + '.tekst.json'
    if os.path.exists(tc):
        teksten = json.load(open(tc, encoding='utf-8'))
    else:
        teksten = [p.get_text() for p in doc]
        json.dump(teksten, open(tc, 'w', encoding='utf-8'), ensure_ascii=False)
    hits = [bool(treffers(t, ts)) for t in teksten]
    doc_hits = sum(hits)
    if sum(len(t) for t in teksten) < 80 * len(teksten):
        return [], doc_hits, (contactvel(v, path, len(teksten), os.path.basename(path)[:8]) if gericht else [])
    if not doc_hits and not gericht: return [], 0, []
    out = []
    for i, t in enumerate(teksten):
        dicht = any(hits[max(0, i - 1): i + 2])
        sterk = bool(STERK.search(t))
        if not (gericht or dicht): continue
        if not (sterk or gericht or hits[i]): continue
        teken, vec, cov = tekeningachtig(doc[i]) if (sterk or len(t) < 1500) else (False, 0, 0)
        ind = INDELING.findall(t)
        score = 3 * hits[i] + dicht + 2 * gericht + 2 * sterk + min(len(ind), 4) * 0.5 + 2 * teken
        if (sterk and (teken or hits[i] or gericht)) or (teken and (hits[i] or gericht)):
            out.append({'bron': bron, 'pdf': path, 'pagina': i + 1, 'paginas': len(teksten), 'score': score, 'tekening': teken,
                        'vectoren': vec, 'beelddekking': cov, 'woorden': sorted(set(w.lower() for w in STERK.findall(t)))[:6],
                        'tekst': re.sub(r'\s+', ' ', t)[:300]})
    return out, doc_hits, []

def render(v, kand):
    d = os.path.join(ROOT, 'data', 'sources', v['id'], 'sweep'); os.makedirs(d, exist_ok=True)
    for k in kand:
        try:
            doc = fitz.open(k['pdf']); pg = doc[k['pagina'] - 1]
            zoom = min(2.0, 1600 / max(pg.rect.width, pg.rect.height))
            fn = os.path.join(d, f"{os.path.basename(k['pdf'])[:-4]}-p{k['pagina']}.png")
            pg.get_pixmap(matrix=fitz.Matrix(zoom, zoom)).save(fn)
            k['png'] = os.path.relpath(fn, ROOT).replace('\\', '/')
        except Exception as e:
            k['png_fout'] = str(e)[:100]

def run(vid):
    v = VENUES[vid]; t0 = time.time()
    ad = adres(v); ts = termen(v, ad)
    pand, (lat, lon) = pand_van(v)
    res = {'id': vid, 'naam': v['name'], 'adres': v.get('address'), 'termen': ts, 'pand': pand, 'status': v.get('status'),
           'huidig': {'basis': v.get('basis'), 'confidence': v.get('confidence'), 'zalen': len(v.get('rooms', []))}}
    tm = {}
    t1 = time.time(); res['bouwdossiers'] = bouwdossiers(pand); tm['bouwdossiers'] = round(time.time() - t1)
    res['pand_adressen'] = pand_adressen(pand)
    t1 = time.time(); res['bekendmakingen'] = bekendmakingen(ad, res['pand_adressen']); tm['bekendmakingen'] = round(time.time() - t1)
    t1 = time.time(); res['plannen'] = plannen(rd(lat, lon), ts) if lat else []; tm['plannen'] = round(time.time() - t1)
    t1 = time.time(); res['woo'] = woo(ad, ts); tm['woo'] = round(time.time() - t1)
    res['tijden'] = tm
    # documenten verzamelen en doorzoeken
    te_scannen = []
    for p in res['plannen']:
        te_scannen += [(x['url'], f"plan {p['id']} ({p['naam']}): {x['titel'] or x['url'].rsplit('/', 1)[1]} [{x['waarom']}]", True) for x in p['pdfs']]
    for x in res['bekendmakingen'].get('plannen', [])[:6]:
        te_scannen.append((f"https://zoek.officielebekendmakingen.nl/{x['id']}.pdf", f"bekendmaking {x['id']}: {x['titel']}", False))
    te_scannen += [(x['url'], f"woo: {x['titel']}", False) for x in res['woo'] if (x['url'] or '').lower().endswith('.pdf')][:6]
    kand, gescand, vellen = [], [], []
    for url, bron, gericht in te_scannen[:60]:
        path = download(url)
        if not path: gescand.append({'url': url, 'bron': bron, 'fout': 'niet te downloaden of te groot'}); continue
        k, hits, cv = scan_pdf(v, path, ts, bron, gericht)
        for x in k: x['url'] = url
        if cv: vellen.append({'bron': bron, 'url': url, 'pdf': os.path.relpath(path, ROOT).replace(os.sep, '/'), 'vellen': cv})
        kand += k; gescand.append({'url': url, 'bron': bron, 'noemingen': hits, 'kandidaten': len(k), 'scan_zonder_tekst': bool(cv)})
    kand.sort(key=lambda k: -k['score'])
    kand = kand[:MAX_KANDIDATEN]
    render(v, kand)
    res['gescand'] = gescand; res['kandidaten'] = kand; res['contactvellen'] = vellen
    res['figuren'] = [f for p in res['plannen'] for f in p['figuren']][:12]
    res['duur_s'] = round(time.time() - t0)
    json.dump(res, open(os.path.join(OUT, vid + '.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    bm = res['bekendmakingen']
    with lock:
        print(f"{vid:32s} pand={'ja' if pand else 'nee'} dossiers={res['bouwdossiers'].get('n', 0):3d} bekendm={bm.get('n', 0):3d} "
              f"zaken={len(bm.get('zaaknummers', [])):2d} plannen={len(res['plannen']):2d} pdfs={len(gescand):2d} kandidaten={len(kand):2d} vellen={len(vellen)} ({res['duur_s']}s)", flush=True)
    return res

def alleen_bekendmakingen(vid):
    """Bekendmakingen opnieuw ophalen op alle adressen van het pand; de rest van het resultaat blijft staan."""
    p = os.path.join(OUT, vid + '.json')
    res = json.load(open(p, encoding='utf-8'))
    res['pand_adressen'] = pand_adressen(res.get('pand'))
    res['bekendmakingen'] = bekendmakingen(adres(VENUES[vid]), res['pand_adressen'])
    json.dump(res, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f"{vid:32s} adressen={len(res['pand_adressen']):2d} bekendm={res['bekendmakingen'].get('n', 0):3d}", flush=True)

if __name__ == '__main__':
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    if '--bekendmakingen' in sys.argv:
        ids, fn = args or [i for i in VENUES if os.path.exists(os.path.join(OUT, i + '.json'))], alleen_bekendmakingen
    else:
        ids, fn = args or [i for i in VENUES if '--opnieuw' in sys.argv or not os.path.exists(os.path.join(OUT, i + '.json'))], run
    print('te doen:', len(ids), flush=True)
    with ProcessPoolExecutor(12) as ex:
        for f in [ex.submit(fn, i) for i in ids]:
            try: f.result()
            except Exception as e: print('FOUT', e, flush=True)
