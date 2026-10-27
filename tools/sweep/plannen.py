"""Bouw een index van alle Amsterdamse ruimtelijke plannen uit de PDOK-bulkdownload (INSPIRE, ruimtelijkeplannen.nl).

Gebruik: python -X utf8 tools/sweep/plannen.py <map met Bestemmingsplangebied.gml.gz en Plangebied.gml.gz>
Bron:    https://service.pdok.nl/kadaster/ruimtelijke-plannen/atom/plu.xml
Schrijft: data/sweep/plannen-0363.json  (per plan: id, naam, type, status, datum, oppervlakte m², RD-omtrek, documenten)
"""
import sys, os, gzip, json
from lxml import etree

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
G = '{http://www.opengis.net/gml}'

def rings(el):
    out = []
    for ext in el.iter(G + 'exterior'):
        pl = ext.find('.//' + G + 'posList')
        if pl is None or not pl.text: continue
        v = [float(x) for x in pl.text.split()]
        out.append([[round(v[i], 1), round(v[i + 1], 1)] for i in range(0, len(v) - 1, 2)])
    return out

def area(r):
    return abs(sum(r[i][0] * r[i - 1][1] - r[i - 1][0] * r[i][1] for i in range(len(r)))) / 2

def parse(path, tag, plans):
    for _, el in etree.iterparse(gzip.open(path), tag=G + tag, huge_tree=True):
        if el.findtext(G + 'overheidsCode') == '0363':
            pid = el.findtext(G + 'identificatie')
            rs = rings(el)
            docs = []
            for f in ('verwijzingNaarTekst', 'verwijzingNaarVaststellingsbesluit'):
                docs += [d.strip() for d in (el.findtext(G + f) or '').split(',') if d.strip().startswith('http')]
            p = plans.setdefault(pid, {'id': pid, 'naam': el.findtext(G + 'naam'), 'type': el.findtext(G + 'typePlan'),
                                       'status': el.findtext(G + 'planstatus'), 'datum': el.findtext(G + 'datum'),
                                       'dossierstatus': el.findtext(G + 'dossierStatus'), 'rings': rs,
                                       'opp_m2': round(sum(area(r) for r in rs)), 'docs': []})
            p['docs'] = sorted(set(p['docs']) | set(docs))
        el.clear()
        while el.getprevious() is not None: del el.getparent()[0]

if __name__ == '__main__':
    src = sys.argv[1]
    plans = {}
    for fn, tag in (('Bestemmingsplangebied.gml.gz', 'Bestemmingsplangebied'), ('Plangebied.gml.gz', 'Plangebied')):
        p = os.path.join(src, fn)
        if os.path.exists(p): parse(p, tag, plans); print(fn, len(plans))
    os.makedirs(os.path.join(ROOT, 'data', 'sweep'), exist_ok=True)
    json.dump(sorted(plans.values(), key=lambda p: p['id']), open(os.path.join(ROOT, 'data', 'sweep', 'plannen-0363.json'), 'w', encoding='utf-8'), ensure_ascii=False)
    print('plannen:', len(plans))
