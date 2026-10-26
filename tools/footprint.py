"""Stap 1: echte pandomtrek per venue uit de BAG (PDOK), plus luchtfoto met omtrek.

Gebruik: python tools/footprint.py id1 id2 ...   (zonder ids: alle venues)
         python tools/footprint.py id@52.3712,4.8945  (eigen punt opgeven als het verkeerde pand gekozen is;
                                                       het pand dat dit punt bevat wordt het hoofdpand)
Schrijft per venue:
  data/footprints/<id>.json  - pand(en) uit de BAG: id, bouwjaar, oppervlakte, polygon in meters
                               (x naar oost, y naar zuid; noord = boven), plus buurpanden
  data/footprints/<id>.png   - luchtfoto (PDOK) met hoofdpand rood, buurpanden geel, schaalbalk, noordpijl
"""
import sys, os, json, math, io, time, urllib.parse
import requests
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.join(os.path.dirname(__file__), '..')
OUT = os.path.join(ROOT, 'data', 'footprints'); os.makedirs(OUT, exist_ok=True)
venues = {v['id']: v for v in json.load(open(os.path.join(ROOT, 'data', 'venues.json'), encoding='utf-8'))}
UA = {'User-Agent': 'ik-sta-hier/0.2 (prive project)'}

def locate(v):
    """Adrespunt via PDOK Locatieserver (ligt in het verblijfsobject), anders venue lat/lng."""
    addr = (v.get('address') or '').split(',')
    q = ' '.join(a.strip() for a in addr[:2]) if addr and addr[0] else ''
    if q:
        try:
            r = requests.get('https://api.pdok.nl/bzk/locatieserver/search/v3_1/free',
                             params={'q': q, 'fq': 'type:adres', 'rows': 1, 'fl': 'centroide_ll,weergavenaam'}, headers=UA, timeout=20).json()
            d = r['response']['docs']
            if d:
                lon, lat = map(float, d[0]['centroide_ll'].replace('POINT(', '').replace(')', '').split())
                return lat, lon, d[0]['weergavenaam']
        except Exception as e:
            print('  locatieserver fout', e)
    return v['lat'], v['lng'], 'venue-coordinaat'

def panden(lat, lon, r_m=60):
    dlat = r_m / 110574; dlon = r_m / (111320 * math.cos(math.radians(lat)))
    bbox = f'{lat-dlat},{lon-dlon},{lat+dlat},{lon+dlon},EPSG:4326'
    url = ('https://service.pdok.nl/lv/bag/wfs/v2_0?service=WFS&version=2.0.0&request=GetFeature&typeNames=bag:pand'
           f'&outputFormat=application/json&srsName=EPSG:4326&count=200&bbox={bbox}')
    return requests.get(url, headers=UA, timeout=30).json().get('features', [])

def ring(f):
    g = f['geometry']
    if g['type'] == 'Polygon': return g['coordinates'][0]
    if g['type'] == 'MultiPolygon': return max((p[0] for p in g['coordinates']), key=len)
    return []

def inside(pt, poly):
    x, y = pt; c = False
    for i in range(len(poly)):
        x1, y1 = poly[i]; x2, y2 = poly[i - 1]
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1 + 1e-15) + x1: c = not c
    return c

def to_m(poly, lat0, lon0):
    kx = 111320 * math.cos(math.radians(lat0)); ky = 110574
    return [[round((lo - lon0) * kx, 2), round(-(la - lat0) * ky, 2)] for lo, la in poly]

def area(p):
    return abs(sum(p[i][0] * p[i - 1][1] - p[i - 1][0] * p[i][1] for i in range(len(p)))) / 2

