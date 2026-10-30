"""Agenda: komende feesten en concerten per venue, uit openbare bronnen van de venue zelf.

Gebruik: python -X utf8 tools/agenda.py            (alle venues met een website)
         python -X utf8 tools/agenda.py paradiso lofi
         python -X utf8 tools/agenda.py -v paradiso  (toont per bron wat er gevonden is)
Schrijft: data/agenda.json  {venue_id: [{title, date, time, url}], ...}  (vandaag t/m de komende 90 dagen)

Bronnen (zie tools/agenda_bronnen.py; per venue ingesteld in BRONNEN hieronder, anders de standaard JSON-LD-crawl):
- eigen website: schema.org Event (JSON-LD), The Events Calendar en andere WordPress-REST, Squarespace-JSON,
  sitemaps met eventpagina's (Wix), ingebedde JSON (Next.js, Nuxt, Astro, Vue-props), JSON die de agendapagina zelf
  laadt, en HTML-agenda's (generieke 'kaartjes'-parser);
- open agenda's en eigen ticketshops die robots.txt toestaan: Radar (radar.squat.net), WeTicket-feeds, Ticket Tailor.
Respecteert robots.txt (ook wildcards en $) en crawl-delay, met een eigen User-Agent; geen browser-UA, geen
botcontroles omzeilen, geen API's met sleutel. Niet gelezen omdat robots.txt het verbiedt of er een botcontrole is:
Weeztix/Eventix, Stager, Paylogic, de API van Celebratix, Fourvenues. TicketSwap en Resident Advisor hebben geen open
API en hun voorwaarden staan scrapen niet toe; die worden nooit gelezen.

Levert een venue deze keer niets op (site plat, time-out), dan blijven de nog komende items van de vorige run staan.
Draait in ruim een minuut; harde grens MAX_SEC, daarna worden hangende venues als 'niets' behandeld.
"""
import sys, os, re, json, time, datetime as dt, traceback
from concurrent.futures import ThreadPoolExecutor, wait
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import agenda_bronnen as B

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
OUT = os.environ.get('AGENDA_OUT') or os.path.join(ROOT, 'data', 'agenda.json')
DAGEN, MAX_SEC, WORKERS = 90, 540, 10
AFGELAST = re.compile(r'\b(cancell?ed|geannuleerd|afgelast|gecanceld)\b', re.I)

