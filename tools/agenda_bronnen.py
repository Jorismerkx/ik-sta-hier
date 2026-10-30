"""Bronnen voor tools/agenda.py: ophalen (robots.txt, crawl-delay), datums lezen en per platform één adapter.

Elke adapter geeft een lijst ruwe items: {'title', 'start' (naive datetime, Amsterdamse tijd), 'tijd' (bool: tijd bekend),
'url', 'loc' (locatienaam of None)}. agenda.py filtert daarna op periode, locatie en dubbelingen.

Alleen openbare, legitieme bronnen: de eigen site van de venue (JSON-LD, iCal, WordPress REST, Squarespace-JSON,
sitemaps, ingebedde JSON van Next/Nuxt/Astro/Vue, JSON-endpoints die de agendapagina zelf laadt, HTML-agenda) en open
agenda's/ticketshops waarvan robots.txt het toestaat. Resident Advisor en TicketSwap worden niet gelezen.

Adapters: jsonld, tribe, ics, radar, squarespace, sitemap, wp, embedded, jsonapi, kaartjes (generieke HTML-agenda),
rss/weticket, jsbundel, en maatwerk voor bitterzoet en paradiso. Let op tijdzones: sommige sites zetten een verkeerde
offset achter de tijd (Paradiso-JSON-LD: UTC met '+01:00'; Gashouder: lokaal met '+00:00'); kies dan een andere bron
of jsonld(klok=True).
"""
import re, json, html, time, threading, datetime as dt, urllib.parse
from html.parser import HTMLParser
from zoneinfo import ZoneInfo
import requests

UA = 'ik-sta-hier/1.0 (+https://github.com/Jorismerkx/ik-sta-hier; agenda van clubs)'
AMS = ZoneInfo('Europe/Amsterdam')
VERBODEN = re.compile(r'(^|\.)(ra\.co|residentadvisor\.net|ticketswap\.[a-z]+)$', re.I)  # geen open API, voorwaarden staan het niet toe


# ---------------------------------------------------------------- ophalen

class Robots:
    """robots.txt volgens RFC 9309: groepen per user-agent (onze eigen token, anders '*', gelijke groepen samengevoegd),
    wildcards '*' en '$', de langste regel wint. Bij een allow en disallow van gelijke lengte kiezen we voorzichtig
    voor disallow. 401/403 op robots.txt = niets ophalen."""
    TOKEN = 'ik-sta-hier'

    def __init__(self, text=None, alles_dicht=False):
        self.dicht, self.rules, self.crawl_delay = alles_dicht, [], None
        if not text: return
        groups, cur, agent_line = [], None, False
        lines = []
        for line in text.splitlines():  # ook robots.txt op één regel ('User-agent: * Disallow: /')
            lines += re.split(r'\s+(?=(?:user-agent|allow|disallow|crawl-delay|sitemap)\s*:)', line.split('#', 1)[0], flags=re.I)
        for line in lines:
            line = line.strip()
            if ':' not in line: continue
            k, v = (s.strip() for s in line.split(':', 1)); k = k.lower()
            if k == 'user-agent':
                if cur is None or not agent_line:
                    cur = {'agents': set(), 'rules': [], 'delay': None}; groups.append(cur)
                cur['agents'].add(v.lower()); agent_line = True; continue
            agent_line = False
            if cur is None: continue
            if k in ('allow', 'disallow') and v:
                cur['rules'].append((k == 'allow', v))
            elif k == 'crawl-delay':
                try: cur['delay'] = float(v)
                except ValueError: pass
        mine = [g for g in groups if any(a != '*' and self.TOKEN.startswith(a) for a in g['agents'])] or \
               [g for g in groups if '*' in g['agents']]
        for g in mine:
            self.rules += [(allow, len(p), re.compile(re.escape(p).replace(r'\*', '.*').replace(r'\$', '$') if p.endswith('$')
                                                      else re.escape(p).replace(r'\*', '.*'))) for allow, p in g['rules']]
            if g['delay'] is not None: self.crawl_delay = max(self.crawl_delay or 0, g['delay'])

    def ok(self, url):
        if self.dicht: return False
        p = urllib.parse.urlparse(url)
        path = (p.path or '/') + ('?' + p.query if p.query else '')
        best = None
        for allow, n, rx in self.rules:
            if rx.match(path) and (best is None or n > best[0] or (n == best[0] and not allow)):
                best = (n, allow)
        return True if best is None else best[1]


class Web:
    """Eén sessie per run: robots.txt per host (gecachet), crawl-delay per host, nette time-outs, nooit een exception."""

    def __init__(self, timeout=20):
        self.timeout = timeout
        self.s = requests.Session()
        self.s.headers['User-Agent'] = UA
        self.robots, self.last, self.lock = {}, {}, threading.Lock()
        self.host_locks, self.cache = {}, {}

    def _rp(self, url):
        p = urllib.parse.urlparse(url)
        base = f'{p.scheme}://{p.netloc}'
        with self.lock:
            if base in self.robots: return self.robots[base]
            self.robots[base] = None  # placeholder tegen dubbel ophalen
        try:
            r = self.s.get(base + '/robots.txt', timeout=10)
            rp = Robots(alles_dicht=True) if r.status_code in (401, 403) else Robots(r.text if r.status_code == 200 else None)
        except Exception:
            rp = Robots()
        with self.lock: self.robots[base] = rp
        return rp

    def _robots(self, url):
        for _ in range(300):
            rp = self._rp(url)
            if rp is not None: return rp
            time.sleep(0.05)
        return Robots(alles_dicht=True)

    def allowed(self, url):
        host = urllib.parse.urlparse(url).netloc.split(':')[0].lower()
        if VERBODEN.search(host): return False
        return self._robots(url).ok(url)

    def delay(self, url):
        return self._robots(url).crawl_delay or 0

    def _wait(self, url):
        """Crawl-delay uit robots.txt per host respecteren (minimaal 0,3 s tussen verzoeken naar dezelfde host)."""
        host = urllib.parse.urlparse(url).netloc
        delay = max(0.3, self.delay(url))
        with self.lock: hl = self.host_locks.setdefault(host, threading.Lock())
        with hl:
            wait = self.last.get(host, 0) + delay - time.time()
            if wait > 0: time.sleep(wait)
            self.last[host] = time.time()

    def get(self, url, params=None, accept=None):
        if not url or not url.startswith('http') or not self.allowed(url): return None
        self._wait(url)
        try:
            h = {'Accept': accept} if accept else {}
            r = self.s.get(url, params=params, timeout=self.timeout, headers=h)
            return r if r.status_code == 200 else None
        except Exception:
            return None

    def post(self, url, data):
        """POST zoals de site zelf doet (bijv. WordPress admin-ajax voor 'meer laden'); robots.txt geldt ook hier."""
        if not url or not url.startswith('http') or not self.allowed(url): return None
        self._wait(url)
        try:
            r = self.s.post(url, data=data, timeout=self.timeout)
            return r if r.status_code == 200 else None
        except Exception:
            return None

    def text(self, url, params=None):
        """Tekst van een pagina; per run gecachet (venues met dezelfde site halen een pagina maar één keer op)."""
        key = (url, json.dumps(params, sort_keys=True) if params else None)
        with self.lock:
            if key in self.cache: return self.cache[key]
        r = self.get(url, params)
        t = None
        if r is not None:
            if not r.encoding or r.encoding.lower() == 'iso-8859-1': r.encoding = r.apparent_encoding if 'html' not in (r.headers.get('content-type') or '') else 'utf-8'
            t = r.text
        with self.lock: self.cache[key] = t
        return t

    def json(self, url, params=None):
        r = self.get(url, params, accept='application/json')
        if r is None: return None
        try: return r.json()
        except Exception: return None


