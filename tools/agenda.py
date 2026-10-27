"""Agenda: komende feesten per club, uit de eigen website van de club (schema.org Event-data, zoals zoekmachines die lezen).

Gebruik: python -X utf8 tools/agenda.py            (alle venues met een website)
         python -X utf8 tools/agenda.py paradiso lofi
Schrijft: data/agenda.json  {venue_id: [{title, start, end, url}], ...}  (alleen de komende 90 dagen)

Werkwijze per club: homepage + agendapagina's lezen, daarna de losse feestpagina's (max. 40) waar de data vaak per
feest staat. Respecteert robots.txt. Clubs zonder gestructureerde data blijven leeg; dan kiest de gebruiker zelf
datum en tijd. TicketSwap en Resident Advisor hebben geen open API; die worden niet gescrapet.
"""
import sys, os, re, json, html, time, datetime as dt, urllib.parse, urllib.robotparser
from concurrent.futures import ThreadPoolExecutor
from zoneinfo import ZoneInfo
import requests

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
OUT = os.path.join(ROOT, 'data', 'agenda.json')
UA = 'ik-sta-hier/1.0 (+https://github.com/Jorismerkx/ik-sta-hier; agenda van clubs)'
AGENDA = re.compile(r'agenda|programma|program|events?|calendar|kalender|line-?up', re.I)
DETAIL = re.compile(r'/(programma|agenda|events?|event|evenementen|tickets?)/[^/?#]+', re.I)
MAX_DETAIL, DAGEN = 40, 90

def robots_ok(url, cache={}):
    base = '{0.scheme}://{0.netloc}'.format(urllib.parse.urlparse(url))
    if base not in cache:
        rp = urllib.robotparser.RobotFileParser()
        try:
            r = requests.get(base + '/robots.txt', headers={'User-Agent': UA}, timeout=10)
            rp.parse(r.text.splitlines() if r.status_code == 200 else [])
        except Exception: rp.parse([])
        cache[base] = rp
    return cache[base].can_fetch(UA, url)

def get(url):
    if not robots_ok(url): return None
    try:
        r = requests.get(url, headers={'User-Agent': UA}, timeout=20)
        return r.text if r.status_code == 200 and 'html' in r.headers.get('content-type', '') else None
    except Exception: return None

def events_in(page, base):
    out = []
    for blok in re.findall(r'<script[^>]+application/ld\+json[^>]*>(.*?)</script>', page, re.S):
        try: data = json.loads(blok.strip())
        except Exception: continue
        stack = [data]
        while stack:
            x = stack.pop()
            if isinstance(x, list): stack += x; continue
            if not isinstance(x, dict): continue
            t = x.get('@type'); t = t if isinstance(t, list) else [t]
            if any(str(s).endswith('Event') for s in t) and x.get('startDate') and x.get('name'):
                out.append({'title': html.unescape(str(x['name'])).strip()[:120], 'start': str(x['startDate'])[:40],
                            'end': str(x.get('endDate') or '')[:40] or None, 'url': urllib.parse.urljoin(base, str(x.get('url') or base))})
            stack += [v for k, v in x.items() if isinstance(v, (dict, list)) and k != 'location']
    return out

AMS = ZoneInfo('Europe/Amsterdam')
def when(s):
    """ISO-datum of -tijd naar Amsterdamse datum + tijd. Alleen een datum (zonder tijd) = geen tijd bekend."""
    try:
        if len(s) == 10: return dt.datetime.fromisoformat(s), False
        d = dt.datetime.fromisoformat(s.replace('Z', '+00:00'))
        return (d.astimezone(AMS).replace(tzinfo=None) if d.tzinfo else d), True
    except Exception: return None, False

def venue_agenda(v):
    site = v.get('website')
    if not site or not site.startswith('http'): return v['id'], []
    host = urllib.parse.urlparse(site).netloc.replace('www.', '')
    home = get(site)
    if not home: return v['id'], []
    found, pages, details = events_in(home, site), [], []
    for href in re.findall(r'href="([^"#]+)"', home):
        u = urllib.parse.urljoin(site, html.unescape(href))
        if urllib.parse.urlparse(u).netloc.replace('www.', '') != host: continue
        if DETAIL.search(urllib.parse.urlparse(u).path): details.append(u)
        elif AGENDA.search(urllib.parse.urlparse(u).path): pages.append(u)
    for u in list(dict.fromkeys(pages))[:3]:
        p = get(u)
        if not p: continue
        found += events_in(p, u)
        for href in re.findall(r'href="([^"#]+)"', p):
            d = urllib.parse.urljoin(u, html.unescape(href))
            if urllib.parse.urlparse(d).netloc.replace('www.', '') == host and DETAIL.search(urllib.parse.urlparse(d).path): details.append(d)
    if len(found) < 5:  # agenda staat niet in één keer op de pagina: losse feestpagina's lezen
        for u in list(dict.fromkeys(details))[:MAX_DETAIL]:
            p = get(u)
            if p: found += events_in(p, u)
            time.sleep(0.3)
    now, until = dt.datetime.now(), dt.datetime.now() + dt.timedelta(days=DAGEN)
    seen, out = set(), []
    for e in found:
        d, met_tijd = when(e['start'])
        if not d or not (now - dt.timedelta(hours=8) <= d <= until): continue
        key = (e['title'].lower(), d.date())
        if key in seen: continue
        seen.add(key)
        out.append({'title': e['title'], 'date': d.strftime('%Y-%m-%d'), 'time': d.strftime('%H:%M') if met_tijd else None, 'url': e['url']})
    return v['id'], sorted(out, key=lambda e: (e['date'], e['time'] or ''))

if __name__ == '__main__':
    venues = json.load(open(os.path.join(ROOT, 'data', 'venues.json'), encoding='utf-8'))
    ids = sys.argv[1:]
    todo = [v for v in venues if not ids or v['id'] in ids]
    agenda = json.load(open(OUT, encoding='utf-8')) if ids and os.path.exists(OUT) else {}
    with ThreadPoolExecutor(8) as ex:
        for vid, evs in ex.map(venue_agenda, todo):
            if evs: agenda[vid] = evs
            else: agenda.pop(vid, None)
            print(f'{vid:32s} {len(evs):3d}', flush=True)
    json.dump(dict(sorted(agenda.items())), open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    print('clubs met agenda:', len(agenda), '| feesten:', sum(len(v) for v in agenda.values()))