def aerial(lat, lon, main, others, path, r_m=70, px=900):
    dlat = r_m / 110574; dlon = r_m / (111320 * math.cos(math.radians(lat)))
    bbox = (lon - dlon, lat - dlat, lon + dlon, lat + dlat)
    params = {'service': 'WMS', 'version': '1.3.0', 'request': 'GetMap', 'layers': 'Actueel_orthoHR', 'styles': '',
              'crs': 'EPSG:4326', 'bbox': f'{bbox[1]},{bbox[0]},{bbox[3]},{bbox[2]}', 'width': px, 'height': px, 'format': 'image/png'}
    try:
        r = requests.get('https://service.pdok.nl/hwh/luchtfotorgb/wms/v1_0', params=params, headers=UA, timeout=40)
        im = Image.open(io.BytesIO(r.content)).convert('RGB')
    except Exception as e:
        print('  luchtfoto fout', e); im = Image.new('RGB', (px, px), (40, 40, 40))
    d = ImageDraw.Draw(im)
    P = lambda lo, la: ((lo - bbox[0]) / (bbox[2] - bbox[0]) * px, (bbox[3] - la) / (bbox[3] - bbox[1]) * px)
    for o in others:
        d.line([P(*c) for c in o] + [P(*o[0])], fill=(255, 220, 0), width=2)
    d.line([P(*c) for c in main] + [P(*main[0])], fill=(255, 40, 40), width=4)
    d.ellipse([P(lon, lat)[0] - 5, P(lon, lat)[1] - 5, P(lon, lat)[0] + 5, P(lon, lat)[1] + 5], fill=(0, 200, 255))
    # schaalbalk 20 m + noordpijl
    s20 = 20 / (2 * r_m) * px
    d.rectangle([20, px - 40, 20 + s20, px - 32], fill=(255, 255, 255)); d.text((20, px - 30), '20 m', fill=(255, 255, 255))
    d.polygon([(px - 40, 20), (px - 50, 50), (px - 30, 50)], fill=(255, 255, 255)); d.text((px - 44, 54), 'N', fill=(255, 255, 255))
    im.save(path, quality=85)

def run(arg):
    vid, _, pt = arg.partition('@')
    v = venues[vid]
    if pt:
        lat, lon = map(float, pt.split(',')); src = 'handmatig punt'
    else:
        lat, lon, src = locate(v)
    feats = panden(lat, lon)
    if not feats:
        print('GEEN panden', vid); return
    rings = [(f, ring(f)) for f in feats]
    main = next(((f, r) for f, r in rings if inside((lon, lat), r)), None)
    if not main:  # dichtstbijzijnde pand (centroid)
        main = min(rings, key=lambda fr: (sum(c[0] for c in fr[1]) / len(fr[1]) - lon) ** 2 + (sum(c[1] for c in fr[1]) / len(fr[1]) - lat) ** 2)
    mf, mr = main
    lat0 = sum(c[1] for c in mr) / len(mr); lon0 = sum(c[0] for c in mr) / len(mr)
    others = [(f, r) for f, r in rings if f is not mf]
    poly_m = to_m(mr, lat0, lon0)
    xs = [p[0] for p in poly_m]; ys = [p[1] for p in poly_m]
    out = {
        'id': vid, 'name': v['name'], 'address': v.get('address'), 'lookup': src,
        'pand': {'bag_id': mf['properties'].get('identificatie'), 'bouwjaar': mf['properties'].get('bouwjaar'),
                 'gebruiksdoel': mf['properties'].get('gebruiksdoel'), 'oppervlakte_vbo_m2': mf['properties'].get('oppervlakte_max'),
                 'footprint_m2': round(area(poly_m)), 'breedte_m': round(max(xs) - min(xs), 1), 'diepte_m': round(max(ys) - min(ys), 1),
                 'polygon_m': poly_m},
        'buurpanden': [{'bag_id': f['properties'].get('identificatie'), 'bouwjaar': f['properties'].get('bouwjaar'),
                        'gebruiksdoel': f['properties'].get('gebruiksdoel'), 'polygon_m': to_m(r, lat0, lon0)}
                       for f, r in others if r],
        'uitleg': 'Coordinaten in meters rond het midden van het hoofdpand. x = oost, y = zuid (noord is boven). '
                  'Footprint is de buitenomtrek van het hele pand op maaiveld, niet per se de zaal.'
    }
    json.dump(out, open(os.path.join(OUT, vid + '.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    aerial(lat, lon, mr, [r for _, r in others if r], os.path.join(OUT, vid + '.png'))
    print(f"ok  {vid:28} pand {out['pand']['bag_id']} {out['pand']['footprint_m2']} m2 {out['pand']['breedte_m']}x{out['pand']['diepte_m']} m  ({src})")

if __name__ == '__main__':
  ids = sys.argv[1:] or list(venues)
  for vid in ids:
    try: run(vid)
    except Exception as e: print('FOUT', vid, e)
    time.sleep(0.3)