# ---------------------------------------------------------------- datums

MAANDEN = {'jan': 1, 'januari': 1, 'january': 1, 'feb': 2, 'februari': 2, 'february': 2, 'mrt': 3, 'maart': 3, 'mar': 3,
           'march': 3, 'maa': 3, 'apr': 4, 'april': 4, 'mei': 5, 'may': 5, 'jun': 6, 'juni': 6, 'june': 6, 'jul': 7,
           'juli': 7, 'july': 7, 'aug': 8, 'augustus': 8, 'august': 8, 'sep': 9, 'sept': 9, 'september': 9, 'okt': 10,
           'oct': 10, 'oktober': 10, 'october': 10, 'nov': 11, 'november': 11, 'dec': 12, 'december': 12}
_M = r'(jan(?:uari|uary)?|feb(?:ruari|ruary)?|mrt|maart|mar(?:ch)?|apr(?:il)?|mei|may|jun[ie]?|jul[iy]?|aug(?:ustus|ust)?|sep(?:t(?:ember)?)?|o[ck]t(?:ober)?|nov(?:ember)?|dec(?:ember)?)'
_D = r'(?:ma(?:andag)?|di(?:nsdag)?|wo(?:ensdag)?|do(?:nderdag)?|vr(?:ijdag)?|za(?:terdag)?|zo(?:ndag)?|mon(?:day)?|tue(?:s(?:day)?)?|wed(?:nesday)?|thu(?:r(?:s(?:day)?)?)?|fri(?:day)?|sat(?:urday)?|sun(?:day)?)'
RX_ISO = re.compile(r'(20\d\d)-(\d\d)-(\d\d)(?:[T ](\d\d):(\d\d))?')
RX_DMY = re.compile(r'(?<![\d.,€$])(\d{1,2})[-/.](\d{1,2})[-/.](20\d\d|\d\d)(?![\d])')
RX_DM_TXT = re.compile(r'(?<![\w])(\d{1,2})(?:e|ste|de|st|nd|rd|th)?\.?[\s.|-]*(?:of\s+)?' + _M + r'\.?(?![a-z])(?:[\s,.|-]*(20\d\d|\'\d\d))?', re.I)
RX_MD_TXT = re.compile(r'(?<![\w])' + _M + r'\.?\s+(\d{1,2})(?:st|nd|rd|th)?(?!\d)(?:,?\s+(20\d\d))?', re.I)
# weekdag + dag + maand, ook als de stukken in losse elementen staan: 'vr 30/10', 'FRI | 27 | .11', 'vr | 30 | 10'
RX_WD_DM = re.compile(r'(?<![\w])' + _D + r'\.?,?[\s|]+(\d{1,2})(?:[\s|]*[/.-][\s|]*|\s*\|\s*)(\d{1,2})(?![\d/.:-])', re.I)
RX_WD_DMY = re.compile(r'(?<![\w])' + _D + r'\.?[\s|,]+(\d{1,2})[\s|/.-]+(\d{1,2})[\s|/.-]+(20\d\d|\d\d)(?!\d)', re.I)
RX_REL = re.compile(r'(?<![\w])(vandaag|vanavond|today|tonight|morgen|tomorrow)(?![\w])', re.I)
RX_TIME = re.compile(r'(?<![\d.,€$:])([01]?\d|2[0-3])[:.]([0-5]\d)(?!\d)(?!\s*(?:euro|eur|€|,-))')
RX_TIME_U = re.compile(r'(?<![\d.,€$:])([01]?\d|2[0-3])\s?(?:u|uur|h)(?![a-z])', re.I)
RX_TIME_AMPM = re.compile(r'(?<![\d:])(1[0-2]|0?[1-9])(?::([0-5]\d))?\s?(am|pm)(?![a-z])', re.I)


def nu():
    return dt.datetime.now(AMS).replace(tzinfo=None)


def iso(s):
    """ISO-datum/-tijd (of epoch in s/ms) naar (naive Amsterdamse datetime, tijd_bekend)."""
    if s is None or s == '': return None, False
    try:
        if isinstance(s, (int, float)) or (isinstance(s, str) and re.fullmatch(r'\d{10}(\d{3})?', s.strip())):
            v = float(s); v = v / 1000 if v > 1e11 else v
            return dt.datetime.fromtimestamp(v, AMS).replace(tzinfo=None), True
        s = str(s).strip()
        if re.fullmatch(r'\d{8}', s): return dt.datetime.strptime(s, '%Y%m%d'), False
        if re.fullmatch(r'\d{4}-\d\d-\d\d', s): return dt.datetime.fromisoformat(s), False
        m = re.match(r'(\d{4}-\d\d-\d\d)[T ](\d\d:\d\d(?::\d\d)?)(\.\d+)?\s*(Z|[+-]\d\d:?\d\d)?', s)
        if not m: return None, False
        d = dt.datetime.fromisoformat(m.group(1) + 'T' + m.group(2))
        tz = m.group(4)
        if tz:
            tz = '+00:00' if tz == 'Z' else (tz if ':' in tz else tz[:3] + ':' + tz[3:])
            d = dt.datetime.fromisoformat(m.group(1) + 'T' + m.group(2) + tz).astimezone(AMS).replace(tzinfo=None)
        return d, True
    except Exception:
        return None, False


def _jaar(d, m, y, vandaag):
    try:
        if y:
            y = int(y.strip("'")); y = y + 2000 if y < 100 else y
            return dt.date(y, m, d)
        x = dt.date(vandaag.year, m, d)
        return x if x >= vandaag - dt.timedelta(days=60) else dt.date(vandaag.year + 1, m, d)
    except ValueError:
        return None


def datums(text, vandaag=None):
    """Alle datums in een stuk tekst (NL/EN), in volgorde van voorkomen: [(pos, date)]."""
    vandaag = vandaag or nu().date()
    out = []
    for m in RX_ISO.finditer(text):
        try: out.append((m.start(), dt.date(int(m[1]), int(m[2]), int(m[3]))))
        except ValueError: pass
    for m in RX_DMY.finditer(text):
        x = _jaar(int(m[1]), int(m[2]), m[3], vandaag) if 1 <= int(m[2]) <= 12 else None
        if x: out.append((m.start(), x))
    for m in RX_DM_TXT.finditer(text):
        x = _jaar(int(m[1]), MAANDEN[m[2].lower()[:3] if m[2].lower()[:3] in MAANDEN else m[2].lower()], m[3], vandaag)
        if x: out.append((m.start(), x))
    for m in RX_MD_TXT.finditer(text):
        k = m[1].lower(); k = k if k in MAANDEN else k[:3]
        x = _jaar(int(m[2]), MAANDEN[k], m[3], vandaag)
        if x and not any(abs(p - m.start()) < 12 for p, _ in out): out.append((m.start(), x))
    for m in RX_WD_DM.finditer(text):
        x = _jaar(int(m[1]), int(m[2]), None, vandaag) if 1 <= int(m[2]) <= 12 else None
        if x and not any(abs(p - m.start()) < 12 for p, _ in out): out.append((m.start(), x))
    for m in RX_WD_DMY.finditer(text):
        x = _jaar(int(m[1]), int(m[2]), m[3], vandaag) if 1 <= int(m[2]) <= 12 else None
        if x and not any(abs(p - m.start()) < 12 for p, _ in out): out.append((m.start(), x))
    for m in RX_REL.finditer(text):
        out.append((m.start(), vandaag + dt.timedelta(days=1 if m[1].lower() in ('morgen', 'tomorrow') else 0)))
    return sorted(out)


