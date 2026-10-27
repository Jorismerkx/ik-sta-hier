# Diepteonderzoek: Warehouse Elementenstraat (warehouse-elementenstraat)

Elementenstraat 25 / Isolatorweg 36, 1014 AR Amsterdam (Sloterdijk I, Westpoort). BAG-pand 0363100012128444,
bouwjaar 1964, één verblijfsobject (0363010000678111, hoofdadres Isolatorweg 36, nevenadres Elementenstraat 25,
7.827 m², bijeenkomst-, industrie- en kantoorfunctie). Onderzocht op 27-10-2026.

**Uitkomst in één zin:** er is een echte plattegrond van de begane grond gevonden. Het is een tekening uit 2013 bij het
bestemmingsplan Sloterdijk I, met Zaal 1, 2 en 3, de chill-zaal, de entree en de garderobe, de toiletten en de
binnenplaats. Hij is opnieuw getekend in `data/batches/precisie-11-warehouse-elementenstraat.json` (confidence
middel, basis plattegrond). De beperkingen: het is een voorstel van vóór de opening in 2014, en sinds 2021 zit
AMAZE (ID&T) in hetzelfde pand.

Ligging (belangrijk voor de tekening): de **Isolatorweg loopt langs de westgevel** en de **Elementenstraat langs de
oostgevel**. PDOK-wegcentroïden: Isolatorweg x≈118474, Elementenstraat x≈118574, pand x≈118482–118563. De
evenementeningang ligt dus aan de oostkant, via de binnenplaats in de zuidoosthoek. Het BAG-adrespunt ligt aan de
westgevel en zegt niets over de ingang. De vorige tekening (precisie-05) zette de ingang daarom aan de westkant
(Isolatorweg). Volgens de stukken uit 2013 is dat de ingang van studio's en kantoren, niet die van de club.

---

## 1. Overheid, ruimtelijke ordening

**Gezocht:** ruimtelijkeplannen.nl (planlijst op het punt RD 118483/489696 via het openbare viewer-endpoint
`web-roo/rest/search/plannen/xy`), de plantekst en de bijlagen van het geldende bestemmingsplan, en de
omgevingsplan- en paraplu-plannen.

**Gevonden:**
- **Bestemmingsplan Sloterdijk I** (NL.IMRO.0363.B1104BPGST-VG02, vastgesteld 3 juli 2013). De toelichting zegt in
  §4.1 dat het pand Elementenstraat 25/Isolatorweg 36 de aanduiding 'horeca' krijgt: één horeca II (nachtzaak) van
  maximaal 2.000 m² en één horeca IV (kantine) van maximaal 400 m². Het plan heet daar 'The Element' (platform voor
  elektronische dansmuziek), met 'evenementenzalen op de begane grond' en 1 à 1,5 nacht per week.
  https://www.ruimtelijkeplannen.nl/documents/NL.IMRO.0363.B1104BPGST-VG02/t_NL.IMRO.0363.B1104BPGST-VG02.html
