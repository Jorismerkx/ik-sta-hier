"""Automatische pijplijn, stap 1-3: verzamel openbare data per venue, zonder bestaande plattegronden.

Gebruik: python -X utf8 tools/auto/collect.py <id> [<id> ...] [--videos 8]
Schrijft naar data/auto/<id>/:
  context.json   gebouw (BAG + 3D BAG), units (BAG verblijfsobjecten), ingangen (OSM), straatbeelden, video's
  luchtfoto.png  luchtfoto met hoofdpand (rood) en OSM-ingangen (groen)
  hoogte.png     AHN-hoogtekaart (DSM 0,5 m) met hoofdpand; hoge hallen vallen op
  street/*.jpg   Panoramax-straatbeelden rond het pand (CC-BY-SA)
  frames/*.jpg   keyframes uit openbare video's (DJ-sets, aftermovies, tours)
"""
import sys, os, json, math, io, re, subprocess, glob, shutil, time
import requests
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import footprint as fpm  # noqa: E402

UA = {'User-Agent': 'ik-sta-hier/0.3 (prive onderzoek)', 'Accept': 'application/json'}
venues = fpm.venues

def kx(lat): return 111320 * math.cos(math.radians(lat))
KY = 110574

def m_xy(lat, lon, lat0, lon0):
    return [round((lon - lon0) * kx(lat0), 1), round(-(lat - lat0) * KY, 1)]

# ---------- gebouw ----------
def building(v, fp):
    lat, lon, src = fpm.locate(v)
    feats = fpm.panden(lat, lon)
    bag_id = fp['pand']['bag_id']
    main = next((f for f in feats if f['properties'].get('identificatie') == bag_id), None)
    if not main:
        main = next((f for f in feats if fpm.inside((lon, lat), fpm.ring(f))), feats[0])
    ring = fpm.ring(main)
    lat0 = sum(c[1] for c in ring) / len(ring); lon0 = sum(c[0] for c in ring) / len(ring)
    return ring, lat0, lon0, (lat, lon)

def bag3d(bag_id):
    try:
        d = requests.get(f'https://api.3dbag.nl/collections/pand/items/NL.IMBAG.Pand.{bag_id}', headers=UA, timeout=30).json()
        co = d['feature']['CityObjects']
        a = co.get(f'NL.IMBAG.Pand.{bag_id}', {}).get('attributes', {})
        keep = ['b3_dak_type', 'b3_h_maaiveld', 'b3_h_dak_min', 'b3_h_dak_50p', 'b3_h_dak_max', 'b3_h_nok', 'b3_opp_grond', 'b3_volume_lod22', 'b3_bouwlagen']
        return {k: (round(a[k], 2) if isinstance(a.get(k), float) else a.get(k)) for k in keep if k in a}
    except Exception as e:
        return {'fout': str(e)}

def units(lat, lon, bag_id, lat0, lon0, r=70):
    dlat = r / KY; dlon = r / kx(lat)
    url = ('https://service.pdok.nl/lv/bag/wfs/v2_0?service=WFS&version=2.0.0&request=GetFeature&typeNames=bag:verblijfsobject'
           f'&outputFormat=application/json&srsName=EPSG:4326&count=300&bbox={lat-dlat},{lon-dlon},{lat+dlat},{lon+dlon},EPSG:4326')
    out = []
    try:
        for f in requests.get(url, headers=UA, timeout=30).json().get('features', []):
            p = f['properties']
            if bag_id not in str(p.get('pandidentificatie', '')): continue
            c = f['geometry']['coordinates']
            out.append({'adres': f"{p.get('openbare_ruimte','')} {p.get('huisnummer','')}{p.get('huisletter') or ''}{('-' + str(p['toevoeging'])) if p.get('toevoeging') else ''}".strip(),
                        'gebruiksdoel': p.get('gebruiksdoel'), 'oppervlakte_m2': p.get('oppervlakte'),
                        'punt_m': m_xy(c[1], c[0], lat0, lon0)})
    except Exception as e:
        out.append({'fout': str(e)})
    return out

def osm(lat0, lon0, r=80):
    dlat = r / KY; dlon = r / kx(lat0)
    bb = f'{lat0-dlat},{lon0-dlon},{lat0+dlat},{lon0+dlon}'
    q = f'[out:json][timeout:25];(node["entrance"]({bb});nwr["amenity"~"nightclub|bar|pub"]({bb});nwr["indoor"]({bb}););out center tags;'
    els, err = None, None
    for url in ('https://overpass-api.de/api/interpreter', 'https://overpass.kumi.systems/api/interpreter', 'https://maps.mail.ru/osm/tools/overpass/api/interpreter'):
        try:
            els = requests.post(url, data={'data': q}, headers=UA, timeout=60).json().get('elements', []); break
        except Exception as e:
            err = e; time.sleep(3)
    if els is None: return [{'fout': str(err)}]
    out = []
    for e in els:
        la = e.get('lat') or e.get('center', {}).get('lat'); lo = e.get('lon') or e.get('center', {}).get('lon')
        if la is None: continue
        out.append({'type': e['type'], 'tags': e.get('tags', {}), 'punt_m': m_xy(la, lo, lat0, lon0)})
    return out