def tijd(text):
    """Eerste tijd (HH:MM) in een tekst, of None. '20.30' telt alleen als er geen €-bedrag omheen staat."""
    cands = []
    for m in RX_TIME.finditer(text):
        before = text[max(0, m.start() - 25):m.start()]
        if re.search(r'(€|eur|prijs|price|vanaf €)\s*$', before, re.I): continue
        if re.match(r'\s?[ap]\.?m\b', text[m.end():m.end() + 5], re.I): continue  # '7:30 pm': dat doet RX_TIME_AMPM
        if '.' in m.group(0):  # 20.30 alleen met context: 'uur', een tijdsbereik, aanvang/doors, of 'do 12 nov, 20.00'
            after = text[m.end():m.end() + 10]
            if not (re.match(r'\s*(uur|u\b|h\b|[-–]\s*\d|tot\b|till?\b|until\b)', after, re.I) or
                    re.search(r'(aanvang|deur|doors|start|open|tijd|time|vanaf|from|begin|zaal|\bom|\bat)\W*$', before, re.I) or
                    re.search(r'(\d{1,2}\s+[a-z]{3,9}\.?|vandaag|morgen|today|tomorrow|\d{1,2}[-/.]\d{1,2}(?:[-/.]\d{2,4})?)\s*,\s*$', before, re.I)):
                continue
        cands.append((m.start(), f'{int(m[1]):02d}:{m[2]}'))
    for m in RX_TIME_U.finditer(text): cands.append((m.start(), f'{int(m[1]):02d}:00'))
    for m in RX_TIME_AMPM.finditer(text):
        h = int(m[1]) % 12 + (12 if m[3].lower() == 'pm' else 0)
        cands.append((m.start(), f'{h:02d}:{m[2] or "00"}'))
    return min(cands)[1] if cands else None


_RX_KOP = re.compile(r'^\s*(?:' + _D + r'\.?,?\s+)?\d{1,2}\s*' + _M + r'\.?(?:\s+20\d\d)?\s*[|:–—-]\s+', re.I)
_RX_STAART = re.compile(r'[\s|,–-]+\d{1,2}[-/.]\d{1,2}[-/.](?:20)?\d\d\s*$')


def item(title, start, met_tijd, url, loc=None):
    title = re.sub(r'\s+', ' ', html.unescape(html.unescape(str(title or '')))).strip(' |-–·')
    kaal = _RX_STAART.sub('', _RX_KOP.sub('', title)).strip(' |-–·')  # '28 NOV | Jeff Mills', 'FEEST ZONDAG 01-11-2026'
    if kaal != title and _is_titel(kaal): title = kaal
    return {'title': title[:120], 'start': start, 'tijd': bool(met_tijd), 'url': url, 'loc': loc}


# ---------------------------------------------------------------- JSON-LD / microdata

def _ld_blocks(page):
    for blok in re.findall(r'<script[^>]+application/ld\+json[^>]*>(.*?)</script>', page, re.S | re.I):
        blok = blok.strip()
        try: yield json.loads(blok)
        except Exception:
            try: yield json.loads(re.sub(r'[\x00-\x1f]', ' ', blok))
            except Exception: continue


def _plaats(x):
    loc = x.get('location')
    if isinstance(loc, list): loc = loc[0] if loc else None
    if isinstance(loc, dict):
        parts = [loc.get('name') or '']
        a = loc.get('address')
        if isinstance(a, dict): parts.append(' '.join(str(a.get(k) or '') for k in ('streetAddress', 'addressLocality')))
        elif isinstance(a, str): parts.append(a)
        return ' '.join(p for p in parts if p).strip() or None
    return str(loc) if isinstance(loc, str) else None


def jsonld_events(page, base, klok=False):
    """schema.org Events in JSON-LD. klok=True: de site zet een verkeerde zone achter de tijd (lokale tijd met
    '+00:00', Gashouder); dan telt alleen de klokwijzer."""
    out = []
    for data in _ld_blocks(page):
        stack = [data]
        while stack:
            x = stack.pop()
            if isinstance(x, list): stack += x; continue
            if not isinstance(x, dict): continue
            t = x.get('@type'); t = t if isinstance(t, list) else [t]
            if any(str(s).endswith('Event') or s == 'Festival' for s in t) and x.get('startDate') and x.get('name'):
                sd = str(x['startDate'])
                d, met = iso(re.sub(r'(Z|[+-]\d\d:?\d\d)$', '', sd.strip()) if klok else sd)
                if d:
                    u = x.get('url') or x.get('@id') or base
                    u = u if isinstance(u, str) and not u.startswith('#') else base
                    out.append(item(x['name'], d, met, urllib.parse.urljoin(base, u), _plaats(x)))
            stack += [v for k, v in x.items() if isinstance(v, (dict, list)) and k not in ('location', 'performer', 'organizer', 'offers')]
    return out


AGENDA = re.compile(r'agenda|programma|program|events?|calendar|kalender|line-?up', re.I)
DETAIL = re.compile(r'/(programma|program|agenda|events?|evenement(?:en)?|event-details|tickets?|concerten|concert|voorstellingen?|shows?|activiteiten|feesten|parties|party|nights?)/[^/?#]+', re.I)


def _hrefs(page):
    """Alle hrefs, eerst ontsleuteld (Ticket Tailor schrijft '&#x2F;events&#x2F;...') en zonder #-deel."""
    for h in re.findall(r'href="([^"]+)"', page):
        h = html.unescape(h).split('#')[0]
        if h: yield h


def jsonld(web, v, urls=None, detail=None, max_detail=40, min_lijst=5, klok=False):
    """Huidige werkwijze, uitgebreid: homepage + agendapagina's lezen; staan daar te weinig items, dan de losse
    eventpagina's (max. max_detail) waar de data vaak per event staat."""
    site = v.get('website')
    urls = urls or [site]
    detail = re.compile(detail, re.I) if isinstance(detail, str) else (detail or DETAIL)
    host = urllib.parse.urlparse(urls[0]).netloc.replace('www.', '')
    found, pages, details = [], [], []
    for i, u in enumerate(urls):
        p = web.text(u)
        if not p: continue
        found += jsonld_events(p, u, klok)
        for href in _hrefs(p):
            x = urllib.parse.urljoin(u, href)
            pu = urllib.parse.urlparse(x)
            if pu.netloc.replace('www.', '') != host: continue
            if detail.search(pu.path): details.append(x)
            elif i == 0 and len(urls) == 1 and AGENDA.search(pu.path): pages.append(x)
    for u in list(dict.fromkeys(pages))[:3]:
        p = web.text(u)
        if not p: continue
        found += jsonld_events(p, u, klok)
        for href in _hrefs(p):
            x = urllib.parse.urljoin(u, href)
            if urllib.parse.urlparse(x).netloc.replace('www.', '') == host and detail.search(urllib.parse.urlparse(x).path): details.append(x)
    if len(found) < min_lijst:
        details = [d for d in dict.fromkeys(details) if d not in urls]
        if web.delay(details[0] if details else site) > 3: max_detail = min(max_detail, 10)
        for u in details[:max_detail]:
            p = web.text(u)
            if p: found += jsonld_events(p, u, klok)
    return found


