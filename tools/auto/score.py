"""Meet de automatische reconstructie (data/auto/<id>/auto.json) tegen de officiële plattegrond (precisie-batch).

Gebruik: python -X utf8 tools/auto/score.py paradiso melkweg bitterzoet panama q-factory
Schrijft: data/auto/score.json en _shots/auto-vergelijk.png (links echt, rechts automatisch)

Vergelijking op de hoofdzaal (rooms[0]), schaalvrij: beide omtrekken worden in hun eigen bounding box
genormaliseerd (podium boven), daarna:
  vorm_iou      overlap van de genormaliseerde omtrek (0-1); ook gespiegeld gemeten
  verhouding    breedte/diepte echt vs automatisch
  podium        middelpunt podium/DJ binnen 0,2 (in een eenheidsvierkant) van het echte
  bars          aandeel echte bars met een automatische bar binnen 0,2 (recall) en omgekeerd (precisie)
  ingangen      aandeel echte doorgangen/ingangen met een automatische binnen 0,2
  balkon        heeft de echte zaal een balkon/vide, en de automatische ook?
"""
import sys, os, json, glob, math, asyncio
from PIL import Image, ImageDraw

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
THR = 0.2

def truth(vid):
    for f in sorted(glob.glob(os.path.join(ROOT, 'data', 'batches', 'precisie-*.json'))):
        for v in json.load(open(f, encoding='utf-8')):
            if v['id'] == vid: return v
def auto(vid):
    p = os.path.join(ROOT, 'data', 'auto', vid, 'auto.json')
    return json.load(open(p, encoding='utf-8'))[0] if os.path.exists(p) else None

def outline(room):
    if room.get('round'):
        c = room['round']; return [[c['cx'] + c['r'] * math.cos(a / 20 * math.pi), c['cy'] + c['r'] * math.sin(a / 20 * math.pi)] for a in range(40)]
    return room['outline']

def norm_fn(room):
    o = outline(room); xs = [p[0] for p in o]; ys = [p[1] for p in o]
    x0, y0, w, h = min(xs), min(ys), (max(xs) - min(xs)) or 1, (max(ys) - min(ys)) or 1
    return (lambda p: [(p[0] - x0) / w, (p[1] - y0) / h]), w / h

def raster(poly, n=120, mirror=False):
    pts = [((1 - x) if mirror else x, y) for x, y in poly]
    img = Image.new('1', (n, n), 0); ImageDraw.Draw(img).polygon([(x * (n - 1), y * (n - 1)) for x, y in pts], fill=1)
    return img

def iou(a, b):
    A = list(a.get_flattened_data()) if hasattr(a, 'get_flattened_data') else list(a.getdata())
    B = list(b.get_flattened_data()) if hasattr(b, 'get_flattened_data') else list(b.getdata())
    inter = sum(1 for x, y in zip(A, B) if x and y); uni = sum(1 for x, y in zip(A, B) if x or y)
    return inter / uni if uni else 0

def poly_area(p):
    return abs(sum(p[i][0] * p[i - 1][1] - p[i - 1][0] * p[i][1] for i in range(len(p)))) / 2

def shape_norm(poly):
    """Verhouding behouden: schaal naar oppervlakte 0,25 en zet het zwaartepunt op (0,5; 0,5)."""
    A = poly_area(poly) or 1; k = math.sqrt(0.25 / A)
    cx = sum(p[0] for p in poly) / len(poly); cy = sum(p[1] for p in poly) / len(poly)
    return [[0.5 + (p[0] - cx) * k, 0.5 + (p[1] - cy) * k] for p in poly]

def centers(room, N):
    st, bars, ins, balk = [], [], [], False
    for f in room.get('features', []):
        t = f.get('t')
        if t in ('dj', 'stage'): st.append((f['w'] * f['h'], N([f['x'] + f['w'] / 2, f['y'] + f['h'] / 2])))
        elif t == 'bar': bars.append(N([(f['a'][0] + f['b'][0]) / 2, (f['a'][1] + f['b'][1]) / 2]))
        elif t == 'in': ins.append(N([(f['a'][0] + f['b'][0]) / 2, (f['a'][1] + f['b'][1]) / 2]))
        txt = (f.get('text') or f.get('label') or '').lower()
        if any(k in txt for k in ('balkon', 'vide', 'balcon', 'balcony')): balk = True
    stage = max(st)[1] if st else None
    return stage, bars, ins, balk

def recall(truth_pts, pred_pts):
    if not truth_pts: return None
    return sum(1 for t in truth_pts if any(math.dist(t, p) <= THR for p in pred_pts)) / len(truth_pts)