# Per venue: lijst van (adapter, argumenten), zie tools/agenda_bronnen.py. Argumenten met een _ zijn filters:
#   _loc: regex waar de locatie (loc) aan moet voldoen   _niet: regex op titels die weg moeten
#   _wel: regex waar de titel aan moet voldoen          _url: regex waar de url aan moet voldoen
# Een lege lijst = bewust geen bron (reden erachter). Venues die hier niet staan krijgen de standaard JSON-LD-crawl.
_PG = lambda u, n, eerste='': [u + (eerste if i == 1 else f'?page={i}') for i in range(1, n + 1)]
BRONNEN = {
    # ---- clubs
    'akhnaton': [('kaartjes', {'url': 'https://akhnaton.nl/agenda/'})],
    'bitterzoet': [('bitterzoet', {})],
    'canvas': [('kaartjes', {'url': 'https://www.volkshotel.nl/agenda/canvas/', 'link': r'volkshotel\.nl/agenda/canvas/[^/]+'})],
    'doka': [('kaartjes', {'url': 'https://www.volkshotel.nl/agenda/doka/', 'link': r'volkshotel\.nl/agenda/doka/[^/]+'})],
    'club-church': [('jsbundel', {'url': 'https://www.clubchurch.nl/'})],
    'club-raum': [('kaartjes', {'url': 'https://clubraum.nl/program', 'link': r'clubraum\.nl/events/[^/]+'})],
    'club-up': [('squarespace', {'url': 'https://www.clubup.nl/program'})],
    'de-trut': [('kaartjes', {'url': 'https://www.trutfonds.nl/', 'link': r'trutfonds\.nl/[\w-]+\.html'})],
    'eagle-amsterdam': [('jsonld', {'urls': ['https://www.eagleamsterdam.com/event-agenda-eagle-amsterdam/']})],
    'escape': [('kaartjes', {'url': 'https://escape.nl/en/agenda/', 'link': r'escape\.nl/en/20\d\d-\d\d-\d\d_', '_niet': r'\b\d{1,2} [A-Za-z]{3,4}\.$'})],
    'exit-cafe': [('sitemap', {'url': 'https://www.exitamsterdam.nl/event-pages-sitemap.xml'})],  # Wix Events; nu leeg
    'garage-noord': [('weticket', {'shop': 'garagenoord'})],
    'gashouder': [('jsonld', {'klok': True})],  # JSON-LD zet lokale tijd met '+00:00'
    'lofi': [('jsonld', {})],
    'maloe-melo': [('tribe', {'base': 'https://www.maloemelo.com'})],
    'melkweg': [('embedded', {'url': 'https://www.melkweg.nl/nl/agenda/', 'titel': 'name', 'start': 'startDate', 'loc': 'profile',
                              'vereist': 'yesplan_id', 'uitsluit': {'isCancelled': 'True', 'isPrivateEvent': 'True', 'profile': '^(Film|Expositie)$'}})],
    'mewe': [('kaartjes', {'url': 'https://mewe.amsterdam/', 'link': r'shop\.(weeztix\.com|celebratix\.io)', 'kaart': '.jet-listing-grid__item'})],
    'occii': [('kaartjes', {'url': 'https://occii.org/events/', 'link': r'occii\.org/events/[^/]+'})],
    'oliva': [('jsonapi', {'url': 'https://oliva-amsterdam.nl/wp-json/ticketapp/v1/events/', 'titel': 'name', 'start': 'startAt',
                           'pad': 'https://shop.ticketapp.com/fgsmnt'})],
    'ot301': [('jsonapi', {'url': 'https://amsterdamalternative.nl/services/get-events-past-v25.php', 'params': {'venue': 105, 'months': 4},
                           'items': 'items', 'base': 'https://www.ot301.nl/agenda/', 'titel': 'title', 'start': 'start', 'url_k': 'id',
                           '_niet': r'^(Lunch|Dinner) at Café Gilde'})],
    'pacific': [('kaartjes', {'url': 'https://www.pacificamsterdam.nl/events', 'link': r'pacificamsterdam\.nl/events/[^/]+'})],
    'panama': [('tribe', {'base': 'https://panama.nl'})],
    'paradiso': [('paradiso', {'locatie': 'Paradiso'})],
    'parallel': [('paradiso', {'locatie': 'Parallel'})],
    'q-factory': [('embedded', {'url': 'https://q-factory.com/nl', 'titel': 'name', 'start': 'content.startTime', 'pad': '/nl/events/',
                                'vereist': 'content.startTime'})],
    'radion': [('kaartjes', {'url': 'https://radion.amsterdam/program/', 'link': r'radion\.amsterdam/program/[^/]+',
                             'titel': '.r-event-row__title', 'datum': '.r-event-row__when'})],
    'shelter': [('kaartjes', {'url': 'https://www.shelteramsterdam.nl/', 'link': r'fourvenues\.com/shelter-amsterdam/'})],  # links niet opgehaald
    'sissis': [('kaartjes', {'url': 'https://www.sissisamsterdam.nl/agenda', 'link': r'sissisamsterdam\.nl/events/[^/]+'})],
    'soulkitchen': [('embedded', {'url': 'https://www.soulkitchenamsterdam.nl/events-by-day', 'kinderen': 'editions', 'titel': 'title',
                                  'start': 'date', 'tijdk': 'time', 'url_k': 'id', 'pad': '/events-by-day/',
                                  'ouder_url': True})],
    'supperclub': [('kaartjes', {'url': 'https://supper.nl/events-2/', 'link': r'shop\.(celebratix\.io|weeztix\.com)', 'kaart': '.e-con-full'})],
    'the-other-side': [('kaartjes', {'url': 'https://the-other-side.nl/', 'link': r'^https?://', 'niet_in': '.elementor-hidden-mobile'})],
    'thuishaven': [('kaartjes', {'url': 'https://thuishaven.nl/', 'link': r'thuishaven\.nl/\d{1,2}-[a-z]{3}-[^/]+'})],
    'toekomstmuziek': [('jsonapi', {'url': 'https://api.bash.social/organisations/1107/events', 'params': {'page': 0, 'size': 100},
                                    'base': 'https://bash.social/toekomstmuziek', 'titel': 'name', 'start': 'startDate', 'vereist': 'code',
                                    'url_k': '_geen'})],
    'tolhuistuin': [('embedded', {'url': 'https://tolhuistuin.nl/agenda', 'titel': 'title', 'start': 'eventStartCompare', 'tijdk': 'eventStartDate',
                                  'url_k': 'url', 'vereist': 'eventType', 'uitsluit': {'eventType.label': '^Doorlopend$', 'location': 'Externe'}})],
    'under-hans': [('jsonld', {'urls': ['https://tickets.onderhans.com/events/hansbrinker'], 'detail': r'/events/hansbrinker/\d+', '_loc': r'Onder Hans'})],
    'vondelbunker': [('radar', {'group': '19942'})],
    'vrankrijk': [('radar', {'group': '137050', '_niet': r'^closed!?$'})],
    'warehouse-elementenstraat': [('kaartjes', {'url': 'https://elementenstraat.nl/events', 'link': r'^https?://(?!(www\.)?elementenstraat\.nl)',
                                                'titel': '.is-event', 'datum': '.event-list_date', 'niet_in': '.accordion-item'})],
    'bret': [],  # Wix Events laadt alleen in de browser via de Wix-API; geen event-sitemap
    'cafe-cafe-bar': [],  # geen programma, alleen privéfeesten op aanvraag
    'chicago-social-club': [], 'chin-chin-club': [], 'jimmy-woo': [],  # alleen Celebratix-widget (API verboden in robots.txt)
    'club-8': [],  # botcontrole (403, ook op robots.txt)
    'club-john-doe': [],  # alleen een Fourvenues-iframe (botcontrole)
    'club-lite': [],  # site geeft 404
    'club-nyx': [],  # agenda verwijst naar Facebook; tickets via Eventix (robots.txt verbiedt)
    'club-prime': [],  # site in onderhoud
    'club-smokey': [],  # geen agenda op de site
    'de-kroon': [],  # site plat (certificaatfout)
    'disco-dolly': [],  # Tuftuf: alleen vaste openingsavonden
    'het-veronicaschip': [],  # agenda via /api/, en robots.txt verbiedt /api/
    'kanarie-club': [],  # alleen zaalverhuur
    'oosterbar': [],  # domein bestaat niet meer
    'shu': [],  # geen agenda (Wix zonder events)
    'skatecafe': [],  # site plat (HTTP 500)
    'soho': [],  # alleen vaste weekavonden zonder datums
    'taboo': [],  # site plat
    # ---- podia
    'afas-live': [('kaartjes', {'url': 'https://www.afaslive.nl/agenda', 'link': r'afaslive\.nl/agenda/[^/?#]+$', 'titel': 'h4',
                                'loc': 'article', '_loc': r'^(?!.*Geannuleerd)'})],
    'bimhuis': [('kaartjes', {'url': u, 'link': r'bimhuis\.nl/agenda/[^/?#]+/?$'}) for u in _PG('https://www.bimhuis.nl/agenda/', 6)],
    'carre': [('jsonapi', {'url': 'https://carre.nl/api/render/production-page-list-nl', 'items': 'productions', 'base': 'https://carre.nl/agenda',
                           'titel': 'data.name', 'start': 'start_date'})],
    'cinetol': [('kaartjes', {'url': 'https://www.cinetol.nl/programma', 'link': r'cinetol\.nl/events/[^/?#]+$', 'titel': 'h2'})],
    'concertgebouw': [('embedded', {'url': u}) for u in _PG('https://www.concertgebouw.nl/concerten-en-tickets', 10)],
    'de-balie': [('wp', {'base': 'https://debalie.nl', 'typ': 'vo-programme', 'start': 'vo.date', 'tijd_veld': 'vo.time',
                         '_niet': r'Wageningen|^Nationaal Gesprek over Vrijheid'})],
    'de-brakke-grond': [('kaartjes', {'url': 'https://brakkegrond.nl/agenda', 'link': r'brakkegrond\.nl/agenda/\d+/', 'titel': 'h3',
                                      'loc': 'a.card-default', '_loc': r'^(?!.*\b(Buitenshuis|Residentie)\b)'})],
    'de-nieuwe-anita': [('kaartjes', {'url': 'https://denieuweanita.nl/', 'link': r'denieuweanita\.nl/agenda/[^/?#]+/?$', 'titel': 'a[aria-label]',
                                      'loc': '.agenda_time_start', '_loc': r'\d:\d\d'})],
    'delamar': [('jsonapi', {'url': 'https://delamar.nl/Entity/GetProductions', 'params': {'id': 1106, 'isMobile': 'false', 'culture': 'nl-NL', 'p': i},
                             'base': 'https://delamar.nl/', 'items': 'pagedList.items', 'titel': 'title', 'kinderen': 'dates', 'start': 'date', 'url_k': 'url', 'ouder_url': True})
                for i in range(1, 8)],
    'ita': [('kaartjes', {'url': u, 'link': r'ita\.nl/nl/voorstellingen/', 'kop': True, 'titel': 'h3', 'loc': '.OverviewListItem',
                          '_loc': r'^(?!.*(Geannuleerd|Schoolvoorstelling))(?=.*Stadsschouwburg Amsterdam)', '_niet': r'rondleiding|public tour'})
            for u in _PG('https://www.ita.nl/nl/agenda-stadsschouwburg', 9)],
    'bijlmer-parktheater': [('jsonld', {})],
    'de-meervaart': [('jsonld', {})],
    'frascati': [('jsonld', {})],
    'johan-cruijff-arena': [('kaartjes', {'url': 'https://www.johancruijffarena.nl/kalender/', 'link': r'johancruijffarena\.nl/kalender/\d+-'})],
    'muziekgebouw': [('kaartjes', {'url': 'https://www.muziekgebouw.nl/nl/agenda' + ('' if i == 1 else f'?p54_page={i}'),
                                   'link': r'muziekgebouw\.nl/nl/agenda/[^/?#]+$', '_niet': r'^rondleiding'}) for i in range(1, 13)],
    'p60': [('kaartjes', {'url': 'https://p60.nl/agenda/' + ('' if i == 1 else f'page/{i}/'), 'link': r'p60\.nl/20\d\d/[^/]+/?$', 'titel': 'h1'})
            for i in range(1, 6)],
    'pakhuis-de-zwijger': [('kaartjes', {'url': 'https://dezwijger.nl/agenda', 'link': r'dezwijger\.nl/programma/[^/?#]+'})] +
                          [('kaartjes', {'url': f'https://dezwijger.nl/ajax/agenda/getItems?page={i}', 'link': r'dezwijger\.nl/programma/[^/?#]+',
                                         'html_veld': 'data'}) for i in range(2, 5)],
    'podium-mozaiek': [('jsonapi', {'url': 'https://www.podiummozaiek.nl/api/events', 'base': 'https://www.podiummozaiek.nl/programma/agenda',
                                    'titel': 'name', 'start': 'startts', 'loc': 'locationname', '_loc': r'^(?!.*(Wasserette|De Vlugt))'})],
    'theater-amsterdam': [('kaartjes', {'url': 'https://www.theateramsterdam.nl/agenda', 'link': r'theateramsterdam\.nl/agenda/[^/?#]+', 'titel': 'h3'})],
    'zaal-100': [('kaartjes', {'url': 'https://zaal100.nl/', 'link': r'zaal100\.nl/event/[^/]+/?$', 'titel': 'h2', '_niet': r'^Restaurant:'})],
    'ziggo-dome': [('jsonapi', {'url': 'https://www.ziggodome.nl/api/agenda/aankomend', 'params': {'limit': 50, 'offset': o}, 'items': 'data',
                                'base': 'https://www.ziggodome.nl/', 'titel': 'performerName', 'start': 'showDate', 'utc': True, 'url_k': 'id',
                                'pad': '/events/', 'loc': 'showState', '_loc': r'^(?!Canceled)'}) for o in (0, 50, 100, 150)],
    'lab111': [],  # bioscoop: alleen filmvertoningen
    # ---- bars
    'bar-benelux': [('jsonapi', {'url': 'https://cms.be-ne-lux.bar/api/v1.0/events?future', 'base': 'https://be-ne-lux.bar/', 'titel': 'title',
                                 'start': 'doorsOpen', 'pad': '/events/'})],
    'bourbon-street': [('kaartjes', {'url': 'https://www.bourbonstreet.nl/', 'link': r'bourbonstreet\.nl/shows/[^/]+\.html'})],
    'club-baggerbeest': [('kaartjes', {'url': 'https://barbaggerbeest.nl/agenda/', 'link': r'barbaggerbeest\.nl/agenda/[^/]+', '_niet': r'besloten|bruiloft'})],
    'mezrab': [('kaartjes', {'url': 'https://mezrab.nl/', 'link': r'mezrab\.nl/events/[^/]+', '_niet': r'Storytelling Festival|^Mezrab at '})],
    'noorderlicht-cafe': [('embedded', {'url': 'https://www.noorderlichtndsm.nl/nl/evenementen', 'titel': 'title', 'start': 'eventDate',
                                        'tijdk': 'startTime', 'pad': '/nl/evenementen/'})],
    'oedipus-craft-space': [('weticket', {'shop': 'oedipus'})],
    'studio-k': [('kaartjes', {'url': 'https://studio-k.nu/events/', 'link': r'studio-k\.nu/studiok-events/[^/]+', 'titel': 'span.title', '_niet': r'screening'})],
    'waterkant': [('embedded', {'url': 'https://www.waterkantamsterdam.nl/agenda', 'titel': 'header', 'start': 'date', 'tijdk': 'dateSubtitle',
                                'alle_datums': True, '_niet': r'@'})],
    'cafe-de-duivel': [], 'lux': [], 'weber': [], 'klaproos': [], 'hannekes-boom': [], 'spijker-bar': [],  # bar zonder programma met datums
    'cue': [],  # programma alleen als maand-PDF
    'nachbar': [],  # alleen een Linktree-pagina; robots.txt van linktr.ee verbiedt het
    'hangar': [],  # alleen een vast weekschema
    'ijver': [],  # geen publieke agenda
    'madam': [],  # alleen Fourvenues-widget (botcontrole)
    'montmartre-xl': [],  # site weigert (429, botcontrole)
    'the-waterhole': [],  # toont alleen vandaag en morgen, zonder eventlinks
}