# ---------------------------------------------------------------- WordPress: The Events Calendar

def tribe(web, base, params=None, max_pages=6):
    out, url = [], base.rstrip('/') + '/wp-json/tribe/events/v1/events'
    q = {'per_page': 50, 'start_date': nu().strftime('%Y-%m-%d 00:00:00'),
         'end_date': (nu() + dt.timedelta(days=95)).strftime('%Y-%m-%d 23:59:59')}
    q.update(params or {})
    for _ in range(max_pages):
        j = web.json(url, q)
        if not j: break
        for e in j.get('events') or []:
            d, met = iso(e.get('start_date'))
            if d and e.get('all_day') in (True, 'true', 'True'): met = False
            ven = e.get('venue') if isinstance(e.get('venue'), dict) else {}
            if d: out.append(item(e.get('title'), d, met, e.get('url'), ven.get('venue')))
        url, q = j.get('next_rest_url'), None
        if not url: break
    return out


# ---------------------------------------------------------------- iCal

def _ics_unfold(t):
    return re.sub(r'\r?\n[ \t]', '', t)


def ics(web, url):
    t = web.text(url)
    if not t or 'BEGIN:VEVENT' not in t: return []
    out = []
    for blok in _ics_unfold(t).split('BEGIN:VEVENT')[1:]:
        f = {}
        for line in blok.splitlines():
            m = re.match(r'([A-Z-]+)((?:;[^:]*)?):(.*)', line)
            if m and m[1] not in f: f[m[1]] = (m[2], m[3])
        if 'DTSTART' not in f or 'SUMMARY' not in f: continue
        prm, val = f['DTSTART']
        try:
            if 'VALUE=DATE' in prm or re.fullmatch(r'\d{8}', val):
                d, met = dt.datetime.strptime(val[:8], '%Y%m%d'), False
            elif val.endswith('Z'):
                d, met = dt.datetime.strptime(val, '%Y%m%dT%H%M%SZ').replace(tzinfo=dt.timezone.utc).astimezone(AMS).replace(tzinfo=None), True
            else:
                tz = re.search(r'TZID=([^;:]+)', prm)
                d = dt.datetime.strptime(val[:15], '%Y%m%dT%H%M%S')
                if tz and tz[1] != 'Europe/Amsterdam':
                    try: d = d.replace(tzinfo=ZoneInfo(tz[1])).astimezone(AMS).replace(tzinfo=None)
                    except Exception: pass
                met = True
        except Exception:
            continue
        unesc = lambda s: s.replace('\\,', ',').replace('\\;', ';').replace('\\n', ' ').replace('\\N', ' ').replace('\\\\', '\\')
        out.append(item(unesc(f['SUMMARY'][1]), d, met, (f.get('URL') or ('', url))[1] or url, unesc(f.get('LOCATION', ('', ''))[1]) or None))
    return out


# ---------------------------------------------------------------- Radar (radar.squat.net, open agenda van kraakpanden)

_radar_lock = threading.Lock()


def radar(web, group):
    """Open API van radar.squat.net. Crawl-delay (20 s) wordt door Web._wait per host bewaakt."""
    with _radar_lock:
        j = web.json('https://radar.squat.net/api/1.2/search/events.json',
                     {'facets[group][]': group, 'fields': 'title,date_time,url', 'limit': 50})
    out = []
    res = (j or {}).get('result') or {}
    for nid, e in (res.items() if isinstance(res, dict) else []):
        for t in e.get('date_time') or []:
            d, met = iso(t.get('time_start'))
            # de node-url werkt altijd; de nette padnamen bestaan niet voor elke taal of herhaling
            if d: out.append(item(e.get('title'), d, met, f'https://radar.squat.net/nl/node/{nid}' if str(nid).isdigit() else e.get('url')))
    return out


# ---------------------------------------------------------------- Squarespace (event-collectie als JSON)

def squarespace(web, url, max_pages=4):
    out, q = [], {'format': 'json'}
    base = '{0.scheme}://{0.netloc}'.format(urllib.parse.urlparse(url))
    for _ in range(max_pages):
        j = web.json(url, q)
        if not j: break
        for e in (j.get('upcoming') or []) + (j.get('items') or []):
            d, met = iso(e.get('startDate'))
            if d: out.append(item(e.get('title'), d, met, urllib.parse.urljoin(base, e.get('fullUrl') or '')))
        nxt = (j.get('pagination') or {}).get('nextPageUrl')
        if not nxt or not j.get('pagination', {}).get('nextPage'): break
        url, q = urllib.parse.urljoin(base, nxt), {'format': 'json'}
    return out


# ---------------------------------------------------------------- sitemap -> eventpagina's (JSON-LD)

def sitemap(web, url, pattern=None, max_detail=40, vers=120):
    """Eventpagina's uit een sitemap (bijv. Wix event-pages-sitemap.xml of een Yoast event-sitemap), de recentst
    gewijzigde eerst, en daarvan de JSON-LD. Pagina's die langer dan `vers` dagen niet gewijzigd zijn, slaan we over."""
    t = web.text(url)
    if not t: return []
    pat = re.compile(pattern, re.I) if pattern else None
    locs = []
    for blok in re.findall(r'<url>(.*?)</url>', t, re.S):
        loc = re.search(r'<loc>\s*([^<\s]+)', blok)
        lm = re.search(r'<lastmod>\s*([^<\s]+)', blok)
        if not loc or (pat and not pat.search(loc[1])): continue
        d = iso(lm[1])[0] if lm else None
        if d and d < nu() - dt.timedelta(days=vers): continue
        locs.append((d or dt.datetime.min, html.unescape(loc[1])))
    locs.sort(reverse=True)
    out = []
    for _, u in locs[:max_detail]:
        p = web.text(u)
        if p: out += jsonld_events(p, u)
    return out


# ---------------------------------------------------------------- WordPress REST (eigen posttypes)

def _pad(x, pad):
    for k in pad.split('.'):
        if isinstance(x, list): x = x[int(k)] if k.isdigit() and int(k) < len(x) else None
        elif isinstance(x, dict): x = x.get(k)
        else: return None
    return x


def wp(web, base, typ, start, tijd_veld=None, params=None, max_pages=5, loc=None, titel='title.rendered'):
    """/wp-json/wp/v2/<typ>: `start` is het pad naar het datumveld (bijv. 'acf.datum'), `tijd_veld` optioneel een
    apart tijdveld. Datumformaten: ISO, YYYYMMDD, dd-mm-yyyy, dd/mm/yyyy, epoch."""
    out, url = [], base.rstrip('/') + f'/wp-json/wp/v2/{typ}'
    q = {'per_page': 100, 'orderby': 'date', 'order': 'desc'}
    q.update(params or {})
    for page in range(1, max_pages + 1):
        q['page'] = page
        j = web.json(url, q)
        if not isinstance(j, list) or not j: break
        for e in j:
            raw = _pad(e, start)
            d, met = _vrije_datum(raw)
            if not d: continue
            if tijd_veld:
                tv = _pad(e, tijd_veld)
                tt = tijd(str(tv or ''))
                if tt: d, met = d.replace(hour=int(tt[:2]), minute=int(tt[3:])), True
            out.append(item(_pad(e, titel), d, met, e.get('link'), _pad(e, loc) if loc else None))
        if len(j) < q['per_page']: break
    return out