- **Bijlage 2 bij de toelichting: 'Ruimtelijke onderbouwing The Element, Elementenstraat 25/Isolatorweg 36'**
  (Oranjewoud, april 2013, 69 pagina's, gescand).
  https://www.ruimtelijkeplannen.nl/documents/NL.IMRO.0363.B1104BPGST-VG02/b_NL.IMRO.0363.B1104BPGST-VG02_tb2.pdf
  (dezelfde PDF staat ook in de raadsstukken: https://api.notubiz.nl/document/2386804/1).
  Opgeslagen: `data/sources/warehouse-elementenstraat/diep/rp-B1104-bijlage2-the-element.pdf`.
  - **p. 33, 'Bijlage 2: Tekening nieuwe situatie begane grond'.** Dit is de plattegrond 'Herindeling Isolatorweg
    36/Elementenweg 25, Plattegrond begane grond, Voorstel functie-indeling', van MSTRS advies&ontwerp, project
    2013-01, tekening 2013-000-0, gedateerd 08-03-2013, schaal 1:100. Er staan een noordpijl, een stramien (assen
    1–27 / A–L) en ruimtenummers met oppervlaktes op. Totaal gebruiksoppervlak 3.520 m². Uitgesneden en opgeslagen
    als `.../diep/the-element-p33-tekening-begane-grond.jpeg` (2340×1654 px). **Laat de indeling zien: ja.**
    - 0.22-2 **Zaal 1**, 835 m²: de noordhal, assen 7–16 / A–D, met twee rijen kolommen (B en C). Langs de westkant
      staat een lang blok dat vermoedelijk 'Bar' heet (het label is onleesbaar). In het midden staat een kader van
      ca. 4,5 × 3,5 m, ook met een onleesbaar label.
    - 0.31 **Zaal 2**, 368 m²: de smalle middenstrook oost (assen 9/10–27, E–G), met een kolommenrij in het midden
      (as F), twee trappen en een 'stellingvloer' (tussenvloer) erboven. Tussen as 14 en 15 zit een opening naar
      Zaal 1.
    - 0.22-3 **Zaal 3**, 217 m²: de middenstrook west (assen II–8, E–G), met dubbele deuren naar de gang.
    - Tussen Zaal 3 en Zaal 2 loopt een **gang** (assen 8–9/10) van Zaal 1 naar de chill. Er staat een wenteltrap.
    - 0.32-1 **Chill-zaal**, 382 m² (zuidstrook, assen 8–21, G–K), met een stellingvloer erboven.
    - 0.32-1 **Entree** en 0.32-2 **Garderobe** (assen 21–23). De deur gaat naar de binnenplaats.
    - 0.28-1/0.28-2 **Sanitair** (2 × 91,5 m²) en 0.29 **EHBO** langs de zuidmuur.
    - De **binnenplaats** (assen 23–27, G–L) heet 'opstelplaats ambulance', met twee poorten in de oostgevel aan de
      Elementenstraat. Volgens de BAG en de luchtfoto is dit buitenterrein van 15 × 20 m. Dat klopt op de meter met
      de inham in het BAG-pand.
    - 0.22-1 **Back stage** (300 m²) en 0.22-4 **vluchtroute** langs de noordgevel. De westband is de toegang voor
      studio's en kantoren vanaf de Isolatorweg (trappenhuizen, toiletblok). Het zuidwestblok heet 0.30 'ateliers'.
  - p. 10–11 (tekst): 'Van de aan de Elementenstraat grenzende ruimte zal ca. 2000 m² gebruikt worden voor …
    (publieks)evenementen. De ingang van deze locatie bevindt zich dan ook aan de Elementenstraat 25.' Kantoren,
    studio's en kantine zijn bereikbaar vanaf de Isolatorweg. Dat bevestigt de oriëntatie.
  - p. 35 'Parkeersituatie' (situatietekening met de entree aan de Elementenstraat), opgeslagen als
    `.../diep/the-element-p35-parkeersituatie.jpeg`.
- Bijlage 15 (zienswijzen, 40 p.) bevat de zienswijze van de initiatiefnemer en het businessplan 'Plan voor
  Isolatorweg 36/Elementenstraat 25'. Er staat geen tekening in.
- Andere plannen op het punt (Datacenters 2023/2026, Grondwaterneutrale kelders, provinciale verordening,
  geluidzone Westpoort) hebben geen pand-specifieke bijlagen.
- **Omgevingswet / omgevingsplan:** geen pand-specifieke omgevingsplanwijziging gevonden (de planlijst bevat alleen
  paraplu-plannen).

**Officielebekendmakingen** (SRU-zoekdienst repository.overheid.nl op 'Elementenstraat', 'Isolatorweg',
'Nachtlab', 'Warehouse Elementenstraat'):
- Exploitatievergunning horeca voor **'Nachtlab / Warehouse'**, Elementenstraat 25, soort 'alcohol verstrekkend
  bedrijf – nachtzaak', inrichting 'Zalenverhuur', geen terras:
  - aanvraag verlenging 10-02-2023, kenmerk Z/23/2129016 (gmb-2023-79919), verleend 10-07-2023 (gmb-2023-313648);
  - **wijziging** verleend 06-11-2024, kenmerk Z/24/2826672 (gmb-2024-472409);
  - aanvraag verlenging 21-11-2025, kenmerk Z/25/3050496 (gmb-2025-522228), **verleend 01-04-2026**
    (gmb-2026-188061 en gmb-2026-184895): https://zoek.officielebekendmakingen.nl/gmb-2026-188061.html
  - Elke publicatie zegt: 'U kunt bij de gemeente Amsterdam de documenten met informatie over de vergunning
    opvragen' via Vergunningenhoreca.west@amsterdam.nl, met straat, huisnummer en kenmerk. **Dit is de beste
    resterende route** (zie de conclusie).
- Omgevingsvergunning Z2024-012827 (aanvraag 23-05-2024, verleend 02-10-2024): alleen een Heineken-reclamebord op de
  gevel (gmb-2024-260485, -393238, -422630, -422606). Geen indeling.
- APV-vergunning voor het reserveren van parkeervakken, 9–11 januari 2023 (gmb-2022-528713). Geen indeling.
- Er zijn geen bekendmakingen van de verbouwingen 2013–2014 en 2016 of de bouw van AMAZE (2021) gevonden. Vóór 2015
  werden vergunningen in Westpoort niet in deze vorm gepubliceerd.
- Isolatorweg 36: geen hits.

## 2. Eerder openbaar gemaakte stukken (Woo/Wob, raadsinformatie)

**Gezocht:** open.overheid.nl (API `openbaarmakingen/api/v0/zoek`) op Elementenstraat, Nachtlab, Warehouse
Elementenstraat en Isolatorweg 36. Open Raadsinformatie Amsterdam (api.openraadsinformatie.nl) op 'Elementenstraat'
(101 treffers) en op recente stukken (2018 en later).

**Gevonden (geen van deze laat de indeling zien):**
- Raadsstukken bestemmingsplan Sloterdijk I (19 juni en 3 juli 2013): nota van beantwoording zienswijzen. 'Het pand …
  is gedeeltelijk leeg komen te staan … na faillissement van de laatste huurder.' De vraag was 2.000 m² horeca II
  plus een 24-uursvergunning. Daarnaast de raadsvoordracht en het raadsbesluit 556 (aanduiding 'horeca').
  https://api.notubiz.nl/document/717269/1
- 'Voortgangsrapportage Aanpak Leegstand Kantoren oktober 2013': 'De voormalige bedrijfshal (7.000 m²) wordt
  omgebouwd tot nachtlab/broedplaats en een gedeelte club. De verwachte opening is op 1 januari 2014.'
  https://api.notubiz.nl/document/1011927/1
- 'Beleid horeca en leisure Westpoort' (2014): nachtclub 'the Element', maximaal 3 nachtzaken in Sloterdijk I.
  https://api.notubiz.nl/document/1672703/1
- 'Evaluatie Rapport 24 uurshoreca' (2017–2018): 'The Warehouse Elementenstraat (onderdeel van Nachtlab)' kreeg in
  de vierde ronde (2016) positief advies voor een 24-uursvergunning. https://api.notubiz.nl/document/5938280/1
- Nachtvisie 2021 (de Warehouse genoemd als vrijplaats) en inspraakreacties op het Integraal Raamwerk Haven-Stad
  (2022, zorg dat 'de Elementenstraat' verdwijnt). https://api.notubiz.nl/document/11021672/1
- open.overheid.nl: alleen het 'Evaluatierapport Project Party Safely-2 2018-2019' (noemt de venue) en
  irrelevante treffers op Isolatorweg 36 (metro, MIRT).
- **Haven-Stad:** in de raadsstukken zijn geen plannen met een pandtekening gevonden. Het pand ligt in de
  transformatiezone Sloterdijk I. De 'Strategienota Sloterdijk I' (2016) heeft alleen kaarten met eigendom en
  milieucontouren.

## 3. Rechtspraak

**Gezocht:** uitspraken.rechtspraak.nl (zoek-API van de site) op 'Elementenstraat', 'Isolatorweg 36', 'Nachtlab',
'Warehouse Elementenstraat'. Raad van State: zoekpagina op Elementenstraat, Nachtlab, Isolatorweg 36.

**Gevonden:**
- ECLI:NL:RBAMS:2020:81 (Rechtbank Amsterdam, 10-01-2020, een casino-zaak). Die noemt alleen dat 'Nachtlab,
  Isolatorweg 36' in 2016 werd voorgedragen voor een 24-uursvergunning. Geen indeling.
- ECLI:NL:GHAMS:2019:1394 (energiecontract): niet relevant.
- Raad van State: 0 uitspraken.

## 4. Academisch

**Gezocht:** één WebSearch op scripties en theses over Elementenstraat (nachtclub, crowd management, akoestiek,
herbestemming). Verder UvA Scripties en HBO Kennisbank (geen treffer in de html; de resultaten worden mogelijk pas in
de browser geladen). TU Delft Repository was vanaf hier niet bereikbaar (geen verbinding).
**Gevonden:** niets.

## 5. Bouw en vastgoed

- **Ontwerper van de tekening 2013:** MSTRS advies&ontwerp (zo staat het in het titelblok). Een WebSearch vond geen
  site of projectpagina.
- **Ruimtelijke onderbouwing:** Oranjewoud (nu Antea Group), projectnr. 257993, 17-04-2013, opdrachtgever Island
  Peak BV (Blaricum). De bijlage 'Beschrijving Nachtlab' is ondertekend door Bas Engels (directeur Stichting
  Nachtlab) en Henk van der Lely (initiatiefnemer), 18-03-2013.
- **AMAZE (ID&T, sinds 2021):** geen architect, ontwerpbureau of 'Moment Factory' gevonden (twee WebSearches).
  AMAZE's eigen site noemt de club als verhuurproduct:
  - https://www.amaze-amsterdam.com/the-club: 'Host your event at Warehouse Elementenstraat … **3 available stage
    areas** … 24-hour permit … **Available space 1.500 m2 – Capacity up to 2.500**.' Foto's gedownload naar
    `.../diep/fotos-amaze-site/`.
  - https://www.amaze-amsterdam.com/event-venue: 'Modular layout options', 'Capacity 50 – 1.500', '1.500 m2'.
  - De experience zelf: 7 à 8 kamers op 'ruim 3.000 m²', met lounge en bar. **Welk deel van het pand AMAZE gebruikt,
    staat nergens.**
- **Verhuurbrochures en locatieplatforms:** niets voor nr. 25. De Funda-in-business-brochure 'The Element,
  Elementenstraat 14-B' gaat over een ander pand aan de overkant. followthebeat.nl geeft 403 (botblokkade, niet
  omzeild).
- Geen monument.

## 6. Bouwdossiers Stadsarchief (alleen vindplaats, scans niet geopend)

Bron: openbare metadata-API `https://bouwdossiers.amsterdam.nl/iiif-metadata/bouwdossier/?pand=0363100012128444`.
De metadata staan in `.../diep/bouwdossiers-metadata.json`. Er zijn 19 dossiers, alle uit 1961–1988 (industriële
periode), vrijwel alle 'PUBLIC':

| dossier | jaar | soort | adres | stukken |
|---|---|---|---|---|
| SJ_58766 | 1962 | oprichting | Isolatorweg 36 | 29 (o.a. tekeningen, constructie, brandweeradvies) |
| SJ_58770, SJ_58772, SJ_58777 | 1961–62 | deelgoedkeuring | Isolatorweg 36 | 3–5 |
| SJ_58763, XY_01213 | 1962 | adresbeschikking | Isolatorweg 36 | 1 |
| SJ_58816 | 1970 | verbouwing | Isolatorweg 36 | 19 |
| SJ_58751 | 1971 | verbouwing | Isolatorweg 36 | 14 |
| SJ_58822 | 1971 | deelgoedkeuring | Isolatorweg 36 | 4 |
| SJ_58830 | 1972 | verbouwing | Isolatorweg 36 | 14 |
| SJ_58832 | 1972 | deelgoedkeuring | Isolatorweg 36 | 4 |
| SJ_58833 | 1974 | verbouwing | Isolatorweg 36 | 23 |
| XY_01072, SJ_58869 | 1977 | adresbeschikking | Elementenstraat 25 | 1 |
| SJ_58857 | 1978 | verbouwing | Isolatorweg 36 | 31 (8 tekeningen + 11 revisietekeningen) |
| SJ_58841 | 1978 | verbouwing | Isolatorweg 36 | 15 (8 tekeningen, brandweer, welstand) |
| SJ_58868, SJ_58873 | 1987 | deelgoedkeuring | Elementenstraat 25; Isolatorweg 36 | 8 / 6 |
| SJ_58874 | 1988 | revisie | Elementenstraat 25; Isolatorweg 36 | 16 (11 tekeningen, 1 document 'restricted') |

Joris kan ze zelf bekijken via data.amsterdam.nl / bouwdossiers.amsterdam.nl (dossiernummer). Ze laten alleen de
fabriek zien (casco, kolommen, gevels). Daarmee zijn ze nuttig voor de stramienmaat, niet voor de clubindeling. **Er
staat geen dossier van na 1988 in het archief.** De verbouwing 2013–2014 (GZG/Studio 80, opening 25-04-2014), de
uitbreiding rond 2016 en de bouw van AMAZE (2021) zitten er niet in.

## 7. Webarchieven

**Gezocht:** Wayback CDX van elementenstraat.nl (alle paden, uploads) en het oude AMAZE-domein amaze.dma.nl. Bij
het laatste kwam een 429-blokkade van de Wayback Machine; daarna gestopt.
**Gevonden:**
- **elementenstraat.nl/warehouse/ (april 2014):** 'GZG en Studio 80 … Studio 80 gaf er tijdens ADE 2013 vijf
  avonden … Een half jaar en een verbouwing verder wordt … op vrijdag 25 april 2014 de locatie officieel geopend …
  vaste toiletten, kluisjes en een ventilatiesysteem … **de ruimste rookruimte van Amsterdam met uitzicht op de grote
  zaal** … biedt met **twee zalen** ruimte aan circa 2500 man. In de grote zaal passen 2000 man en in de kleine 500.'
  https://web.archive.org/web/2014/http://www.elementenstraat.nl/warehouse/
- elementenstraat.nl/history/ en /contact/ (2020): 'modular, multi-roomed interior – tailored to suit every event'.
  Geen plattegrond.
- In de uploads van 2013–2020 staan alleen foto's, logo's en `huisregels-E25.pdf`. Geen kaart of plattegrond.
- Huidige site (2026): /about ('stripped back and rebuilt into a modular concrete maze with multiple rooms …
  capacity of 3000'; de huisregels verwijzen naar 'AMAZE Amsterdam'), /terms-conditions ('No smoking inside the
  venue (designated areas only)', lockers, 'No re-entry'), /events (events tot en met november 2026, dus de club is
  actief). In /gallery staan 25 foto's van Intercell Indoor 2024, opgeslagen in `.../diep/fotos-gallery/`. Er is geen
  verhuur- of tech-pagina.

## 8. Event- en productiemateriaal

- Partyflock: aparte locaties 'Warehouse Elementenstraat' en 'Amaze' (beide Elementenstraat 25). Dezelfde
  ADE-nachten staan onder beide namen. Event-pagina's (240KM/H, Intercell, Housequake) noemen geen zalen en hebben
  geen kaart.
- RA/ADE-venuepagina: geen kaart. Bekende zaalnamen per event: Intercell 'Core/Vortex/Nano', Reaktor 'Room 1/Room
  2', HYTE 'room two'.
- Er is geen festival- of venuekaart gevonden (twee WebSearches op Reaktor/Katharsis/Intercell + map).

## 9. Media

- amsterdamnow (artikel over AMAZE): na de experience terug in de 'reception area/bar' en buiten 'at a canopy with
  long benches'. Dat past bij de binnenplaats. 'Warehouse Elementenstraat: from illegal raves to 3,000 people':
  'gutted and converted into a modular concrete maze', 'each space is configurable'.
- iamsterdam: 'vier zalen, ca. 2.500'.
- Foto's (AMAZE-site en gallery): hallen met vierkante betonkolommen en lage stalen liggers, onder meer een lange hal
  met kolommen aan weerszijden en een hal met één kolom midden op de vloer. Dat past bij de kolommenrijen op de
  tekening, maar geen foto is aan een zaal toe te wijzen.

---

## Conclusie

**Is er nu een bruikbare plattegrond? Ja, met beperkingen.** De MSTRS-tekening van 08-03-2013 (bijlage bij
bestemmingsplan Sloterdijk I) is de enige echte plattegrond die openbaar is. Hij klopt maatvast met het BAG-pand en
de binnenplaats. Hij laat zien hoe de zalen liggen: Zaal 1 in het noorden, Zaal 2 en 3 in de middenstrook met de gang
ertussen, en chill, entree, garderobe en toiletten in het zuiden bij de binnenplaats aan de Elementenstraat. De drie
zalen samen (835 + 368 + 217 ≈ 1.420 m²) passen bij wat AMAZE nu over de club zegt: 3 stage areas, 1.500 m², tot 2.500
bezoekers. Opnieuw getekend als één overzichtszaal in `data/batches/precisie-11-warehouse-elementenstraat.json`,
gecontroleerd naast de bron in `_preview/warehouse-elementenstraat-bron-naast-preview.png`.

Beperkingen:
1. Het is een *voorstel* van vóór de verbouwing. Bij de opening in 2014 sprak de club over twee zalen (2000 + 500) en
   een rookruimte met zicht op de grote zaal. Wat daarna in 2016 en 2021 is veranderd, is niet gedocumenteerd.
2. AMAZE (ID&T) zit sinds 2021 in hetzelfde pand, op een onbekend deel.
3. DJ-plekken, bars en de rookplek staan niet (leesbaar) op de tekening. Daarom staan ze niet in de app-tekening.

**Beste volgende stap (voor Joris zelf):** vraag de stukken op bij de **exploitatievergunning horeca 'Nachtlab /
Warehouse', Elementenstraat 25**. De publicatie nodigt daar zelf toe uit: Vergunningenhoreca.west@amsterdam.nl,
met straat, huisnummer en kenmerk.
- **Z/25/3050496** (verlenging, verleend 01-04-2026) en vooral **Z/24/2826672** (*wijziging*, verleend 06-11-2024).
  Een wijziging van een exploitatievergunning gaat vaak over de inrichting. Bij een Amsterdamse exploitatieaanvraag
  hoort een plattegrond van de horecaruimte(n).
- Een Woo-verzoek bij stadsdeel West / VTH is de reserveroute, voor de omgevingsvergunning brandveilig gebruik of
  gebruiksmelding van 2013–2014 (opening 25-04-2014), de wijziging rond 2016 (24-uursvergunning) en de bouw of
  gebruiksmelding van AMAZE (2021). Daarin zitten de actuele vluchtweg- en ontruimingsplattegronden.

De bouwdossiers in het Stadsarchief (SJ_58766 t/m SJ_58874, 1961–1988) laten alleen de fabriek zien.

*WebSearch-gebruik: 13 calls.*
