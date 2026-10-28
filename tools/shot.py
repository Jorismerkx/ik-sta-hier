"""Screenshots + rooktest van de app met Playwright. Gebruik: python tools/shot.py [out_dir]"""
import sys, os, asyncio
from playwright.async_api import async_playwright

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), '..', '_shots')
os.makedirs(OUT, exist_ok=True)
BASE = os.environ.get('ISH_BASE', 'http://localhost:8765/')
errors = []

async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        ctx = await b.new_context(viewport={'width': 1100, 'height': 950})
        pg = await ctx.new_page()
        pg.on('console', lambda m: errors.append(m.text) if m.type == 'error' else None)
        pg.on('pageerror', lambda e: errors.append(str(e)))
        await pg.goto(BASE, wait_until='networkidle')
        await pg.wait_for_timeout(800)
        await pg.screenshot(path=os.path.join(OUT, '0-welkom.png'))
        await pg.click('#ob-next'); await pg.wait_for_timeout(700)
        await pg.screenshot(path=os.path.join(OUT, '0b-welkom-2.png'))
        await pg.click('#ob-next'); await pg.wait_for_timeout(700)
        await pg.screenshot(path=os.path.join(OUT, '0c-welkom-3.png'))
        assert (await pg.text_content('#ob-next')).strip().lower() == 'begin', 'laatste slide'
        await pg.click('#ob-next')
        await pg.wait_for_timeout(400)
        await pg.screenshot(path=os.path.join(OUT, '1-lijst.png'))
        # zoeken
        await pg.fill('#q', 'para'); await pg.wait_for_timeout(200)
        n = await pg.locator('#list .row').count(); assert n >= 1, 'zoeken faalt'
        await pg.click('#q-clear')
        # chips
        await pg.click('.chip[data-a="Noord"]'); await pg.wait_for_timeout(200)
        assert await pg.locator('#list .row').count() > 5, 'chip Noord faalt'
        await pg.click('.chip[data-a="Alle"]')
        # kaart
        await pg.click('.tab[data-tab="map"]')
        await pg.wait_for_timeout(2500)
        await pg.screenshot(path=os.path.join(OUT, '2-kaart.png'))
        mb = await pg.locator('#map').bounding_box()
        pins = await pg.locator('.pin').all()
        for pin in pins:
            bb = await pin.bounding_box()
            if bb and mb['x']+40 < bb['x'] < mb['x']+mb['width']-40 and mb['y']+60 < bb['y'] < mb['y']+mb['height']-120:
                await pin.click(force=True); break
        await pg.wait_for_timeout(500)
        assert await pg.locator('#map-card:not(.hidden)').count(), 'kaartkaartje niet open'
        await pg.screenshot(path=os.path.join(OUT, '2b-kaart-kaartje.png'))
        await pg.click('.tab[data-tab="list"]')
        # venue met meerdere zalen (Paradiso)
        await pg.fill('#q', 'paradiso'); await pg.wait_for_timeout(200)
        await pg.click('#list .row >> nth=0'); await pg.wait_for_timeout(500)
        assert await pg.locator('#view-venue.active').count(), 'venue-view niet open'
        await pg.screenshot(path=os.path.join(OUT, '3-venue.png'))
        await pg.click('#v-rooms .room-card >> nth=0'); await pg.wait_for_timeout(400)
        # puntje + pen
        card = await pg.locator('#plan-ink').bounding_box()
        await pg.mouse.click(card['x'] + card['width'] * 0.6, card['y'] + card['height'] * 0.55)
        await pg.click('.tool[data-tool="pen"]')
        x0, y0 = card['x'] + card['width'] * 0.3, card['y'] + card['height'] * 0.7
        await pg.mouse.move(x0, y0); await pg.mouse.down()
        for i in range(1, 20): await pg.mouse.move(x0 + i * 4, y0 - i * 3)
        await pg.mouse.up(); await pg.wait_for_timeout(300)
        await pg.screenshot(path=os.path.join(OUT, '4-plan.png'))
        async with pg.expect_download() as dl:
            await pg.click('#p-share')
        d = await dl.value
        await d.save_as(os.path.join(OUT, '5-gedeeld.png'))
        # terug, terug, over
        # favoriet via planscherm
        await pg.click('#p-fav'); await pg.wait_for_timeout(200)
        assert 'on' in (await pg.get_attribute('#p-fav', 'class')), 'ster niet goud'
        await pg.click('#view-plan .back'); await pg.wait_for_timeout(200)
        assert await pg.locator('#view-venue.active').count(), 'terug naar venue faalt'
        assert 'on' in (await pg.get_attribute('#v-fav', 'class')), 'ster venue niet goud'
        await pg.screenshot(path=os.path.join(OUT, '3b-venue-fav.png'))
        await pg.click('#view-venue .back'); await pg.wait_for_timeout(200)
        assert await pg.locator('#view-home.active').count(), 'terug naar home faalt'
        await pg.click('#q-clear'); await pg.wait_for_timeout(200)
        assert await pg.locator('#list .recent').count() >= 1, 'recent ontbreekt'
        await pg.click('.chip[data-a="Favorieten"]'); await pg.wait_for_timeout(200)
        assert await pg.locator('#list .row').count() == 1, 'favorietenlijst leeg'
        await pg.screenshot(path=os.path.join(OUT, '3c-favorieten.png'))
        await pg.click('.chip[data-a="Alle"]')
        await pg.click('#info'); await pg.wait_for_timeout(200)
        await pg.screenshot(path=os.path.join(OUT, '6-over.png'))
        # deep link
        await pg.goto('about:blank'); await pg.goto(BASE + '#melkweg/0', wait_until='networkidle'); await pg.wait_for_timeout(500)
        assert await pg.locator('#view-plan.active').count(), 'deeplink faalt'
        # service worker geregistreerd?
        sw = await pg.evaluate('navigator.serviceWorker.getRegistration().then(r => !!r)')
        print('service worker:', sw)
        # mobiel
        pm = await b.new_page(viewport={'width': 390, 'height': 844}, device_scale_factor=2, is_mobile=True, has_touch=True)
        await pm.goto(BASE, wait_until='networkidle'); await pm.wait_for_timeout(600)
        await pm.screenshot(path=os.path.join(OUT, '7-mobiel-welkom.png'))
        await pm.evaluate("localStorage.setItem('welcomed','true')"); await pm.reload(wait_until='networkidle'); await pm.wait_for_timeout(500)
        await pm.screenshot(path=os.path.join(OUT, '8-mobiel-lijst.png'))
        await pm.fill('#q', 'shelter'); await pm.wait_for_timeout(200); await pm.click('#list .row >> nth=0'); await pm.wait_for_timeout(400)
        await pm.screenshot(path=os.path.join(OUT, '9-mobiel-plan.png'))
        await b.close()
    print('console errors:', errors or 'geen')
    print('ok', OUT)

asyncio.run(main())