def _vrije_datum(raw):
    if raw is None or raw == '' or raw is False: return None, False
    if isinstance(raw, list): raw = raw[0] if raw else None
    if isinstance(raw, dict): raw = raw.get('date') or raw.get('value') or raw.get('start')
    s = str(raw).strip()
    d, met = iso(s)
    if d: return d, met
    m = re.fullmatch(r'(\d{1,2})[-/.](\d{1,2})[-/.](\d{4})(?:\s+(\d{1,2}):(\d\d))?', s)
    if m:
        try:
            d = dt.datetime(int(m[3]), int(m[2]), int(m[1]), int(m[4] or 0), int(m[5] or 0))
            return d, bool(m[4])
        except ValueError: return None, False
    ds = datums(s)
    if ds:
        d = dt.datetime.combine(ds[0][1], dt.time())
        tt = tijd(s[ds[0][0]:])
        return (d.replace(hour=int(tt[:2]), minute=int(tt[3:])), True) if tt else (d, False)
    return None, False


# ---------------------------------------------------------------- ingebedde JSON (Next.js, Nuxt, andere app-data)

def _nuxt_devalue(arr):
    """Nuxt 3 payload (devalue): een platte lijst waarin objecten naar indexen verwijzen."""
    memo = {}

    def res(i, depth=0):
        if not isinstance(i, int) or i < 0 or i >= len(arr) or depth > 60: return None
        if i in memo: return memo[i]
        v = arr[i]
        if isinstance(v, dict):
            o = {}; memo[i] = o
            for k, x in v.items(): o[k] = res(x, depth + 1)
            return o
        if isinstance(v, list):
            if v and isinstance(v[0], str) and v[0] in ('Reactive', 'ShallowReactive', 'Ref', 'ShallowRef', 'EmptyRef', 'NuxtError'):
                r = res(v[1], depth + 1) if len(v) > 1 else None; memo[i] = r; return r
            if v and v[0] == 'Date' and len(v) > 1: return v[1]
            if v and v[0] in ('Set', 'Map'): return [res(x, depth + 1) for x in v[1:]]
            o = []; memo[i] = o
            o.extend(res(x, depth + 1) for x in v)
            return o
        return v
    return res(0) if arr else None


def _flight_rijen(s):
    """Next.js app router (RSC): de stroom 'id:<json>\\n' rij voor rij. Een tekstrij 'id:T<hexlengte>,<tekst>' heeft
    geen regeleinde en wordt op lengte (in bytes) overgeslagen, anders plakt de volgende rij eraan vast."""
    b, i, n = s.encode('utf-8'), 0, len(s.encode('utf-8'))
    rx = re.compile(rb'([0-9a-zA-Z]+):')
    while i < n:
        m = rx.match(b, i)
        if not m:
            j = b.find(b'\n', i); i = n if j < 0 else j + 1; continue
        i = m.end()
        if b[i:i + 1] == b'T':
            k = b.find(b',', i)
            if k < 0: break
            try: i = k + 1 + int(b[i + 1:k], 16)
            except ValueError: i = k + 1
            continue
        j = b.find(b'\n', i); j = n if j < 0 else j
        yield b[i:j].decode('utf-8', 'replace'); i = j + 1


def _astro(v):
    """Astro-props: elke waarde is [type, waarde] (0 = gewoon, 1 = lijst, 3 = datum, ...)."""
    if isinstance(v, list) and len(v) == 2 and isinstance(v[0], int):
        k, x = v
        if k == 0: return {a: _astro(b) for a, b in x.items()} if isinstance(x, dict) else x
        if k == 1: return [_astro(y) for y in x] if isinstance(x, list) else x
        return x
    if isinstance(v, dict): return {a: _astro(b) for a, b in v.items()}
    return v


def ingebed(page):
    """Alle JSON in een pagina: __NEXT_DATA__, __NUXT_DATA__, andere <script type=application/json>, de Next.js
    RSC-stroom, props van Astro-eilanden en JSON in HTML-attributen (Vue-props als :all-items='[...]')."""
    out = []
    for m in re.finditer(r'<script([^>]*)>(.*?)</script>', page, re.S | re.I):
        attrs, body = m.group(1), m.group(2).strip()
        if 'application/json' in attrs or '__NEXT_DATA__' in attrs:
            try: j = json.loads(body)
            except Exception: continue
            if '__NUXT_DATA__' in attrs and isinstance(j, list): j = _nuxt_devalue(j)
            out.append(j)
    chunks = re.findall(r'self\.__next_f\.push\(\[1,"(.*?)"\]\)', page, re.S)
    if chunks:
        try:
            s = ''.join(json.loads('"' + c + '"') for c in chunks)
            for rij in _flight_rijen(s):
                if rij[:1] in '[{':
                    try: out.append(json.loads(rij))
                    except Exception: pass
        except Exception: pass
    for m in re.finditer(r'<astro-island\b[^>]*\bprops="([^"]*)"', page):
        try: out.append(_astro(json.loads(html.unescape(m[1]))))
        except Exception: pass
    for m in re.finditer(r'\s[:@]?[\w.-]+=(?:\'(\s*[\[{].*?)\'|"(\s*[\[{]&quot;.*?)")', page, re.S):
        s = html.unescape(m.group(1) or m.group(2))
        if len(s) < 40 or 'astro-island' in page[max(0, m.start() - 300):m.start()]: continue
        try: out.append(json.loads(s))
        except Exception: pass
    return out


TITEL_K = ('title', 'name', 'naam', 'titel', 'eventName', 'event_name', 'eventTitle', 'heading')
START_K = ('startDate', 'start_date', 'startsAt', 'starts_at', 'start', 'startTime', 'start_time', 'begin', 'beginDate',
           'eventDate', 'event_date', 'dateStart', 'date_start', 'startDateTime', 'start_datetime', 'datetime', 'dateFrom',
           'from', 'datum', 'aanvang', 'date', 'dateTime', 'performanceDate', 'showDate', 'eventStart', 'start_at')
URL_K = ('url', 'link', 'href', 'permalink', 'uri', 'fullUrl', 'path', 'slug')


def _get(x, k):
    """Sleutel of pad met punten ('content.startTime', 'data.name')."""
    if not k or not isinstance(x, dict): return None
    return _pad(x, k) if '.' in k else x.get(k)


def _tekstwaarde(t):
    if isinstance(t, dict): t = t.get('nl') or t.get('en') or t.get('rendered') or next((v for v in t.values() if isinstance(v, str)), None)
    return t if isinstance(t, str) and t.strip() else None


