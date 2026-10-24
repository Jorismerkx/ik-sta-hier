"""Geocodeert venues zonder lat/lng via Nominatim (1 request/sec) en schrijft ze naar data/geo.json
(keyed op venue-id). merge.py vult daaruit ontbrekende lat/lng aan.
Gebruik: python tools/geocode.py
"""
import json, time, os, urllib.parse, urllib.request

ROOT = os.path.join(os.path.dirname(__file__), '..')
GEO = os.path.join(ROOT, 'data', 'geo.json')
venues = json.load(open(os.path.join(ROOT, 'data', 'venues.json'), encoding='utf-8'))
geo = json.load(open(GEO, encoding='utf-8')) if os.path.exists(GEO) else {}
UA = 'ik-sta-hier/0.1 (lokale test, joris.merkx@agyle.nl)'

# Amsterdam + rand
BOX = (4.60, 52.20, 5.10, 52.50)  # lon_min, lat_min, lon_max, lat_max

def lookup(q):
    url = 'https://nominatim.openstreetmap.org/search?' + urllib.parse.urlencode({'q': q, 'format': 'json', 'limit': 1, 'countrycodes': 'nl'})
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=20) as r:
        data = json.load(r)
    if not data: return None
    lat, lon = float(data[0]['lat']), float(data[0]['lon'])
    if not (BOX[0] <= lon <= BOX[2] and BOX[1] <= lat <= BOX[3]): return None
    return (round(lat, 5), round(lon, 5))

done = 0
for v in venues:
    if isinstance(v.get('lat'), (int, float)) or v['id'] in geo:
        continue
    addr = (v.get('address') or '').strip()
    tries = []
    if addr:
        tries.append(addr if 'amsterdam' in addr.lower() or 'zaandam' in addr.lower() or 'halfweg' in addr.lower() or 'amstelveen' in addr.lower() else addr + ', Amsterdam')
        # zonder postcode (Nominatim struikelt soms over postcode + straat)
        tries.append(' '.join(p for p in addr.split(',')[0:1]) + ', Amsterdam')
    tries.append(f"{v['name']}, Amsterdam")
    hit = None
    for q in tries:
        try: hit = lookup(q)
        except Exception as e: print('fout', q, e); hit = None
        time.sleep(1.1)
        if hit: break
    if hit:
        geo[v['id']] = {'lat': hit[0], 'lng': hit[1], 'q': q}; done += 1
        print('ok  ', v['name'], hit)
    else:
        print('GEEN', v['name'], '|', addr)
    json.dump(geo, open(GEO, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

print('klaar, nieuw:', done, 'totaal in cache:', len(geo))
