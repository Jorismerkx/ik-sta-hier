"""Voegt alle data/batches/*.json (arrays van venue-objecten) samen tot data/venues.json.
Controleert elke zaal op geldige spec en meldt fouten. Gebruik: python tools/merge.py
"""
import json, glob, os, re, sys, unicodedata

ROOT = os.path.join(os.path.dirname(__file__), '..')
BATCHES = sorted(glob.glob(os.path.join(ROOT, 'data', 'batches', '*.json')))
OUT = os.path.join(ROOT, 'data', 'venues.json')
FEATS = {'dj', 'stage', 'bar', 'in', 'wc', 'smoke', 'stairs', 'cloak', 'pillar', 'line', 'poly', 'label', 'lift'}

def slug(s):
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z0-9]+', '-', s).strip('-')

def check_room(vn, r, errs):
    if not r.get('name'): errs.append(f'{vn}: zaal zonder naam')
    if not r.get('outline') and not r.get('round'): errs.append(f'{vn}/{r.get("name")}: geen outline/round')
    if r.get('outline') and len(r['outline']) < 3: errs.append(f'{vn}/{r.get("name")}: outline < 3 punten')
    for f in r.get('features', []):
        t = f.get('t')
        if t not in FEATS: errs.append(f'{vn}/{r.get("name")}: onbekende feature {t}')
        if t in ('dj', 'stage') and not all(k in f for k in ('x', 'y', 'w', 'h')): errs.append(f'{vn}/{r.get("name")}: {t} mist x/y/w/h')
        if t in ('bar', 'in', 'line') and not (f.get('a') and f.get('b')): errs.append(f'{vn}/{r.get("name")}: {t} mist a/b')
        if t == 'poly' and not f.get('pts'): errs.append(f'{vn}/{r.get("name")}: poly mist pts')
        if t in ('wc', 'smoke', 'stairs', 'cloak', 'pillar', 'label', 'lift') and not all(k in f for k in ('x', 'y')): errs.append(f'{vn}/{r.get("name")}: {t} mist x/y')

venues, seen, errs = {}, {}, []
for b in BATCHES:
    try:
        data = json.load(open(b, encoding='utf-8'))
    except Exception as e:
        errs.append(f'{os.path.basename(b)}: JSON-fout {e}'); continue
    for v in data:
        if not v.get('name'): errs.append(f'{os.path.basename(b)}: venue zonder naam'); continue
        # "Naam (toelichting)" of "Naam / Alias" -> korte naam + aka (zoekbaar)
        m = re.match(r'^(.*?)\s*(?:\((.*)\)|/\s*(.*))\s*$', v['name'])
        if m and m.group(1):
            aka = (m.group(2) or m.group(3) or '').strip(' ()')
            v['aka'] = (v.get('aka', '') + ' ' + aka).strip()
            v['name'] = m.group(1).strip()
        vid = v.get('id') or slug(v['name'])
        v['id'] = vid
        if not v.get('rooms'): errs.append(f'{v["name"]}: geen zalen'); continue
        for r in v['rooms']: check_room(v['name'], r, errs)
        if vid in venues:
            # precisie-batches (stap 1-2: BAG + echte plattegronden) winnen altijd;
            # verder wint de hoogste confidence, bij gelijk het latere bestand
            RANK = {'hoog': 3, 'middel': 2, 'laag': 1}
            old = venues[vid]
            is_prec = os.path.basename(b).startswith('precisie')
            if not is_prec and seen[vid].startswith('precisie'):
                continue
            if not is_prec and RANK.get(old.get('confidence'), 0) > RANK.get(v.get('confidence'), 0):
                print('dubbel:', vid, '(', os.path.basename(b), 'verliest van', seen[vid], ')'); continue
            print('dubbel:', vid, '(', seen[vid], '->', os.path.basename(b), ')')
        venues[vid] = v; seen[vid] = os.path.basename(b)

DEDUPE = os.path.join(ROOT, 'data', 'dedupe.json')
if os.path.exists(DEDUPE):
    dd = json.load(open(DEDUPE, encoding='utf-8'))
    for d in dd.get('drop', []): venues.pop(d, None)
    for k, n in dd.get('rename', {}).items():
        if k in venues:
            v = venues[k]; m = re.match(r'^(.*?)\s*\((.*)\)\s*$', n)
            v['name'] = m.group(1) if m else n
            if m: v['aka'] = (v.get('aka', '') + ' ' + m.group(2)).strip()

# selectie: eventlocaties en gesloten zaken gaan eruit, de rest krijgt een type (club, twijfel, bar, podium)
SEL = os.path.join(ROOT, 'data', 'selectie.json')
if os.path.exists(SEL):
    cat = json.load(open(SEL, encoding='utf-8'))['categorie']
    for vid in list(venues):
        c = cat.get(vid)
        if c is None: errs.append(f'{vid}: niet ingedeeld in data/selectie.json')
        elif c in ('eventlocatie', 'dicht'): venues.pop(vid)
        else: venues[vid]['type'] = c

GEO = os.path.join(ROOT, 'data', 'geo.json')
geo = json.load(open(GEO, encoding='utf-8')) if os.path.exists(GEO) else {}
for v in venues.values():
    if not isinstance(v.get('lat'), (int, float)) and v['id'] in geo:
        v['lat'], v['lng'] = geo[v['id']]['lat'], geo[v['id']]['lng']

for v in venues.values():
    v['photo'] = os.path.exists(os.path.join(ROOT, 'img', 'venues', v['id'] + '.jpg'))

seen_names = {}
for v in venues.values():
    k = re.sub(r'[^a-z0-9]', '', v['name'].lower())
    if k in seen_names: errs.append(f'dubbele naam: {v["name"]} ({seen_names[k]} en {v["id"]}) -> zet een id in data/dedupe.json')
    seen_names[k] = v['id']

out = sorted(venues.values(), key=lambda v: slug(v['name']))
json.dump(out, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
rooms = sum(len(v['rooms']) for v in out)
geo = sum(1 for v in out if isinstance(v.get('lat'), (int, float)))
print(f'venues: {len(out)}  zalen: {rooms}  met coördinaten: {geo}  batches: {len(BATCHES)}')
if errs:
    print('FOUTEN:'); [print(' -', e) for e in errs]
    sys.exit(1)

# service-worker versie: hash over data + schil, zodat de app na elke wijziging ververst
import hashlib
h = hashlib.md5()
for f in ['data/venues.json', 'index.html', 'style.css', 'config.js', 'app.js', 'plan.js', 'qr.js', 'social.js', 'demo.js']:
    h.update(open(os.path.join(ROOT, f), 'rb').read())
swp = os.path.join(ROOT, 'sw.js'); sw = open(swp, encoding='utf-8').read()
sw = re.sub(r"const VERSION = '[^']*';", f"const VERSION = 'ish-{h.hexdigest()[:10]}';", sw)
open(swp, 'w', encoding='utf-8').write(sw)
print('sw versie: ish-' + h.hexdigest()[:10])