def json_events(data, base, titel=None, start=None, url_k=None, pad=None, tijdk=None, loc=None, vereist=None,
                kinderen=None, utc=False, alle_datums=False, uitsluit=None, ouder_url=False):
    """Zoekt in willekeurige JSON naar objecten met een titel en een startdatum.
    titel/start/url_k/tijdk/loc/vereist: vaste sleutel of pad met punten (anders de gangbare namen uit TITEL_K e.d.);
    pad: prefix voor een relatieve slug of id ('/programma/'); vereist: sleutel die gevuld moet zijn (sluit bijv.
    nieuwsitems uit); kinderen: pad naar een lijst voorstellingen/edities die de titel van de ouder erven (en met
    ouder_url=True ook de link: de voorstelling zelf heeft dan geen eigen pagina);
    utc: tijden zonder zone zijn UTC; alle_datums: een tekstveld met meerdere datums geeft één item per datum;
    uitsluit: {pad: regex}, objecten waarvan dat veld matcht vallen af (bijv. {'isCancelled': 'True'})."""
    tk = [titel] if titel else list(TITEL_K)
    sk = [start] if start else [k for k in START_K if k != 'date']
    uk = [url_k] if url_k else list(URL_K)
    out, seen, stack = [], set(), [data]

    def link(x, ouder=None):
        u = next((v for v in (_get(x, k) for k in uk) if isinstance(v, (str, int)) and not isinstance(v, bool) and str(v)), None)
        if u is None and ouder is not None: return link(ouder)
        if u is None: return base
        u = str(u)
        if pad and not u.startswith(('http', '/')): u = pad + u
        return urllib.parse.urljoin(base, u)

    def maak(x, t, ouder=None):
        s = next((v for v in (_get(x, k) for k in sk) if v not in (None, '', [], {})), None)
        if s is None: return
        if utc and isinstance(s, str) and re.fullmatch(r'\d{4}-\d\d-\d\d[T ]\d\d:\d\d(:\d\d(\.\d+)?)?', s.strip()): s = s.strip() + 'Z'
        if alle_datums and isinstance(s, str) and len(datums(s)) > 1:
            ds = [(dt.datetime.combine(d, dt.time()), False) for _, d in datums(s)]
        else:
            ds = [_vrije_datum(s) if not isinstance(s, (int, float)) else iso(s)]
        tv = _get(x, tijdk) if tijdk else None
        if tijdk and tv is None and ouder is not None: tv = _get(ouder, tijdk)
        tt = tijd(str(tv)) if tv else None
        lv = (_get(x, loc) or (_get(ouder, loc) if ouder is not None else None)) if loc else None
        for d, met in ds:
            if not d: continue
            if tt: d, met = d.replace(hour=int(tt[:2]), minute=int(tt[3:])), True
            out.append(item(t, d, met, link(ouder) if ouder_url and ouder is not None else link(x, ouder), str(lv) if lv is not None else None))

    while stack:
        x = stack.pop()
        if isinstance(x, list): stack += x; continue
        if not isinstance(x, dict) or id(x) in seen: continue
        seen.add(id(x))
        t = next((v for v in (_tekstwaarde(_get(x, k)) for k in tk) if v), None)
        if t and uitsluit and any(re.search(rx, str(_get(x, k)), re.I) for k, rx in uitsluit.items()):
            continue
        if kinderen:
            kids = _get(x, kinderen)
            if t and isinstance(kids, list):
                for c in kids:
                    if isinstance(c, dict): maak(c, t, x)
                continue
        elif t and (not vereist or _get(x, vereist) not in (None, '', [])):
            maak(x, t)
        stack += [v for v in x.values() if isinstance(v, (dict, list))]
    return out


def embedded(web, url, **kw):
    """JSON die in de pagina zelf zit (zie ingebed)."""
    page = web.text(url)
    if not page: return []
    out = []
    for j in ingebed(page): out += json_events(j, url, **kw)
    return out


def jsonapi(web, url, params=None, base=None, items=None, **kw):
    """Een JSON-endpoint dat de site zelf voor de eigen agenda laadt (url = het endpoint, url_k = sleutel voor de
    link per event)."""
    j = web.json(url, params)
    if j is None: return []
    if items: j = _pad(j, items)
    return json_events(j, base or url, **kw)


# ---------------------------------------------------------------- HTML-agenda (generiek: kaartjes met link + datum)

class _N:
    __slots__ = ('tag', 'attrs', 'kids', 'up')

    def __init__(self, tag, attrs, up):
        self.tag, self.attrs, self.kids, self.up = tag, attrs, [], up


class _Dom(HTMLParser):
    VOID = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'source', 'track', 'wbr', 'param'}
    SKIP = {'script', 'style', 'noscript', 'svg', 'template'}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = _N('root', {}, None); self.cur = self.root; self.skip = 0

    def handle_starttag(self, tag, attrs):
        if self.skip or tag in self.SKIP:
            if tag in self.SKIP: self.skip += 1
            return
        n = _N(tag, {k: (v or '') for k, v in attrs}, self.cur)
        self.cur.kids.append(n)
        if tag not in self.VOID: self.cur = n

    def handle_startendtag(self, tag, attrs):
        if self.skip or tag in self.SKIP: return
        self.cur.kids.append(_N(tag, {k: (v or '') for k, v in attrs}, self.cur))

    def handle_endtag(self, tag):
        if tag in self.SKIP:
            self.skip = max(0, self.skip - 1); return
        if self.skip: return
        n = self.cur
        while n is not None and n.tag != tag: n = n.up
        if n is not None and n.up is not None: self.cur = n.up

    def handle_data(self, d):
        if not self.skip and d.strip(): self.cur.kids.append(d)


BLOK = {'p', 'div', 'li', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'tr', 'td', 'th', 'article', 'section', 'br', 'time',
        'span', 'a', 'header', 'footer', 'dt', 'dd', 'strong', 'b', 'em', 'small', 'button', 'figcaption', 'label'}


def _tekst(n, sep=' | '):
    out = []

    def w(x):
        if isinstance(x, str): out.append(x); return
        for k in x.kids: w(k)
        if x.tag in BLOK: out.append(sep)
    w(n)
    s = re.sub(r'\s+', ' ', ''.join(out))
    s = re.sub(r'(\s*\|\s*)+', ' | ', s)
    return s.strip(' |')


def _alle(n, pred):
    stack = [n]
    while stack:
        x = stack.pop()
        if isinstance(x, str): continue
        if pred(x): yield x
        stack.extend(reversed(x.kids))


def _match(n, sel):
    """Mini-selector: 'h3', '.class-deel', 'h3.class-deel', '[attr]'."""
    if not sel: return False
    for s in sel.split(','):
        s = s.strip()
        m = re.fullmatch(r'([a-z0-9]*)(?:\.([\w-]+))?(?:\[([\w-]+)\])?', s)
        if not m: continue
        tag, cls, attr = m.groups()
        if tag and n.tag != tag: continue
        if cls and cls not in n.attrs.get('class', ''): continue
        if attr and attr not in n.attrs: continue
        return True
    return False


_RX_WD = re.compile(r'(?<![\w])' + _D + r'(?![\w])\.?', re.I)
_RX_MAAND = re.compile(r'(?<![\w])' + _M + r'(?![\w])\.?', re.I)


def _is_titel(t):
    """True als er na het weghalen van datums, tijden, dag- en maandnamen nog echte tekst over is."""
    if not t or len(t) < 2: return False
    r = t
    for rx in (RX_ISO, RX_DMY, RX_DM_TXT, RX_MD_TXT, RX_WD_DMY, RX_WD_DM, RX_REL, RX_TIME, RX_TIME_U, RX_TIME_AMPM, _RX_WD, _RX_MAAND):
        r = rx.sub(' ', r)
    r = re.sub(r'\b(20\d\d|doors?|deuren|open|aanvang|start|tot|until|till|uur|from|vanaf)\b', ' ', r, flags=re.I)
    return len(re.findall(r'[^\W\d_]', r)) >= 3


