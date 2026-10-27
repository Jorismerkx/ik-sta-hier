"""Overzicht na de documentensweep: per venue hoe compleet de plattegrond is en wat er nog op te vragen valt.

Gebruik: python -X utf8 tools/sweep/overzicht.py
Leest:    data/venues.json, data/sweep/<id>.json, data/sweep/oordeel/<id>.json
Schrijft: data/sweep/overzicht.json en data/sweep/overzicht.md

Categorieën (de eerste die past):
  compleet     zaal getekend van een echte, actuele plattegrond of rider (confidence hoog)
  deels        echte plattegrond, maar ouder dan een verbouwing of niet alle zalen (basis plattegrond, middel)
  opvraagbaar  geen tekening online, wel een omgevingsvergunning voor de binnenkant met zaaknummer: de
               gemeente heeft de tekeningen en stuurt de stukken op verzoek per e-mail
  bouwdossier  alleen een openbaar bouwdossier (scans zelf te bekijken op bouwdossiers.amsterdam.nl)
  niets        niets gevonden
"""
import os, json, re, glob, collections

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
SW = os.path.join(ROOT, 'data', 'sweep')
# Vergunningen waarvoor plattegronden van de binnenkant worden ingediend
BINNEN = re.compile(r'indeling|intern|inpandig|inwendig|verbouw|brandcompartiment|brandveilig|vluchtweg|nooduitgang|nachtzaak|'
                    r'dancing|zaal|vergrot|uitbrei|renovat|binnenwerk|vloer|trap|entresol|kelder|verdieping|splitsen|samenvoegen|'
                    r'wijzigen van (het|de) (pand|gebouw|gebruik)', re.I)
BUITEN = re.compile(r'reclame|gevel|zonnepane|dakkapel|\bdak|kozijn|boom|kap\b|terras|luifel|scherm|kunstwerk|steiger|antenne|'
                    r'airco|warmtepomp|installatie|unit|vlag|bord|lichtbak|hekwerk|fietsen|container|fundering|ontheffing|'
                    r'slaapplaats|logies|woning|appartement|kantoor|verblijf|kademuur|evenement|tent', re.I)
# Alleen de eigen plaats: "straat + nummer" komt ook elders voor; de titel van een bekendmaking noemt de plaats
ELDERS = re.compile(r'Rx\.Mission|\bGU-|\bEHV-')

def plaats(v):
    m = re.search(r'\d{4}\s?[A-Z]{2}\s+([A-Za-z\- ]+?)\s*(\(|$)', v.get('address') or '')
    return m.group(1).strip() if m else 'Amsterdam'

def binnen_zaken(sw, stad='Amsterdam'):
    out = {}
    for x in (sw.get('bekendmakingen') or {}).get('vergunningen', []):
        o = (x.get('onderwerp') or '') + ' ' + (x.get('activiteit') or '')
        if ELDERS.search(' '.join(x.get(k) or '' for k in ('titel', 'zaak', 'onderwerp'))) or stad not in (x.get('titel') or ''): continue
        if x.get('zaak') and BINNEN.search(o) and not BUITEN.search(x.get('onderwerp') or ''):
            out.setdefault(x['zaak'], {'zaak': x['zaak'], 'onderwerp': x.get('onderwerp'), 'titel': x.get('titel'),
                                       'datum': x.get('datum'), 'url': x.get('url')})
    return sorted(out.values(), key=lambda z: z['datum'] or '', reverse=True)

def main():
    V = json.load(open(os.path.join(ROOT, 'data', 'venues.json'), encoding='utf-8'))
    rows = []
    for v in V:
        p = os.path.join(SW, v['id'] + '.json')
        sw = json.load(open(p, encoding='utf-8')) if os.path.exists(p) else {}
        op = os.path.join(SW, 'oordeel', v['id'] + '.json')
        oo = json.load(open(op, encoding='utf-8')) if os.path.exists(op) else None
        zaken = binnen_zaken(sw, plaats(v))
        bd = sw.get('bouwdossiers') or {}
        if v.get('confidence') == 'hoog': cat = 'compleet'
        elif v.get('basis') == 'plattegrond': cat = 'deels'
        elif zaken: cat = 'opvraagbaar'
        elif bd.get('openbaar'): cat = 'bouwdossier'
        else: cat = 'niets'
        rows.append({'id': v['id'], 'naam': v['name'], 'status': v.get('status'), 'categorie': cat,
                     'basis': v.get('basis'), 'confidence': v.get('confidence'),
                     'sweep_gevonden': bool(oo and oo.get('gevonden')), 'sweep_getekend': bool(oo and oo.get('getekend')),
                     'sweep_document': oo.get('document') if oo else None, 'sweep_jaar': oo.get('jaar') if oo else None,
                     'zaken_binnenkant': zaken[:6], 'bouwdossiers_openbaar': bd.get('openbaar', 0), 'bouwdossier_laatste': bd.get('laatste'),
                     'kandidaten': len(sw.get('kandidaten', [])), 'scans': len(sw.get('contactvellen', [])), 'gesweept': bool(sw)})
    json.dump(rows, open(os.path.join(SW, 'overzicht.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    c = collections.Counter(r['categorie'] for r in rows)
    lines = ['# Overzicht plattegronden na de documentensweep', '',
             f"{len(rows)} venues. " + ', '.join(f"{k}: {c[k]}" for k in ('compleet', 'deels', 'opvraagbaar', 'bouwdossier', 'niets')), '',
             '| venue | categorie | basis | nieuw uit sweep | zaaknummers binnenkant | openbare bouwdossiers |', '|---|---|---|---|---|---|']
    order = {k: i for i, k in enumerate(('compleet', 'deels', 'opvraagbaar', 'bouwdossier', 'niets'))}
    for r in sorted(rows, key=lambda r: (order[r['categorie']], r['naam'].lower())):
        lines.append(f"| {r['naam']} | {r['categorie']} | {r['basis'] or '-'} / {r['confidence']} | "
                     f"{('ja, ' + str(r['sweep_jaar'] or '')) if r['sweep_getekend'] else ('gevonden' if r['sweep_gevonden'] else '')} | "
                     f"{', '.join(z['zaak'] for z in r['zaken_binnenkant'][:3])} | {r['bouwdossiers_openbaar'] or ''} |")
    open(os.path.join(SW, 'overzicht.md'), 'w', encoding='utf-8').write('\n'.join(lines) + '\n')
    print(dict(c), '| nieuw getekend uit sweep:', sum(r['sweep_getekend'] for r in rows), '| niet gesweept:', sum(not r['gesweept'] for r in rows))

if __name__ == '__main__':
    main()
