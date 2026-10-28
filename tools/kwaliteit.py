"""Overzicht per venue hoe goed de plattegrond is, per type (club, twijfel, bar, podium).
Gebruik: python tools/kwaliteit.py  ->  data/kwaliteit.md en data/kwaliteit.json
"""
import json, os, collections

ROOT = os.path.join(os.path.dirname(__file__), '..')
venues = json.load(open(os.path.join(ROOT, 'data', 'venues.json'), encoding='utf-8'))
sweep_p = os.path.join(ROOT, 'data', 'sweep', 'overzicht.json')
sweep = {s['id']: s for s in json.load(open(sweep_p, encoding='utf-8'))} if os.path.exists(sweep_p) else {}

TYPES = [('club', 'Clubs'), ('twijfel', 'Twijfel (eerst checken)'), ('bar', 'Bars met DJ'), ('podium', 'Podia')]
NIVEAU = ['echt', 'gemeten', 'geschat', 'oud']
UITLEG = {
    'echt': 'overgetrokken van een echte plattegrond, tekening of rider',
    'gemeten': 'buitenmuren uit de BAG en luchtfoto, binnenkant uit foto\'s en video',
    'geschat': 'nagelopen in de precisieronde, maar binnenkant grotendeels geschat',
    'oud': 'eerste ronde: vorm en indeling geschat uit beschrijvingen, nog niet nagemeten',
}
VERBETER = {
    'compleet': 'tekening is al gebruikt',
    'deels': 'tekening van een deel van het pand',
    'opvraagbaar': 'binnenvergunning met zaaknummer: tekening op te vragen bij de gemeente',
    'bouwdossier': 'alleen bouwdossier Stadsarchief (niet bruikbaar)',
    'niets': 'geen openbare stukken gevonden',
}

def niveau(v):
    b, c = v.get('basis'), v.get('confidence')
    if b == 'plattegrond' or (b is None and c == 'hoog'): return 'echt'
    if b == 'bag+fotos': return 'gemeten'
    if b == 'schatting': return 'geschat'
    return 'oud'

def oordeel(v):
    """goed = muren kloppen en DJ/bar/ingang staan goed; twijfel = muren kloppen, binnenkant onzeker."""
    n = niveau(v)
    if n == 'echt' or (n == 'gemeten' and v.get('confidence') in ('middel', 'hoog')): return 'goed'
    if n == 'gemeten': return 'twijfel'
    return 'niet goed'

rows = collections.defaultdict(list)
for v in venues:
    rows[v.get('type', '?')].append(v)

out = ['# Plattegrondkwaliteit per venue', '',
       f'{len(venues)} venues, {sum(len(v["rooms"]) for v in venues)} zalen. Eventlocaties en gesloten zaken staan niet meer in de app.', '',
       '| Niveau | Betekenis |', '|---|---|']
out += [f'| {n} | {UITLEG[n]} |' for n in NIVEAU]
out.append('')
tel = collections.Counter()
for t, kop in TYPES:
    vs = sorted(rows.get(t, []), key=lambda v: (NIVEAU.index(niveau(v)), v['name'].lower()))
    c = collections.Counter(niveau(v) for v in vs)
    tel.update({(t, n): c[n] for n in NIVEAU})
    out += [f'## {kop} ({len(vs)})', '', ' · '.join(f'{n} {c[n]}' for n in NIVEAU), '',
            '| Venue | Zalen | Oordeel | Niveau | Zekerheid | Openbare tekening |', '|---|---|---|---|---|---|']
    for v in vs:
        s = sweep.get(v['id'], {}).get('categorie')
        out.append(f'| {v["name"]} | {len(v["rooms"])} | {oordeel(v)} | {niveau(v)} | {v.get("confidence", "")} | {VERBETER.get(s, "nog niet gezocht")} |')
    out.append('')

open(os.path.join(ROOT, 'data', 'kwaliteit.md'), 'w', encoding='utf-8').write('\n'.join(out))
rij = lambda v: {'id': v['id'], 'naam': v['name'], 'type': v.get('type'), 'wijk': v.get('area'), 'zalen': [r['name'] for r in v['rooms']],
                 'oordeel': oordeel(v), 'niveau': niveau(v), 'zekerheid': v.get('confidence'),
                 'tekening': VERBETER.get(sweep.get(v['id'], {}).get('categorie'), 'nog niet gezocht'), 'bron': v.get('source', '')}
json.dump([rij(v) for v in venues], open(os.path.join(ROOT, 'data', 'kwaliteit.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
oo = collections.Counter((v.get('type'), oordeel(v)) for v in venues)
for t, kop in TYPES:
    print(f'{kop:26}', '  '.join(f'{o} {oo[(t, o)]:2}' for o in ('goed', 'twijfel', 'niet goed')))
for t, kop in TYPES:
    print(f'{kop:26}', '  '.join(f'{n} {tel[(t, n)]:2}' for n in NIVEAU))
print('-> data/kwaliteit.md, data/kwaliteit.json')