def _los(n):
    """Alle tekststukken van een element met spaties ertussen (ook tussen inline-elementen: '2026' '20:30')."""
    out = []

    def w(x):
        if isinstance(x, str): out.append(x); return
        for k in x.kids: w(k)
    w(n)
    return ' '.join(out)


def _datum_in(card, text, vandaag):
    """Datum en tijd in een kaartje: eerst <time>/datetime-attributen, anders de eerste datum in de tekst."""
    for t in _alle(card, lambda x: x.tag == 'time' or 'datetime' in x.attrs or 'data-date' in x.attrs or 'content' in x.attrs and x.attrs.get('itemprop') == 'startDate'):
        v = t.attrs.get('datetime') or t.attrs.get('data-date') or t.attrs.get('content')
        d, met = iso(v) if v else (None, False)
        zicht = _los(t)
        zd, zt = datums(zicht, vandaag), tijd(zicht)
        if zd and zt: return zd[0][1], zt, 0  # zichtbare datum + tijd gaat voor (Framer zet lokale tijd met een 'Z')
        if d: return d.date(), (d.strftime('%H:%M') if met else zt), 0  # <time datetime="2026-10-30">… <span>20:30</span>
    ds = datums(text, vandaag)
    if ds:
        pos, d = ds[0]
        return d, tijd(text[pos:]) or tijd(text), pos
    return None, None, None


_KNOP = re.compile(r'(koop |buy |get |bestel )?(je |your )?tickets?|meer info|more info|lees meer|lees verder|verder lezen|'
                   r'read more|bekijk|details|view|info|uitverkocht|sold out|€.*|gratis|free', re.I)


def kaartjes(web, url, link=None, titel=None, kop=False, datum=None, loc=None, uitsluit=None, vandaag=None, page=None,
             kaart=None, niet_in=None, html_veld=None):
    """Generieke HTML-agenda: elk event is een link (`link` = regex op de url) in een 'kaartje' met datum en titel.
    Het kaartje is het grootste blok rond de link waarin geen links naar andere events staan.
    kop=True: de datum staat als tussenkop boven een groep events. titel/datum/loc: mini-selector ('h3', '.deel',
    'span.title', 'a[aria-label]') voor het titel-, datum- of locatie-element (loc: zonder treffer de hele kaarttekst).
    kaart: selector voor het kaartje zelf (voor events zonder eigen link of met dezelfde link; link = eerste passende
    link erin, anders de agendapagina). niet_in: selector van blokken die eerst weg moeten (bijv. een dubbele
    mobiele lijst). html_veld: de pagina is JSON met de HTML in dit veld (een 'meer laden'-endpoint)."""
    if page is None:
        page = (_pad(web.json(url) or {}, html_veld) if html_veld else web.text(url))
    if not isinstance(page, str) or not page: return []
    vandaag = vandaag or nu().date()
    dom = _Dom()
    try: dom.feed(page); dom.close()
    except Exception: pass
    if niet_in:
        for n in list(_alle(dom.root, lambda x: _match(x, niet_in))):
            if n.up is not None and n in n.up.kids: n.up.kids.remove(n)
    lp = re.compile(link, re.I) if link else DETAIL
    ux = re.compile(uitsluit, re.I) if uitsluit else None
    host = urllib.parse.urlparse(url).netloc.replace('www.', '')

    def href(n):
        h = n.attrs.get('href') if n.tag == 'a' else None
        if not h or h.startswith(('#', 'mailto:', 'tel:', 'javascript:')): return None
        u = urllib.parse.urljoin(url, html.unescape(h)).split('#')[0]
        if not lp.search(u) or (ux and ux.search(u)): return None
        if not link and urllib.parse.urlparse(u).netloc.replace('www.', '') != host: return None
        return u.rstrip('/')

    sets = {}

    def links_in(n):
        k = id(n)
        if k not in sets:
            s = set()
            for a in _alle(n, lambda x: x.tag == 'a'):
                h = href(a)
                if h: s.add(h)
                if len(s) > 1: break
            sets[k] = s
        return sets[k]

    if kaart:
        cards = [n for n in _alle(dom.root, lambda x: _match(x, kaart))
                 if not any(_match(k, kaart) for k in _alle(n, lambda x: x is not n))]
        paren = []
        for c in cards:
            a = next((x for x in _alle(c, lambda x: x.tag == 'a') if href(x)), None)
            paren.append((c, href(a) if a is not None else url))
    else:
        paren = []
        for a in _alle(dom.root, lambda x: x.tag == 'a'):
            h = href(a)
            if not h or h.rstrip('/') == url.rstrip('/'): continue
            card, hops = a, 0
            while card.up is not None and card.up.tag not in ('root', 'body', 'main') and links_in(card.up) <= {h} and hops < 12:
                card, hops = card.up, hops + 1
            paren.append((card, h))

    out, done = [], set()
    for card, h in paren:
        if id(card) in done: continue
        done.add(id(card))
        dn = next(iter(_alle(card, lambda x: _match(x, datum))), None) if datum else None
        text = _tekst(card)
        d, tt, pos = _datum_in(dn or card, _tekst(dn) if dn is not None else text, vandaag)
        if d is None and dn is not None: d, tt, pos = _datum_in(dn, _tekst(dn, ''), vandaag)  # '30','.','10','.','2026'
        if d is not None and dn is not None and not tt: tt = tijd(text)
        if d is None and kop:
            # datum als tussenkop: dichtstbijzijnde voorgaande tekst met een datum
            n, hops = card, 0
            while n is not None and n.up is not None and d is None and hops < 6:
                sibs = n.up.kids
                for s in reversed(sibs[:sibs.index(n)]):
                    st = s if isinstance(s, str) else _tekst(s)
                    if isinstance(s, _N) and links_in(s): continue
                    ds = datums(st, vandaag)
                    if ds: d = ds[-1][1]; break
                n, hops = n.up, hops + 1
            if d: tt = tijd(text)
        if d is None: continue
        t = ''
        if titel:
            tn = next(iter(_alle(card, lambda x: _match(x, titel))), None)
            t = _tekst(tn, ' ') if tn is not None else ''
            if tn is not None and not t: t = tn.attrs.get('aria-label') or tn.attrs.get('title') or ''
        else:
            for tn in _alle(card, lambda x: x.tag in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6') or (
                    re.search(r'title|titel|name|naam|heading', x.attrs.get('class', ''), re.I) and not re.search(r'sub|sup|date|datum', x.attrs.get('class', ''), re.I))):
                t = _tekst(tn, ' ')
                if _is_titel(t) and not _KNOP.fullmatch(t): break
                t = ''
        if not t:
            parts = [p for p in text.split(' | ') if _is_titel(p) and not _KNOP.fullmatch(p)]
            t = max(parts, key=len) if parts else ''
        t = re.sub(r'\s+([01]?\d|2[0-3])[:.][0-5]\d(\s*uur)?$', '', t)  # tijd achter de titel
        if not t: continue
        start = dt.datetime.combine(d, dt.time(int(tt[:2]), int(tt[3:]))) if tt else dt.datetime.combine(d, dt.time())
        lv = None
        if loc:
            ln = next(iter(_alle(card, lambda x: _match(x, loc))), None)
            lv = _tekst(ln, ' ') if ln is not None else text
        out.append(item(t, start, bool(tt), h, lv))
    return out


