"""Contactsheets van alle zalen (60 per vel) naar _shots/sheet-N.png. Server moet draaien op :8765."""
import os, asyncio
from playwright.async_api import async_playwright
OUT = os.path.join(os.path.dirname(__file__), '..', '_shots'); os.makedirs(OUT, exist_ok=True)
N = 48
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(); pg = await b.new_page(viewport={'width': 1500, 'height': 1000})
        await pg.goto('http://localhost:8765/tools/sheet.html?from=0&n=1', wait_until='networkidle')
        total = await pg.evaluate('window.TOTAL')
        i = 0
        while i < total:
            await pg.goto(f'http://localhost:8765/tools/sheet.html?from={i}&n={N}', wait_until='networkidle')
            await pg.wait_for_timeout(300)
            await pg.screenshot(path=os.path.join(OUT, f'sheet-{i:03d}.png'), full_page=True)
            i += N
        await b.close(); print('zalen:', total)
asyncio.run(main())
