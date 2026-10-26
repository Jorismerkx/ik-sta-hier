"""Geometriehulp voor het overtrekken van zalen (meters).

    import sys; sys.path.insert(0, 'tools'); from geom import *
    fp = footprint('paradiso')                 # BAG-polygon in meters, noord boven (x oost, y zuid)
    poly = rotate(fp, 135)                     # draai met de klok mee in graden (podium naar boven)
    poly = simplify(poly, 0.6)                 # haal kleine knikjes < 0,6 m weg
    poly = normalize(poly)                     # schuif naar (0,0) linksboven, afgerond op 0,1 m
    print(dims(poly))                          # (breedte, diepte) in meters

Alle functies werken op lijsten [[x, y], ...]. Gebruik dezelfde rotate/normalize-parameters
voor features (bar, dj, ingang) als je ze in het noord-boven-assenstelsel hebt bepaald: zie transform().
"""
import json, math, os

ROOT = os.path.join(os.path.dirname(__file__), '..')

def footprint(vid, buren=False):
    d = json.load(open(os.path.join(ROOT, 'data', 'footprints', vid + '.json'), encoding='utf-8'))
    return d['buurpanden'] if buren else d['pand']['polygon_m']

def rotate(pts, deg, origin=(0, 0)):
    a = math.radians(deg); c, s = math.cos(a), math.sin(a); ox, oy = origin
    # y wijst naar beneden (zuid), dus dit is met de klok mee op het scherm
    return [[ox + (x - ox) * c - (y - oy) * s, oy + (x - ox) * s + (y - oy) * c] for x, y in pts]

def _dp(pts, eps):
    if len(pts) < 3: return pts
    (x1, y1), (x2, y2) = pts[0], pts[-1]
    L = math.hypot(x2 - x1, y2 - y1) or 1e-9
    dmax, idx = 0, 0
    for i in range(1, len(pts) - 1):
        d = abs((y2 - y1) * pts[i][0] - (x2 - x1) * pts[i][1] + x2 * y1 - y2 * x1) / L
        if d > dmax: dmax, idx = d, i
    if dmax > eps: return _dp(pts[:idx + 1], eps)[:-1] + _dp(pts[idx:], eps)
    return [pts[0], pts[-1]]

def simplify(poly, eps=0.5):
    """Douglas-Peucker op een gesloten ring (knip op het verste punt, vereenvoudig beide helften)."""
    poly = [list(q) for q in poly]
    if len(poly) > 1 and poly[0] == poly[-1]: poly = poly[:-1]
    if len(poly) < 4: return poly
    far = max(range(len(poly)), key=lambda i: math.hypot(poly[i][0] - poly[0][0], poly[i][1] - poly[0][1]))
    a = _dp(poly[:far + 1], eps); b = _dp(poly[far:] + [poly[0]], eps)
    out = a[:-1] + b[:-1]
    return out if len(out) >= 3 else poly

def bounds(pts):
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    return min(xs), min(ys), max(xs), max(ys)

def normalize(poly, ref=None, nd=1):
    """Schuif zodat linksboven op (0,0) ligt. ref = polygon waarvan de bounds gebruikt worden (standaard poly zelf)."""
    x0, y0, _, _ = bounds(ref or poly)
    return [[round(x - x0, nd), round(y - y0, nd)] for x, y in poly]

def dims(poly):
    x0, y0, x1, y1 = bounds(poly); return round(x1 - x0, 1), round(y1 - y0, 1)

def transform(pts, deg, ref_poly):
    """Draai punten (noord-boven-meters) net als de outline en schuif mee met de genormaliseerde outline."""
    r = rotate(pts, deg); rp = rotate(ref_poly, deg)
    x0, y0, _, _ = bounds(rp)
    return [[round(x - x0, 1), round(y - y0, 1)] for x, y in r]

def main_axis_deg(poly):
    """Hoek (graden) van de langste zijde t.o.v. de x-as; handig om een pand recht te zetten."""
    best, ang = 0, 0
    for i in range(len(poly)):
        (x1, y1), (x2, y2) = poly[i - 1], poly[i]
        L = math.hypot(x2 - x1, y2 - y1)
        if L > best: best, ang = L, math.degrees(math.atan2(y2 - y1, x2 - x1))
    return round(ang, 1)