def verzamel(web, v, verbose=False):
    """Alle bronnen van één venue; geeft (items, gebruikte_bronnen)."""
    bronnen = BRONNEN[v['id']] if v['id'] in BRONNEN else ([('jsonld', {})] if v.get('website') else [])
    found, used = [], []
    for naam, args in bronnen:
        kw = {k: a for k, a in args.items() if not k.startswith('_')}
        flt = {k: a for k, a in args.items() if k.startswith('_')}
        try:
            fn = getattr(B, naam)
            res = fn(web, v, **kw) if naam == 'jsonld' else fn(web, **kw)
        except Exception:
            if verbose: traceback.print_exc()
            res = []
        if flt.get('_loc'): res = [e for e in res if e['loc'] and re.search(flt['_loc'], e['loc'], re.I)]
        if flt.get('_wel'): res = [e for e in res if re.search(flt['_wel'], e['title'], re.I)]
        if flt.get('_niet'): res = [e for e in res if not re.search(flt['_niet'], e['title'], re.I)]
        if flt.get('_url'): res = [e for e in res if e['url'] and re.search(flt['_url'], e['url'], re.I)]
        if verbose: print(f'  {naam:12s} {len(res):3d} {kw.get("url") or kw.get("base") or kw.get("group") or v.get("website")}')
        if res: used.append(naam)
        found += res
    return found, used