# ---------- beelden ----------
def wms_image(url, layer, lat0, lon0, r, px, fmt='image/png'):
    dlat = r / KY; dlon = r / kx(lat0)
    params = {'service': 'WMS', 'version': '1.3.0', 'request': 'GetMap', 'layers': layer, 'styles': '', 'crs': 'EPSG:4326',
              'bbox': f'{lat0-dlat},{lon0-dlon},{lat0+dlat},{lon0+dlon}', 'width': px, 'height': px, 'format': fmt}
    r_ = requests.get(url, params=params, headers={'User-Agent': UA['User-Agent']}, timeout=60)
    return Image.open(io.BytesIO(r_.content)).convert('RGB'), (lon0 - dlon, lat0 - dlat, lon0 + dlon, lat0 + dlat)

def overlay(im, bbox, ring, pts, path, px):
    d = ImageDraw.Draw(im)
    P = lambda lo, la: ((lo - bbox[0]) / (bbox[2] - bbox[0]) * px, (bbox[3] - la) / (bbox[3] - bbox[1]) * px)
    d.line([P(*c) for c in ring] + [P(*ring[0])], fill=(255, 40, 40), width=3)
    for la, lo in pts:
        x, y = P(lo, la); d.ellipse([x - 6, y - 6, x + 6, y + 6], outline=(0, 255, 90), width=3)
    s10 = 10 / (bbox[2] - bbox[0]) / kx((bbox[1] + bbox[3]) / 2) * px
    d.rectangle([15, px - 30, 15 + s10, px - 24], fill=(255, 255, 255)); d.text((15, px - 20), '10 m', fill=(255, 255, 255))
    d.text((px - 25, 10), 'N', fill=(255, 255, 255))
    im.save(path, quality=88)

def street(lat0, lon0, outdir, r=45, n=8):
    os.makedirs(outdir, exist_ok=True)
    dlat = r / KY; dlon = r / kx(lat0)
    res = []
    try:
        feats = requests.get('https://api.panoramax.xyz/api/search', params={'bbox': f'{lon0-dlon},{lat0-dlat},{lon0+dlon},{lat0+dlat}', 'limit': 60},
                             headers=UA, timeout=40).json().get('features', [])
    except Exception as e:
        return [{'fout': str(e)}]
    # spreid over posities: kies telkens het beeld dat het verst van de al gekozen beelden ligt
    pts = [(f, f['geometry']['coordinates']) for f in feats if f.get('assets', {}).get('sd')]
    chosen = []
    for f, c in sorted(pts, key=lambda fc: (fc[1][0] - lon0) ** 2 + (fc[1][1] - lat0) ** 2):
        if len(chosen) >= n: break
        if all(math.hypot((c[0] - cc[0]) * kx(lat0), (c[1] - cc[1]) * KY) > 6 for _, cc in chosen): chosen.append((f, c))
    for i, (f, c) in enumerate(chosen):
        try:
            img = requests.get(f['assets']['sd']['href'], headers={'User-Agent': UA['User-Agent']}, timeout=40).content
            p = os.path.join(outdir, f'street_{i:02d}.jpg'); open(p, 'wb').write(img)
            pr = f.get('properties', {})
            res.append({'bestand': os.path.basename(p), 'punt_m': m_xy(c[1], c[0], lat0, lon0), 'kijkrichting_graden': pr.get('view:azimuth'),
                        'panorama_360': (pr.get('pers:interior_orientation', {}) or {}).get('field_of_view') == 360, 'datum': pr.get('datetime'),
                        'licentie': 'CC-BY-SA-4.0 (Panoramax)'})
        except Exception as e:
            res.append({'fout': str(e)})
    return res

# ---------- video ----------
def norm(s): return re.sub(r'[^a-z0-9 ]', ' ', s.lower())

def yt_search(q, n=12):
    try:
        out = subprocess.run(['yt-dlp', f'ytsearch{n}:{q}', '--flat-playlist', '-J', '--no-warnings'], capture_output=True, text=True, timeout=120, encoding='utf-8')
        return json.loads(out.stdout).get('entries', []) or []
    except Exception:
        return []

