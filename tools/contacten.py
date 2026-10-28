"""Voegt data/contacten/groep-*.json samen tot de lijst voor de mailcampagne.
Gebruik: python tools/contacten.py
Schrijft (alles in data/contacten/, staat in .gitignore want het zijn persoonsgegevens):
  contacten.json  per venue: managers, adressen, telefoon, formulier, opmerking, plus type en plattegrondoordeel
  campagne.csv    één regel per mailadres, gesorteerd op prioriteit (puntkomma-gescheiden, opent zo in Excel)
"""
import json, glob, os, csv, re

ROOT = os.path.join(os.path.dirname(__file__), '..')
DIR = os.path.join(ROOT, 'data', 'contacten')
kw = {r['id']: r for r in json.load(open(os.path.join(ROOT, 'data', 'kwaliteit.json'), encoding='utf-8'))}

# bronnen die de agents ophaalden terwijl de site dat niet wilde (robots.txt, wachtrij, botcheck): adres eerst zelf nakijken
NAKIJKEN = {'paradiso.nl': 'paradiso.nl weert bots via robots.txt', 'muziekgebouw.nl': 'opgehaald langs de wachtrij van de site',
            'chicagosocialclub': 'site had een botcheck', 'bijlmerparktheater': 'opgehaald langs de wachtrij van de site',
            'frascatitheater': 'opgehaald langs de wachtrij van de site'}
NAKIJKEN_VENUE = {'de-meervaart': 'adres stond achter e-mailbescherming van Cloudflare',
                  'bar-benelux': 'adres stond achter e-mailbescherming van Cloudflare',
                  'lab111': 'adres stond achter e-mailbescherming van Cloudflare'}
# beste rol voor een plattegrondverzoek eerst
VOLGORDE = ['productie', 'management', 'verhuur/events', 'programmering', 'marketing/pers', 'algemeen', 'anders']

def prioriteit(v):
    k = kw.get(v['id'], {})
    if k.get('type') in ('club', 'twijfel'):
        return 1 if k.get('oordeel') != 'goed' else 2
    return 3

venues = []
for p in sorted(glob.glob(os.path.join(DIR, 'groep-*.json'))):
    venues += json.load(open(p, encoding='utf-8'))

rows, seen = [], set()
for v in venues:
    k = kw.get(v['id'], {})
    v['type'], v['oordeel'], v['prioriteit'] = k.get('type'), k.get('oordeel'), prioriteit(v)
    for e in v.get('emails', []):
        adres = e['adres'].strip().lower()
        if (v['id'], adres) in seen or not re.match(r'^[^@\s]+@[^@\s]+\.[a-z]{2,}$', adres): continue
        seen.add((v['id'], adres))
        let = '; '.join([t for d, t in NAKIJKEN.items() if d in (e.get('bron') or '')] + ([NAKIJKEN_VENUE[v['id']]] if v['id'] in NAKIJKEN_VENUE else []))
        rows.append({'prioriteit': v['prioriteit'], 'venue': v['naam'], 'type': v['type'], 'plattegrond': v['oordeel'],
                     'email': adres, 'voor': e.get('voor'), 'persoon': e.get('persoon') or '', 'bron': e.get('bron') or '',
                     'nakijken': let, 'telefoon': v.get('telefoon') or '', 'opmerking': v.get('opmerking') or ''})

rows.sort(key=lambda r: (r['prioriteit'], r['venue'].lower(), VOLGORDE.index(r['voor']) if r['voor'] in VOLGORDE else 99))
json.dump(sorted(venues, key=lambda v: (v['prioriteit'], v['naam'].lower())), open(os.path.join(DIR, 'contacten.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
with open(os.path.join(DIR, 'campagne.csv'), 'w', encoding='utf-8-sig', newline='') as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0]), delimiter=';'); w.writeheader(); w.writerows(rows)

n = lambda f: sum(1 for v in venues if f(len({e['adres'].lower() for e in v.get('emails', [])})))
print(f'venues {len(venues)}  adressen {len(rows)}  met managernaam {sum(1 for v in venues if v.get("managers"))}')
print(f'>=3 adressen {n(lambda x: x >= 3)}  1-2 {n(lambda x: 1 <= x <= 2)}  0 {n(lambda x: x == 0)}')
for p in (1, 2, 3):
    vs = [v for v in venues if v['prioriteit'] == p]
    print(f'prioriteit {p}: {len(vs)} venues, {sum(1 for r in rows if r["prioriteit"] == p)} adressen, zonder adres: {", ".join(v["naam"] for v in vs if not v.get("emails")) or "-"}')
print('nakijken:', sum(1 for r in rows if r['nakijken']), 'adressen')
missing = set(kw) - {v['id'] for v in venues}
if missing: print('nog geen contacten voor:', ', '.join(sorted(missing)))