def schoon(found, vandaag):
    """Periode (vandaag t/m +90 dagen), dubbelingen weg, sorteren en naar het formaat van data/agenda.json."""
    tot = vandaag + dt.timedelta(days=DAGEN)
    groups = {}
    for e in found:
        if not e['title'] or not e['start']: continue
        if AFGELAST.search(e['title']): continue
        d = e['start'].date()
        if not (vandaag <= d <= tot): continue
        key = (re.sub(r'\W+', '', e['title'].lower()), d)
        groups.setdefault(key, []).append(e)
    out = []
    for (_, d), evs in groups.items():
        met = [e for e in evs if e['tijd']]
        seen = set()
        for e in (met or evs[:1]):
            t = e['start'].strftime('%H:%M') if e['tijd'] else None
            if t in seen: continue
            seen.add(t)
            out.append({'title': e['title'], 'date': d.strftime('%Y-%m-%d'), 'time': t, 'url': e['url']})
    # hetzelfde event twee keer op de pagina met een andere titel (bijv. een uitgelicht blok): zelfde link, datum en tijd
    best = {}
    for e in out:
        k = (e['url'], e['date'], e['time'])
        if k not in best or len(e['title']) > len(best[k]['title']): best[k] = e
    return sorted(best.values(), key=lambda e: (e['date'], e['time'] or '', e['title']))


