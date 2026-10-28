"""Screenshots van de schermen die social_test.py niet vastlegt: Mijn kaart, venuepagina met je event, onderbladen, mobiel.
Gebruik: python -X utf8 tools/v2_shots.py [out_dir]   (start zelf een server op poort 8789)
"""
import sys, os, asyncio, subprocess, tempfile, time, urllib.request
from playwright.async_api import async_playwright

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, '_shots', 'v2')
os.makedirs(OUT, exist_ok=True)
PORT = 8789
BASE = f'http://localhost:{PORT}/'
errors = []

def start_server():
    env = dict(os.environ, PORT=str(PORT), DATA_DIR=tempfile.mkdtemp(prefix='ish-v2-'))
    p = subprocess.Popen(['node', os.path.join(ROOT, 'server', 'server.js')], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    for _ in range(50):
        try: urllib.request.urlopen(BASE + 'api/health', timeout=1); return p
        except Exception: time.sleep(0.2)
    p.kill(); raise SystemExit('server start niet')

async def shot(pg, naam):
    await pg.wait_for_timeout(400)
    await pg.screenshot(path=os.path.join(OUT, naam + '.png'))

async def main():
    srv = start_server()
    try:
        async with async_playwright() as p:
            b = await p.chromium.launch()
            for label, vp, mob in (('desk', {'width': 1100, 'height': 950}, False), ('mob', {'width': 390, 'height': 844}, True)):
                ctx = await b.new_context(viewport=vp, device_scale_factor=2 if mob else 1, is_mobile=mob, has_touch=mob)
                pg = await ctx.new_page()
                pg.on('console', lambda m: errors.append(m.text) if m.type == 'error' else None)
                pg.on('pageerror', lambda e: errors.append(str(e)))
                await pg.goto(BASE, wait_until='networkidle')
                await pg.evaluate("localStorage.setItem('welcomed','true')")
                await pg.reload(wait_until='networkidle'); await pg.wait_for_timeout(500)
                # account via de vriendentab
                await pg.click('.tab[data-tab="friends"]')
                await pg.click('#friends [data-act="profiel"]')
                await pg.wait_for_selector('#sheet.open #me-form')
                await shot(pg, f'{label}-01-account')
                await pg.fill('#me-form [name="username"]', 'Joris' + label)
                await pg.fill('#me-form [name="password"]', 'geheim-123')
                await pg.click('#me-form .cta'); await pg.wait_for_timeout(700)
                await shot(pg, f'{label}-02-vrienden')
                await pg.click('#friends [data-act="card"]'); await pg.wait_for_selector('#view-card.active')
                await shot(pg, f'{label}-03-mijn-kaart')
                # event vanavond in Shelter, dan de venuepagina
                await pg.evaluate("""async () => {
                  const me = JSON.parse(localStorage.getItem('me'));
                  const d = new Date(); const p = n => String(n).padStart(2, '0');
                  await fetch('api/events', { method: 'POST', headers: { 'content-type': 'application/json', authorization: 'Bearer ' + me.token },
                    body: JSON.stringify({ venue: 'shelter', rooms: [], date: `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`, time: '23:00', title: 'Techno met de crew', friends: [] }) });
                }""")
                await pg.reload(wait_until='networkidle'); await pg.wait_for_timeout(800)
                await pg.evaluate("App.openVenue('shelter')"); await pg.wait_for_timeout(900)
                await shot(pg, f'{label}-04-venue-vanavond')
                await pg.evaluate("document.querySelector('#v-scroll').scrollTop = 600"); await pg.wait_for_timeout(200)
                await shot(pg, f'{label}-05-venue-programma')
                await pg.click('#view-venue .back'); await pg.wait_for_timeout(300)
                await pg.click('.tab[data-tab="events"]'); await pg.wait_for_timeout(500)
                await shot(pg, f'{label}-06-events')
                await pg.click('#here'); await pg.wait_for_selector('#sheet.open .here-sheet')
                await shot(pg, f'{label}-07-waar-sta-je')
                await pg.click('#sheet .sheet-bg'); await pg.wait_for_timeout(300)
                await pg.click('.tab[data-tab="list"]'); await pg.wait_for_timeout(300)
                await shot(pg, f'{label}-08-lijst-recent')
                await pg.click('#info'); await shot(pg, f'{label}-09-over')
                await ctx.close()
            await b.close()
    finally:
        srv.kill()
    print('console errors:', errors or 'geen')
    print('ok', OUT)

asyncio.run(main())