# ---------------------------------------------------------------- RSS met event-velden (WeTicket)

def rss(web, url, org=None):
    """RSS-feed met de 'ev:'-module (ev:startdate). org: regex op ev:organizer (bij gedeelde feeds)."""
    t = web.text(url)
    if not t: return []
    out = []
    for blok in re.findall(r'<item>(.*?)</item>', t, re.S):
        f = lambda tag: (re.search(r'<' + tag + r'>(.*?)</' + tag + r'>', blok, re.S) or [None, None])[1]
        titel, link, start = f('title'), f('link'), f('ev:startdate')
        if org and not re.search(org, f('ev:organizer') or '', re.I): continue
        if not (titel and start): continue
        titel = re.sub(r'^<!\[CDATA\[(.*)\]\]>$', r'\1', titel.strip(), flags=re.S)
        d, met = iso(start.strip())
        if d: out.append(item(titel, d, met, html.unescape((link or url).strip())))
    return out


def weticket(web, shop, org=None):
    """Eigen WeTicket-shop van de venue (<shop>.weticket.io): de shop verwijst zelf naar zijn RSS-feed met alle
    komende events (api.weticket.io/storefront/organizations/<id>/events.xml)."""
    page = web.text(f'https://{shop}.weticket.io/')
    m = re.search(r'href="(https://api\.weticket\.io/storefront/organizations/[0-9a-f-]+/events\.xml)"', page or '')
    return rss(web, html.unescape(m[1]), org) if m else []


# ---------------------------------------------------------------- agenda in de JS-bundel van een SPA (Club Church)

def jsbundel(web, url, script=r'/assets/index-[\w-]+\.js', pad='/parties/', uitsluit=r'^(closed|toBeAnnounced)$'):
    """Agenda die hard in de JavaScript-bundel van de site staat: objecten {day,month,year,startTime,theme} en een
    titelmap {title:{theme:"naam"}} (Vite/React, Club Church)."""
    page = web.text(url)
    m = re.search(r'src="(' + script + ')"', page or '')
    js = web.text(urllib.parse.urljoin(url, m.group(1))) if m else None
    if not js: return []
    tm = re.search(r'=\{title:\{(.*?)\}', js, re.S)
    titels = dict(re.findall(r'(\w+):"([^"]*)"', tm.group(1))) if tm else {}
    out = []
    for obj in re.findall(r'\{(day:\d+,month:\d+,year:20\d\d,[^{}]*theme:"\w+"[^{}]*)\}', js):
        f = dict(re.findall(r'(\w+):("[^"]*"|[\d.e]+|!0|!1)', obj))
        th = f.get('theme', '').strip('"')
        if not th or re.search(uitsluit, th): continue
        try: d = dt.datetime(int(float(f['year'])), int(float(f['month'])), int(float(f['day'])))
        except (KeyError, ValueError): continue
        met = 'startTime' in f
        if met:
            st = int(float(f['startTime'])); d = d.replace(hour=st // 100 % 24, minute=st % 100)
        t = titels.get(th, th)
        if f.get('extraTitle'): t = f'{t} ({f["extraTitle"].strip(chr(34))})'
        out.append(item(t, d, met, urllib.parse.urljoin(url, pad + th)))
    return out


# ---------------------------------------------------------------- maatwerk: Bitterzoet

def bitterzoet(web, url='https://www.bitterzoet.com/agenda/'):
    """De agendapagina laadt het programma per maand via admin-ajax (action load_agenda_results, met de nonce uit
    de pagina). We doen dezelfde verzoeken: 'now' plus de maanden binnen de periode."""
    import base64
    page = web.text(url)
    if not page: return []
    js = page + ''.join(base64.b64decode(b).decode('utf-8', 'replace')
                        for b in re.findall(r'src="data:text/javascript;base64,([A-Za-z0-9+/=]+)"', page))
    nonce = re.search(r'"agendaNonce"\s*:\s*"(\w+)"', js)
    ajax = re.search(r'"url"\s*:\s*"(https:[^"]+admin-ajax\.php)"', js)
    if not nonce or not ajax: return kaartjes(web, url, link=r'bitterzoet\.com/event/', page=page)
    tot = (nu() + dt.timedelta(days=95)).strftime('%Y-%m')
    maanden = ['now'] + [m for m in dict.fromkeys(re.findall(r'data-filter="(\d{4}-\d\d)"', page)) if m <= tot]
    out = []
    for m in maanden:
        r = web.post(ajax[1].replace(r'\/', '/'), {'action': 'load_agenda_results', 'agendaNonce': nonce[1],
                                                   'query': json.dumps({'label': 'all', 'query': '', 'month': m})})
        try: content = r.json().get('content') if r is not None else None
        except Exception: content = None
        if content: out += kaartjes(web, url, link=r'bitterzoet\.com/event/', page=content)
    return out


# ---------------------------------------------------------------- maatwerk: Paradiso (ook Parallel)

def paradiso(web, locatie, max_detail=40):
    """paradiso.nl toont het programma van alle locaties van Paradiso (Paradiso, Parallel, Tolhuistuin, ...).
    Elke pagina bevat server-side de eerste 25 programma-items (objecten 'eventType' met startDateTime en
    location); elke eventpagina bevat bovendien het eigen event. De volledige lijst laadt de site via een GraphQL-API
    met een Bearer-token: die gebruiken we niet. De JSON-LD van Paradiso zet de UTC-tijd neer met '+01:00' erachter
    (een uur te vroeg), dus die slaan we ook over. locatie: exacte locatienaam ('Paradiso', 'Parallel')."""
    base = 'https://www.paradiso.nl'
    gevonden, links = {}, []
    for u in (base + '/programma', base + '/'):
        p = web.text(u)
        if not p: continue
        links += [urllib.parse.urljoin(base, h) for h in re.findall(r'href="(/programma/[\w-]+/\d+)"', p)]
        for j in ingebed(p): _paradiso_events(j, gevonden)
    for u in list(dict.fromkeys(links))[:max_detail]:
        eid = u.rsplit('/', 1)[-1]
        if eid in gevonden: continue
        p = web.text(u)
        if p:
            for j in ingebed(p): _paradiso_events(j, gevonden)
    out = []
    for x in gevonden.values():
        loc = x.get('location')
        loc = loc.get('title') if isinstance(loc, dict) else (loc[0].get('title') if isinstance(loc, list) and loc and isinstance(loc[0], dict) else None)
        if loc != locatie or x.get('eventStatus') in ('cancelled', 'canceled'): continue
        d, met = iso(x.get('startDateTime'))
        if d: out.append(item(x.get('title'), d, met, urllib.parse.urljoin(base + '/', x.get('uri') or ''), loc))
    return out


def _paradiso_events(x, gevonden):
    stack = [x]
    while stack:
        y = stack.pop()
        if isinstance(y, list): stack += y; continue
        if not isinstance(y, dict): continue
        if y.get('__typename') in ('eventType', 'event_default_Entry') and y.get('startDateTime') and y.get('id'):
            gevonden.setdefault(str(y['id']), y)  # startDateTime is echte UTC/offset-tijd (de site rekent zelf om)
        stack += [v for v in y.values() if isinstance(v, (dict, list))]