def score(vid):
    T, A = truth(vid), auto(vid)
    if not A: return {'id': vid, 'fout': 'geen auto.json'}
    tr, ar = T['rooms'][0], A['rooms'][0]
    Nt, rt = norm_fn(tr); Na, ra = norm_fn(ar)
    to = [Nt(p) for p in outline(tr)]; ao = [Na(p) for p in outline(ar)]
    rT = raster(to); i0 = iou(rT, raster(ao)); i1 = iou(rT, raster(ao, mirror=True))
    sT = shape_norm(outline(tr)); sA = shape_norm(outline(ar))
    rS = raster(sT, 200); j0 = iou(rS, raster(sA, 200)); j1 = iou(rS, raster(sA, 200, mirror=True))
    ts, tb, ti, tbal = centers(tr, Nt); as_, ab, ai, abal = centers(ar, Na)
    podium = (ts is not None and as_ is not None and math.dist(ts, as_) <= THR)
    res = {'id': vid, 'naam': T['name'], 'echte_zaal': tr['name'], 'auto_zaal': ar['name'],
           'zalen_echt': len(T['rooms']), 'zalen_auto': len(A['rooms']),
           'vorm_iou': round(j0, 2), 'vorm_iou_gespiegeld': round(j1, 2), 'vorm_iou_uitgerekt': round(i0, 2),
           'verhouding_echt': round(rt, 2), 'verhouding_auto': round(ra, 2),
           'podium_goed': podium, 'podium_afstand': round(math.dist(ts, as_), 2) if ts and as_ else None,
           'bars_recall': recall(tb, ab), 'bars_precisie': recall(ab, tb), 'bars_echt': len(tb), 'bars_auto': len(ab),
           'ingangen_recall': recall(ti, ai), 'ingangen_echt': len(ti), 'ingangen_auto': len(ai),
           'balkon_echt': tbal, 'balkon_auto': abal}
    ok = [res['vorm_iou'] >= 0.7, podium, (res['bars_recall'] or 0) >= 0.5, (res['ingangen_recall'] or 0) >= 0.5]
    res['geloofwaardig'] = all(ok); res['criteria_gehaald'] = f'{sum(ok)}/4'
    return res

async def sheet(ids, rows):
    from playwright.async_api import async_playwright
    plan_js = open(os.path.join(ROOT, 'plan.js'), encoding='utf-8').read()
    tiles = []
    async with async_playwright() as p:
        b = await p.chromium.launch(); pg = await b.new_page(viewport={'width': 900, 'height': 1600})
        await pg.set_content('<div id="o"></div>'); await pg.add_script_tag(content=plan_js)
        for vid in ids:
            T, A = truth(vid), auto(vid)
            pair = []
            for v in (T, A):
                if not v: pair.append(None); continue
                svg = await pg.evaluate('([v, r]) => Plan.render(v, r, {noFooter: true})', [v, v['rooms'][0]])
                await pg.evaluate('s => document.getElementById("o").innerHTML = s', svg)
                path = os.path.join(ROOT, '_shots', f'_cmp_{vid}_{len(pair)}.png')
                await pg.locator('#o svg').screenshot(path=path); pair.append(path)
            tiles.append(pair)
        await b.close()
    w, h = 300, 533; pad = 30
    out = Image.new('RGB', (len(ids) * (2 * w + pad), h + 70), (18, 18, 18)); d = ImageDraw.Draw(out)
    for i, (vid, pair) in enumerate(zip(ids, tiles)):
        x = i * (2 * w + pad)
        for j, pth in enumerate(pair):
            if pth: out.paste(Image.open(pth).convert('RGB').resize((w - 6, h - 6)), (x + j * w + 3, 3))
        r = rows[i]
        d.text((x + 6, h + 6), f"{vid}: links echt, rechts automatisch", fill=(255, 255, 255))
        if 'vorm_iou' in r:
            d.text((x + 6, h + 24), f"vorm {r['vorm_iou']}  podium {'ja' if r['podium_goed'] else 'nee'}  bars {r['bars_recall']}  ingang {r['ingangen_recall']}", fill=(200, 200, 200))
            d.text((x + 6, h + 42), f"geloofwaardig: {'JA' if r['geloofwaardig'] else 'nee'} ({r['criteria_gehaald']})", fill=(120, 230, 140) if r['geloofwaardig'] else (255, 170, 80))
    out.save(os.path.join(ROOT, '_shots', 'auto-vergelijk.png'))

if __name__ == '__main__':
    ids = sys.argv[1:]
    rows = [score(v) for v in ids]
    json.dump(rows, open(os.path.join(ROOT, 'data', 'auto', 'score.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    for r in rows: print(json.dumps(r, ensure_ascii=False))
    asyncio.run(sheet(ids, rows))
