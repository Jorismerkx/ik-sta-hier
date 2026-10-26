"""Render de zalen uit een batchbestand naar PNG, om de tekening naast de bron te leggen.

Gebruik: python tools/preview.py data/batches/precisie-01.json [venue-id ...]
Schrijft: _preview/<venue-id>-<zaalindex>.png  (900x1600, zelfde renderer als de app)
Lokale server hoeft niet te draaien.
"""
import sys, os, json, asyncio
from playwright.async_api import async_playwright

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
OUT = os.path.join(ROOT, '_preview'); os.makedirs(OUT, exist_ok=True)
batch = json.load(open(sys.argv[1], encoding='utf-8'))
only = set(sys.argv[2:])
plan_js = open(os.path.join(ROOT, 'plan.js'), encoding='utf-8').read()

async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await b.new_page(viewport={'width': 900, 'height': 1600})
        await pg.set_content('<html><body style="margin:0"><div id="o"></div></body></html>')
        await pg.add_script_tag(content=plan_js)
        for v in batch:
            vid = v.get('id')
            if only and vid not in only: continue
            for i, r in enumerate(v.get('rooms', [])):
                svg = await pg.evaluate('([v, r]) => Plan.render(v, r)', [v, r])
                await pg.evaluate('s => document.getElementById("o").innerHTML = s', svg)
                path = os.path.join(OUT, f'{vid}-{i}.png')
                await pg.locator('#o svg').screenshot(path=path)
                print(path)
        await b.close()

asyncio.run(main())
