"""Haalt per venue een profielfoto op van de eigen website (og:image / twitter:image / grootste img)
en bewaart hem verkleind als img/venues/<id>.jpg (800x800 center-crop, kwaliteit 82).
Handmatige overrides: data/photos.json  { "<id>": "https://...jpg" }  (wint altijd).
Gebruik: python tools/photos.py [--force] [id ...]
"""
import sys, os, re, json, io, html
import requests
from PIL import Image, ImageOps
from urllib.parse import urljoin

ROOT = os.path.join(os.path.dirname(__file__), '..')
OUT = os.path.join(ROOT, 'img', 'venues'); os.makedirs(OUT, exist_ok=True)
venues = json.load(open(os.path.join(ROOT, 'data', 'venues.json'), encoding='utf-8'))
OVR_PATH = os.path.join(ROOT, 'data', 'photos.json')
overrides = json.load(open(OVR_PATH, encoding='utf-8')) if os.path.exists(OVR_PATH) else {}
LOG = os.path.join(ROOT, 'data', 'photos-log.json')
log = json.load(open(LOG, encoding='utf-8')) if os.path.exists(LOG) else {}
force = '--force' in sys.argv
only = [a for a in sys.argv[1:] if not a.startswith('--')]
H = {'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
     'Accept': 'text/html,application/xhtml+xml,image/jpeg,image/png,image/webp;q=0.9,*/*;q=0.5', 'Accept-Language': 'nl,en;q=0.8'}
SIZE = 800

def find_image_urls(page_url):
    r = requests.get(page_url, headers=H, timeout=20, allow_redirects=True)
    r.raise_for_status()
    t = r.text
    cands = []
    for prop in ('og:image:secure_url', 'og:image', 'twitter:image', 'twitter:image:src'):
        for m in re.finditer(r'<meta[^>]+(?:property|name)=["\']%s["\'][^>]*>' % re.escape(prop), t, re.I):
            c = re.search(r'content=["\']([^"\']+)', m.group(0))
            if c: cands.append(html.unescape(c.group(1)))
    # link rel=image_src
    for m in re.finditer(r'<link[^>]+rel=["\']image_src["\'][^>]*href=["\']([^"\']+)', t, re.I): cands.append(m.group(1))
    # grote img's (src of data-src), geen svg/logo/icon
    for m in re.finditer(r'<img[^>]+(?:data-src|src)=["\']([^"\']+)', t, re.I):
        u = html.unescape(m.group(1))
        if re.search(r'\.(svg|gif)|logo|icon|sprite|pixel|tracking|avatar|flag|facebook\.com/tr|\.php\?', u, re.I): continue
        cands.append(u)
    seen, out = set(), []
    for c in cands:
        u = urljoin(r.url, c)
        if u.startswith('http') and u not in seen: seen.add(u); out.append(u)
    return out

def fetch_image(u):
    r = requests.get(u, headers=H, timeout=25)
    r.raise_for_status()
    im = Image.open(io.BytesIO(r.content)); im.load()
    return im

def save(im, path):
    im = ImageOps.exif_transpose(im).convert('RGB')
    im = ImageOps.fit(im, (SIZE, SIZE), Image.LANCZOS, centering=(0.5, 0.45))
    im.save(path, 'JPEG', quality=82, optimize=True, progressive=True)

ok = 0
for v in venues:
    vid = v['id']
    if only and vid not in only: continue
    dest = os.path.join(OUT, vid + '.jpg')
    if os.path.exists(dest) and not force and vid not in only: ok += 1; continue
    tried = []
    urls = []
    if vid in overrides: urls = [overrides[vid]]
    elif v.get('website'):
        try: urls = find_image_urls(v['website'])
        except Exception as e: tried.append(f'pagina: {e}')
    got = None
    for u in urls[:12]:
        try:
            im = fetch_image(u)
            if im.width < 400 or im.height < 300: tried.append(f'klein {im.width}x{im.height} {u}'); continue
            save(im, dest); got = u; break
        except Exception as e:
            tried.append(f'{u}: {e}')
    log[vid] = {'ok': bool(got), 'url': got, 'tried': tried[:6]}
    print(('ok   ' if got else 'GEEN ') + vid, got or (tried[0] if tried else 'geen website'))
    if got: ok += 1
    json.dump(log, open(LOG, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('foto', ok, 'van', len(venues))