def videos(v, outdir, maxv=8):
    name = v['name']; key = norm(name).split()
    key = [k for k in key if len(k) > 2 and k not in ('club', 'the', 'amsterdam', 'zaal')] or norm(name).split()
    queries = [f'{name} amsterdam dj set', f'{name} amsterdam boiler room', f'{name} amsterdam aftermovie', f'{name} amsterdam inside venue tour', f'{name} amsterdam crowd']
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(5) as ex: results = list(ex.map(yt_search, queries))
    seen, cands = set(), []
    for q, res in zip(queries, results):
        for e in res:
            if not e or e.get('id') in seen: continue
            seen.add(e['id']); t = norm(e.get('title') or '')
            d = e.get('duration') or 0
            if not any(k in t for k in key): continue
            if d and (d < 45 or d > 5 * 3600): continue
            cands.append({'id': e['id'], 'titel': e.get('title'), 'duur_s': d, 'kanaal': e.get('channel') or e.get('uploader'), 'query': q})
    picked = cands[:maxv]
    os.makedirs(outdir, exist_ok=True)
    tmp = os.path.join(outdir, '_tmp'); os.makedirs(tmp, exist_ok=True)
    for vi, c in enumerate(picked):
        d = c['duur_s'] or 300
        starts = [0.12, 0.38, 0.62, 0.86] if d > 240 else [0.2, 0.6]
        secs = []
        for s in starts:
            a = int(d * s); secs += ['--download-sections', f'*{a}-{a + 15}']
        cmd = ['yt-dlp', f'https://www.youtube.com/watch?v={c["id"]}', '-f', '231/230/135/134/229/18', '--no-warnings', '--quiet',
               '-o', os.path.join(tmp, f'v{vi:02d}_%(section_start)s.%(ext)s')] + secs
        try: subprocess.run(cmd, timeout=180)
        except Exception as e: c['fout'] = str(e)
        files = sorted(glob.glob(os.path.join(tmp, f'v{vi:02d}_*')))
        c['frames'] = []
        for fi, f in enumerate(files):
            pat = os.path.join(outdir, f'v{vi:02d}_s{fi}_%02d.jpg')
            subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-i', f, '-vf', "select='eq(n,12)+gt(scene,0.28)',scale=854:-2", '-vsync', 'vfr', '-frames:v', '3', pat])
            c['frames'] += sorted(os.path.basename(x) for x in glob.glob(os.path.join(outdir, f'v{vi:02d}_s{fi}_*.jpg')))
    shutil.rmtree(tmp, ignore_errors=True)
    return picked

# ---------- run ----------
def run(vid, maxv):
    v = venues[vid]; out = os.path.join(ROOT, 'data', 'auto', vid); os.makedirs(out, exist_ok=True)
    fp = json.load(open(os.path.join(ROOT, 'data', 'footprints', vid + '.json'), encoding='utf-8'))
    ring, lat0, lon0, (alat, alon) = building(v, fp)
    ctx = {'id': vid, 'naam': v['name'], 'adres': v.get('address'),
           'uitleg': 'Alle *_m coordinaten in meters rond het midden van het hoofdpand: x = oost, y = zuid (noord boven), zelfde stelsel als gebouw.polygon_m.',
           'gebouw': {**{k: fp['pand'][k] for k in ('bag_id', 'bouwjaar', 'gebruiksdoel', 'footprint_m2', 'breedte_m', 'diepte_m')},
                      'polygon_m': [m_xy(c[1], c[0], lat0, lon0) for c in ring], 'hoogtes_3dbag': bag3d(fp['pand']['bag_id'])},
           'adrespunt_m': m_xy(alat, alon, lat0, lon0),
           'units_bag': units(alat, alon, fp['pand']['bag_id'], lat0, lon0),
           'osm': osm(lat0, lon0)}
    ents = [(o['punt_m'][1] / -KY + lat0, o['punt_m'][0] / kx(lat0) + lon0) for o in ctx['osm'] if 'entrance' in o.get('tags', {})]
    try:
        im, bb = wms_image('https://service.pdok.nl/hwh/luchtfotorgb/wms/v1_0', 'Actueel_orthoHR', lat0, lon0, 55, 900)
        overlay(im, bb, ring, ents, os.path.join(out, 'luchtfoto.png'), 900)
        im, bb = wms_image('https://service.pdok.nl/rws/ahn/wms/v1_0', 'dsm_05m', lat0, lon0, 55, 900)
        overlay(im, bb, ring, ents, os.path.join(out, 'hoogte.png'), 900)
    except Exception as e:
        ctx['beeld_fout'] = str(e)
    ctx['straatbeelden'] = street(lat0, lon0, os.path.join(out, 'street'))
    ctx['videos'] = videos(v, os.path.join(out, 'frames'), maxv)
    json.dump(ctx, open(os.path.join(out, 'context.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    nf = sum(len(c.get('frames', [])) for c in ctx['videos'])
    print(f"ok {vid}: units {len(ctx['units_bag'])}, osm {len(ctx['osm'])}, straat {len(ctx['straatbeelden'])}, video's {len(ctx['videos'])}, frames {nf}")

if __name__ == '__main__':
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    maxv = int(sys.argv[sys.argv.index('--videos') + 1]) if '--videos' in sys.argv else 8
    args = [a for a in args if not a.isdigit()]
    for vid in args:
        try: run(vid, maxv)
        except Exception as e: print('FOUT', vid, repr(e))
