"""End-to-end test van vrienden, events en de feed met drie gebruikers in aparte browsers.

Gebruik: python -X utf8 tools/social_test.py [out_dir]
Start zelf een verse server (node server/server.js) met een tijdelijke database op poort 8788.
Joris maakt een profiel, Jonas wordt vriend via de vriendlink, Joris maakt een event met Jonas,
Sanne doet mee via de WhatsApp-link, Jonas pingt, Joris stuurt zijn plek, Sanne stuurt zonder bereik.
"""
import sys, os, asyncio, subprocess, tempfile, time, urllib.request
from playwright.async_api import async_playwright

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, '_shots', 'social')
os.makedirs(OUT, exist_ok=True)
PORT = 8788
BASE = f'http://localhost:{PORT}/'
errors = []

def start_server():
    data = tempfile.mkdtemp(prefix='ish-test-')
    env = dict(os.environ, PORT=str(PORT), DATA_DIR=data)
    p = subprocess.Popen(['node', os.path.join(ROOT, 'server', 'server.js')], env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    for _ in range(50):
        try: urllib.request.urlopen(BASE + 'api/health', timeout=1); return p
        except Exception: time.sleep(0.2)
    p.kill(); raise SystemExit('server start niet')

async def user(b, name):
    ctx = await b.new_context(viewport={'width': 1100, 'height': 950})
    pg = await ctx.new_page()
    pg.on('console', lambda m: errors.append(f'{name}: {m.text}') if m.type == 'error' else None)
    pg.on('pageerror', lambda e: errors.append(f'{name}: {e}'))
    return ctx, pg

async def shot(pg, naam):
    await pg.wait_for_timeout(350)  # onderblad en toasts uitgeschoven
    await pg.screenshot(path=os.path.join(OUT, naam + '.png'))

async def profiel(pg, naam):
    await pg.wait_for_selector('#sheet.open #me-name', timeout=5000)
    await pg.fill('#me-name', naam)
    await pg.click('#sheet .name-form .cta')
    await pg.wait_for_timeout(500)

async def tik_op_plan(pg, fx=0.62, fy=0.58):
    await pg.wait_for_selector('#view-plan.active')
    await pg.wait_for_timeout(300)
    bb = await pg.locator('#plan-ink').bounding_box()
    await pg.mouse.click(bb['x'] + bb['width'] * fx, bb['y'] + bb['height'] * fy)

async def main():
    srv = start_server()
    try:
        async with async_playwright() as p:
            b = await p.chromium.launch()
            jctx, joris = await user(b, 'joris')
            nctx, jonas = await user(b, 'jonas')
            sctx, sanne = await user(b, 'sanne')

            # 1. Joris: welkom -> vrienden -> profiel
            await joris.goto(BASE, wait_until='networkidle')
            await shot(joris, '01-welkom')
            await joris.click('#start')
            await joris.click('.tab[data-tab="friends"]')
            await shot(joris, '02-vrienden-leeg')
            await joris.click('#friends [data-act="profiel"]')
            await profiel(joris, 'Joris')
            code = (await joris.locator('.me-code strong').inner_text()).strip()
            assert len(code) == 6, f'code {code!r}'
            await shot(joris, '03-vrienden-profiel')

            # 2. Jonas opent de vriendlink
            await jonas.goto(BASE + '#vriend/' + code, wait_until='networkidle')
            await profiel(jonas, 'Jonas')
            await jonas.wait_for_selector('#friends .row.friend', timeout=5000)
            assert 'Joris' in await jonas.locator('#friends').inner_text()
            await joris.wait_for_function("document.querySelector('#friends').innerText.includes('Jonas')", timeout=6000)
            await shot(joris, '04-vrienden-jonas')

            # 3. Joris maakt een event met Jonas
            await joris.click('.tab[data-tab="events"]')
            await joris.click('#events [data-act="new"]')
            await joris.wait_for_selector('#view-event-new.active')
            await joris.click('#ne-venue')
            await joris.fill('#vs-q', 'paradiso'); await joris.wait_for_timeout(200)
            await joris.click('.vs-list .row >> nth=0'); await joris.wait_for_timeout(300)
            await joris.click('#ne-friends .opt >> nth=0')
            await shot(joris, '05-nieuw-event')
            await joris.click('#ne-save')
            await joris.wait_for_selector('#view-event.active', timeout=5000)
            await joris.wait_for_selector('#sheet.open', timeout=3000)
            await shot(joris, '06-event-klaar-uitnodigen')
            await joris.click('#sheet [data-s="later"]'); await joris.wait_for_timeout(300)
            invite = await joris.evaluate("JSON.parse(localStorage.getItem('events'))[0].invite")

            # 4. Jonas krijgt het event live binnen
            await jonas.click('.tab[data-tab="events"]')
            await jonas.wait_for_selector('#events .ev-card', timeout=6000)
            await shot(jonas, '07-jonas-events')

            # 5. Sanne doet mee via de WhatsApp-link
            await sanne.goto(BASE + '#e/' + invite, wait_until='networkidle')
            await sanne.wait_for_selector('#sheet.open .invite', timeout=5000)
            await shot(sanne, '08-sanne-uitnodiging')
            await sanne.click('#sheet [data-s="join"]')
            await profiel(sanne, 'Sanne')
            await sanne.wait_for_selector('#view-event.active', timeout=6000)
            await joris.wait_for_function("document.querySelector('#e-members').innerText.includes('Sanne')", timeout=6000)

            # 6. Jonas: Waar zijn jullie? -> Joris krijgt het alarm
            await jonas.click('#events .ev-card >> nth=0')
            await jonas.wait_for_selector('#view-event.active')
            await jonas.click('#e-ping')
            await joris.wait_for_selector('#alert.show', timeout=6000)
            await joris.wait_for_timeout(400)
            await shot(joris, '09-joris-alarm')

            # 7. Joris: Stuur mijn plek -> zaal -> tik -> Stuur
            await joris.click('#alert .al-go')
            await joris.wait_for_timeout(600)
            if await joris.locator('#sheet.open .room-pick').count():
                await shot(joris, '10-joris-zaal-kiezen')
                await joris.click('#sheet .room-pick .room-card >> nth=0')
            await tik_op_plan(joris)
            await shot(joris, '11-joris-plan-stuur')
            await joris.click('#p-share')
            await joris.wait_for_selector('#view-event.active', timeout=5000)
            await joris.wait_for_selector('#e-feed .bubble.spot:not(.pending)', timeout=6000)
            await shot(joris, '12-joris-feed')

            # 8. Jonas ziet Joris' puntje en opent het
            await jonas.wait_for_selector('#e-feed .bubble.spot', timeout=6000)
            await shot(jonas, '13-jonas-feed')
            await jonas.click('#e-feed .bubble.spot >> nth=-1')
            await jonas.wait_for_selector('#view-plan.active')
            svg = await jonas.locator('#plan-svg').inner_html()
            assert 'Joris' in svg, 'naam van Joris niet op de kaart'
            await shot(jonas, '14-jonas-ziet-joris')

            # 9. Sanne: de grote knop
            await sanne.click('#view-event .back'); await sanne.wait_for_timeout(300)
            await sanne.click('#here'); await sanne.wait_for_selector('#sheet.open .here-sheet', timeout=3000)
            await shot(sanne, '15-sanne-grote-knop')
            await sanne.click('#sheet [data-s="ping"]')
            await joris.wait_for_function("document.querySelectorAll('#e-feed .bubble.ping').length >= 2", timeout=6000)

            # 10. Sanne zonder bereik: puntje wacht, gaat later vanzelf
            await sanne.wait_for_selector('#view-event.active', timeout=5000)
            await sctx.set_offline(True)
            await sanne.click('#e-pin'); await sanne.wait_for_timeout(500)
            if await sanne.locator('#sheet.open .room-pick').count():
                await sanne.click('#sheet .room-pick .room-card >> nth=0')
            await tik_op_plan(sanne, 0.4, 0.4)
            await sanne.click('#p-share'); await sanne.wait_for_timeout(600)
            assert await sanne.locator('#sheet.open a[href^="sms:"]').count(), 'sms-terugval ontbreekt'
            await shot(sanne, '16-sanne-geen-bereik')
            await sanne.click('#sheet .sheet-bg'); await sanne.wait_for_timeout(300)
            assert await sanne.locator('#e-feed .bubble.pending').count(), 'wachtend puntje niet zichtbaar'
            await sctx.set_offline(False)
            await joris.wait_for_function("[...document.querySelectorAll('#e-feed .bubble.spot')].some(b => b.innerText.includes('Sanne'))", timeout=20000)
            await sanne.wait_for_function("!document.querySelector('#e-feed .bubble.pending')", timeout=20000)
            await shot(joris, '17-joris-ziet-sanne')

            # 11. de tabbalk en de lijst met favorietenchip
            await joris.click('#view-event .back'); await joris.wait_for_timeout(300)
            await joris.click('.tab[data-tab="list"]'); await joris.wait_for_timeout(200)
            await shot(joris, '18-lijst-tabbalk')

            # mobiel formaat
            m = await b.new_context(viewport={'width': 390, 'height': 844}, device_scale_factor=2, is_mobile=True, has_touch=True)
            mp = await m.new_page()
            await mp.goto(BASE, wait_until='networkidle')
            await mp.evaluate("localStorage.setItem('welcomed','true')"); await mp.reload(wait_until='networkidle'); await mp.wait_for_timeout(500)
            await shot(mp, '19-mobiel-lijst')
            await mp.click('.tab[data-tab="events"]'); await mp.wait_for_timeout(300)
            await shot(mp, '20-mobiel-events-intro')
            await b.close()
    finally:
        srv.kill()
    print('console errors:', errors or 'geen')
    print('ok', OUT)

asyncio.run(main())
