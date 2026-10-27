"""Render één PDF-pagina scherp als PNG, eventueel een uitsnede, om een tekening te kunnen aflezen.

Gebruik: python -X utf8 tools/sweep/pagina.py <pdf> <pagina> <uit.png> [breedte_px=2400] [x0 y0 x1 y1 als fractie 0-1]
Voorbeeld: python -X utf8 tools/sweep/pagina.py data/sources/_sweep_cache/304fa027afb533bd.pdf 33 data/sources/x/p33.png 3000 0.1 0.2 0.7 0.8
"""
import sys, fitz

pdf, nr, out = sys.argv[1], int(sys.argv[2]), sys.argv[3]
px = int(sys.argv[4]) if len(sys.argv) > 4 else 2400
pg = fitz.open(pdf)[nr - 1]
r = pg.rect
if len(sys.argv) > 8:
    x0, y0, x1, y1 = map(float, sys.argv[5:9])
    r = fitz.Rect(r.x0 + x0 * r.width, r.y0 + y0 * r.height, r.x0 + x1 * r.width, r.y0 + y1 * r.height)
z = px / max(r.width, r.height)
pg.get_pixmap(matrix=fitz.Matrix(z, z), clip=r, alpha=False).save(out)
print(out, round(r.width * z), 'x', round(r.height * z))