def main(argv):
    verbose = '-v' in argv
    ids = [a for a in argv if not a.startswith('-')]
    venues = json.load(open(os.path.join(ROOT, 'data', 'venues.json'), encoding='utf-8'))
    known = {v['id'] for v in venues}
    todo = [v for v in venues if not ids or v['id'] in ids]
    try: oud = json.load(open(OUT, encoding='utf-8'))
    except Exception: oud = {}
    vandaag = B.nu().date()
    web = B.Web()
    t0 = time.time()
    nieuw, stats = {}, {}

    def run(v):
        found, used = verzamel(web, v, verbose)
        return v['id'], schoon(found, vandaag), used

    ex = ThreadPoolExecutor(1 if verbose else WORKERS)
    futs = {ex.submit(run, v): v['id'] for v in todo}
    done, pending = wait(futs, timeout=MAX_SEC)
    for f in done:
        try: vid, evs, used = f.result()
        except Exception: vid, evs, used = futs[f], [], []
        nieuw[vid] = evs
        stats[vid] = used
    for f in pending: print(f'{futs[f]:32s} time-out', flush=True)

    agenda = {k: v for k, v in oud.items() if k in known} if (ids or pending) else {}
    for v in todo:
        vid = v['id']
        evs = nieuw.get(vid) or []
        if evs:
            agenda[vid] = evs; bron = '+'.join(dict.fromkeys(stats.get(vid) or []))
        else:
            keep = [e for e in oud.get(vid, []) if e.get('date', '') >= vandaag.strftime('%Y-%m-%d')]
            if keep: agenda[vid] = keep; bron = 'vorige run bewaard'
            else: agenda.pop(vid, None); bron = ''
        print(f'{vid:32s} {len(agenda.get(vid, [])):3d}  {bron}', flush=True)
    agenda = {k: [e for e in evs if e['date'] >= vandaag.strftime('%Y-%m-%d')] for k, evs in agenda.items() if k in known}
    agenda = {k: evs for k, evs in agenda.items() if evs}
    with open(OUT, 'w', encoding='utf-8') as fh:
        json.dump(dict(sorted(agenda.items())), fh, ensure_ascii=False, separators=(',', ':'))
    print(f'venues met agenda: {len(agenda)} | items: {sum(len(v) for v in agenda.values())} | {time.time() - t0:.0f} s', flush=True)
    ex.shutdown(wait=False, cancel_futures=True)
    if pending: os._exit(0)  # hangende verzoeken niet afwachten


if __name__ == '__main__':
    main(sys.argv[1:])
