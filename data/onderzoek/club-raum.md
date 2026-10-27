# Club RAUM: diepteonderzoek indeling

- **id:** club-raum
- **Adres:** Humberweg 3, 1043 AC Amsterdam. Nevenadres Basisweg 35, 1043 AN. Het is hetzelfde verblijfsobject: VBO 0363010000578093, pand 0363100012134632.
- **Datum onderzoek:** 27-10-2026
- **Uitkomst:** **geen echte plattegrond gevonden.** Daarom is er geen `precisie-11-club-raum.json`.
- **WebSearch gebruikt:** 12 calls. De rest liep via curl en WebFetch op concrete vindplaatsen en open API's (SRU officielebekendmakingen, Open Raadsinformatie, PDOK, 3D BAG, Woo-index, TenderNed en bouwdossiers-metadata).
- **Downloads:** `data/sources/club-raum/diep/` (zie onderaan)

## Kern in vijf regels

1. Er is nergens een openbare plattegrond, vluchtwegplan, rider of tekening van de huidige club te vinden.
2. De beste openbare bron over de indeling is de **verhuurdeck "RENTALS 2026"** van de club zelf (Google Slides, gelinkt op clubraum.nl/contact). Die geeft de zalen met vloeroppervlak en capaciteit, maar geen plattegrond.
3. Het **architectenbureau Bram van Grinsven** (samen met Joaquin Valdes) heeft een projectpagina met het ontwerpprincipe en 10 foto's, maar ook daar staat geen plattegrond.
4. Uit **3D BAG** blijkt dat alleen het noordwestelijke voorblok (ca. 26 × 17 m) twee bouwlagen heeft, met het dak op ca. 7,0 m. De rest (ca. 2030 m²) is één hal met het dak op ca. 5,1 tot 5,5 m. De Studio (boven) moet dus in dat voorblok liggen. Dat klopt met de huidige tekening.
5. De echte tekeningen bestaan wel, bij de gemeente: omgevingsvergunning Z2022-NW002985 / OLO 7114215 (evenementenruimte, 2022-23) en **Z2024-023654 / DSO 2024081300744 (aanpassen brandcompartimentering, verleend 03-09-2024)**. De Gemeenteblad-publicaties zeggen letterlijk dat je "het besluit en bijbehorende stukken per e-mail kunt ontvangen". Dat is de beste volgende stap (zie Conclusie).

---

## Route 1: overheid, ruimtelijke ordening

### officielebekendmakingen.nl (SRU-API repository.overheid.nl)

**Gezocht:** "Humberweg" (122 records, gefilterd op Amsterdam), "Basisweg 35" (10), "Club Raum" (11) en "Basisweg" + Amsterdam (330, gefilterd).

**Gevonden voor dit adres:**

| Datum publ. | Soort | Kenmerk | Inhoud |
|---|---|---|---|
| 21-09-2022 | Aanvraag omgevingsvergunning Basisweg 35 | Z2022-NW002985, OLO 7114215 | "Afwijken van het bestemmingsplan voor het realiseren van een evenementenruimte" (aanvrager Temporary Palaces). [gmb-2022-422008](https://zoek.officielebekendmakingen.nl/gmb-2022-422008.html) |
| 16-02-2023 | Besluit: geweigerd | idem | [gmb-2023-70376](https://zoek.officielebekendmakingen.nl/gmb-2023-70376.html) |
| 22-02-2023 | Rectificatie: **van rechtswege verleend, 5 jaar** (verzonden 20-02-2023) | idem | [gmb-2023-79381](https://zoek.officielebekendmakingen.nl/gmb-2023-79381.html) |
| 19-09-2023 | Aanvraag exploitatievergunning, "Soort inrichting: nachtclub" | Z/23/2209186 | [gmb-2023-402097](https://zoek.officielebekendmakingen.nl/gmb-2023-402097.html) |
| 24-10-2023 | Evenementenvergunning ADE geweigerd (650 bezoekers op drukste moment) | Z/23/2236055 | [gmb-2023-452538](https://zoek.officielebekendmakingen.nl/gmb-2023-452538.html) |
| 23-11-2023 / 05-04-2024 | Alcoholwetvergunning aanvraag / verleend | Z/23/2210687 | gmb-2023-499660, [gmb-2024-149137](https://zoek.officielebekendmakingen.nl/gmb-2024-149137.html) |
| 24-11-2023 | Verkeersbesluit: 13 autovakken Basisweg 35 en Humberweg in het weekend fietsparkeren. Er staan 3 situatietekeningen bij (alleen straatniveau) | | [gmb-2023-503367](https://zoek.officielebekendmakingen.nl/gmb-2023-503367.html) |
| 12-04-2024 | Exploitatievergunning verleend: nachtzaak, vr+za 9.00 tot 8.00, zo 9.00 tot 6.00, geen terras | Z/23/2209186 | [gmb-2024-161339](https://zoek.officielebekendmakingen.nl/gmb-2024-161339.html) |
| 15-05-2024 | Aanvraag omgevingsvergunning "wijzigen van de brandcompartimentering in het pand van Club Raum" | Z2024-010662, DSO 2024050301174 | [gmb-2024-212030](https://zoek.officielebekendmakingen.nl/gmb-2024-212030.html) |
| 05-09-2024 / 06-09-2024 | Aanvraag en **besluit verleend: "aanpassen van de brandcompartimentering"** (verzonden 03-09-2024) | **Z2024-023654, DSO 2024081300744** | gmb-2024-381074, [gmb-2024-381388](https://zoek.officielebekendmakingen.nl/gmb-2024-381388.html) |
| 2024 tot 2025 | Ontheffingen geluid/openingstijden (19-10-2024 ADE; 14-12-2024; 19 en 20-04-2025; 31-05 t/m 25-10-2025) | Z/24/2417727, Z/24/2837013, Z/25/2879598, Z/25/2944508 | gmb-2024-332720, gmb-2024-447945, gmb-2025-64994, gmb-2025-229756 |
| 2025 tot 2026 | APV-meldingen "ter hoogte van nr. 3" (TVM, filmmelding, objectvergunning) | | geen informatie over de indeling |

**Laat het de indeling zien?** Nee. Het zijn alleen kennisgevingen. Twee punten zijn wel belangrijk:
(a) Elke publicatie zegt: *"Het besluit en bijbehorende stukken kunt u per e-mail ontvangen. Stuur een verzoek naar vthsdnw@amsterdam.nl en vermeld daarin straatnaam, huisnummer en Zaak- en OLO/DSO-nummer."*
(b) Bij een omgevingsvergunning voor brandcompartimentering horen altijd plattegronden met compartimentsgrenzen en vluchtwegen. Dat is de huidige indeling (stand 2024, dus van vóór Nexus).

Er is **geen** omgevingsvergunning voor de verbouwing naar Nexus (2025-26) gepubliceerd. Die verbouwing was waarschijnlijk vergunningvrij, met een (gewijzigde) melding brandveilig gebruik. Zo'n melding wordt niet gepubliceerd.

**24-uursvergunning:** voor Humberweg 3 is geen 24-uursvergunning gepubliceerd. De exploitatievergunning staat al bijna 24 uur toe (vr+za 9.00 tot 8.00). RAUM 24HRS (Koningsdag 2026) liep vermoedelijk via een ontheffing. Volgens de gemeentelijke verkenning "Agent of Change" (nov. 2025) verdwijnt de 24-uursvergunning onder het nieuwe horecabeleid.

### ruimtelijkeplannen.nl (via PDOK WMS GetFeatureInfo op RD 117142, 489421)

- **Bestemmingsplan "Sloterdijk II"** (NL.IMRO.0363.B1103BPGST-VG02, vastgesteld 03-07-2013): bestemming Bedrijf, t/m categorie 3.2. Het plan dateert van vóór de club en heeft geen tekening van het pand.
  - **Bijlage 1 Inventarisatie plangebied (feb. 2013)**, [tb1.pdf](https://ruimtelijkeplannen.nl/documents/NL.IMRO.0363.B1103BPGST-VG02/b_NL.IMRO.0363.B1103BPGST-VG02_tb1.pdf): *Basisweg 33-35, **Kloosterman, Boekbinderij**, kavel 2500 m², bebouwd 2500 m², bvo 2925 m², 27 werkzame personen.* Dat is de oude naam van het gebouw.
- **"Geluidverdeelplan Westpoort 2e herziening"** (NL.IMRO.0363.B2302BPGST-OW01, ontwerp 08-11-2023). De initiatiefnemer diende hierop een zienswijze in "aangaande locatie Basisweg 35/Humberweg 3" (feitenrelaas). In de toelichting en de 9 bijlagen staat niets over Club Raum, alleen geluidkavels. Er is geen tekening.
- Ook gevonden: Grondwaterneutrale Kelders, Darkstores, Datacenters (paraplu). Er is **geen besluitgebied of projectbesluit** op het adres. De afwijking uit 2023 was een reguliere procedure (kruimelgeval, tijdelijk) en heeft daarom geen ruimtelijke onderbouwing op ruimtelijkeplannen.nl.

### Omgevingswet / omgevingsplan

Er is geen omgevingsplanwijziging voor dit adres gepubliceerd. De DSO "Regels op de kaart" geeft geen vergunningstukken, en de DSO-API's vragen een sleutel. Aanvraagstukken uit het Omgevingsloket zijn niet openbaar.

### Plannen voor het gebied (Sloterdijk / Haven-Stad)

- **Investeringsnota Sloterdijk 2 Zuid "Van stadsrand naar stadsentree"** (okt. 2020, raadsbesluit 1547/2020), [notubiz 9525667](https://api.notubiz.nl/document/9525667/1). Basisweg 35 valt in dit transformatiegebied. Figuur 19 is een foto van de **gevel van Basisweg 35**: twee lagen met lintramen in metselwerk. Er staat geen interieur in.
- In de bijlagen L (Bodemkwaliteit) en N (Stikstof) komt Basisweg 35 voor. Bodem: Fugro-onderzoek 31-03-1999, H-8154/110, "pot. ernstig en urgent". Stikstof (2020): "Basisweg 35 en Humberweg 3, 2.500 m², organisatie-adviesbureaus". Ook hier geen indeling.
- Gebiedsvisie Synergie Sloterdijk-West (2019) en de haalbaarheidsstudie "tijdelijke nachtcultuur Basisweg 35 en Donauweg 11" (collegebesluit 13-06-2023) worden in het feitenrelaas genoemd. Ze zijn niet openbaar gevonden.
- **Context:** de vergunning is tijdelijk: 5 jaar vanaf 20-02-2023, dus tot ca. februari 2028.

## Route 2: Woo en raadsinformatie

**Gezocht:** Open Raadsinformatie (api.openraadsinformatie.nl, index ori_amsterdam*) op "Club Raum", "Humberweg", "Basisweg 35", "SPIELRAUM", "24-uursvergunning Raum", "Raum isolatie" en "Raum Westerveld". Daarnaast open.overheid.nl (Woo-index API) op "Club Raum", "Basisweg 35" en "Temporary Palaces".

**Gevonden (gedownload naar diep/):**

- **Feitenrelaas vergunningverlening Club Raum** (Van de Bunt Adviseurs, 22-03-2024, 58 p.), [notubiz 15538794](https://api.notubiz.nl/document/15538794/1) (ook als bijlage 2 bij de RIB van 2024: [13976839](https://api.notubiz.nl/document/13976839/1)). Er staan geen tekeningen in, maar het **noemt alle onderliggende stukken**:
  - *Akoestisch Rapport V1 Basisweg 35* (20-04-2023, opdracht initiatiefnemer); *V2 door Westerveld Advies* (12-08-2023); bijgewerkt 14-09-2023; *aangepast akoestisch rapport* 11-10-2023 (v4, gedeeld met Havenbedrijf 13-10-2023); *V5 maatregelstudie* (Westerveld, concept 22-12-2023); *V6* (Westerveld in opdracht van de gemeente, 26-01-2024). Westerveld rapporten bevatten doorgaans bronposities per zaal en het gebouw.
  - *Rapport Externe Veiligheid Basisweg 35* van LBP Sight (06-06-2023).
  - *Melding/gebruiksmelding brandveilig gebruik*: positief brandweeradvies 18-10-2023. Overleg 02-02-2024 over "BMI, OAI, extra vluchtmogelijkheid en verzamelplaats, **capaciteit verdiepingen**". Het verslag van 05-02-2024 geldt als advies brandveiligheid.
  - *Concept maatwerkvoorschrift geluid* (20-10-2023), *Mobiliteitsplan Club Raum* (22-11-2023), *Tekening fietsparkeren* (Ingenieursbureau, 16-11-2023), *veiligheidsplan* (okt. 2023), *conceptplan* Temporary Palaces (01-02-2023).
  - Maatregelen genoemd op 27-11-2023: "dakisolatie, het niet gelijktijdig gebruiken van ruimtes, volume lage tonen aanpassen".
  - Initiatiefnemers zijn **Temporary Palaces** (huurder/ontwikkelaar van het pand) en Spielraum.
- **Evaluatie Club Raum: inzichten en lessen** (02-12-2024), [15538793](https://api.notubiz.nl/document/15538793/1), plus de **RIB Evaluatie** (2025), [15538792](https://api.notubiz.nl/document/15538792/1). Gaat alleen over het proces.
- **RIB Club Raum 26-03-2024** ([13976838](https://api.notubiz.nl/document/13976838/1)), voordrachten RO ([13976837](https://api.notubiz.nl/document/13976837/1), [15538791](https://api.notubiz.nl/document/15538791/1)). Het college stond gebruik toe "gedurende de uitvoering van de noodzakelijke isolatiewerkzaamheden in het pand".
- **Beantwoording schriftelijke vragen** ([14005936](https://api.notubiz.nl/document/14005936/1)): de aanvraag ging over *"een evenementenruimte/nachtzaak van 1.500 m² (1.500 personen) op de locatie Basisweg 35"*. Verder: beantwoording raadsadres ([14005935](https://api.notubiz.nl/document/14005935/1)), raadsadres 2023 ([13420360](https://api.notubiz.nl/document/13420360/1)) en RIB afdoening ([14005937](https://api.notubiz.nl/document/14005937/1)).
- **Stadsdeelcommissie Nieuw-West 21-11-2023**, agendapunt "Bespreking Basisweg 35" (agenda [13504645](https://api.notubiz.nl/document/13504645/2), afsprakenlijst [13569022](https://api.notubiz.nl/document/13569022/2)). Alleen een mondelinge toelichting.
- Voortgangsrapportage Nachtcultuur (2026) en AFK-jaarverslag 2024: Club RAUM heeft de eerste "nachtbroedplaats" (2025) en AFK-subsidies (artist in residency € 50.000; Club RAUM € 20.000). Er staat geen indeling in.
- **open.overheid.nl:** geen Woo-besluiten over Club Raum of Basisweg 35. Het Woo-verzoek dat de initiatiefnemer op 18-10-2023 indiende (over de ADE-weigering) is niet gepubliceerd gevonden.

**Laat het de indeling zien?** Nee, maar het feitenrelaas is de beste inventaris van de documenten die de indeling wél bevatten.

## Route 3: rechtspraak

- **Raad van State** (zoeken op raadvanstate.nl): "Club Raum" en "Temporary Palaces" geven 0 hits. "Basisweg" geeft 2 hits die er niets mee te maken hebben (Gatwickstraat 1; planschade Beverwijk).
- **rechtspraak.nl:** de open-data-API heeft geen full-text zoekfunctie. Een WebSearch op "Basisweg 35" / "Club Raum" / Havenbedrijf / nachtclub leverde geen uitspraak op.
- Dat ligt voor de hand: het bezwaar van Havenbedrijf en Meesters Advocaten liep via de bezwaarschriftencommissie. Rhone Events trok het bezwaar op 06-06-2023 in.
- **Indeling:** nee.

## Route 4: academisch

Een WebSearch op scriptie/thesis + Club Raum gaf niets. Er is ook geen vakpers (Frame, Dezeen, ArchDaily, Architectenweb, de Architect) gevonden: een WebSearch met de namen van de ontwerpers en deze titels leverde alleen muziekpers op. **Indeling:** nee.

## Route 5: bouw en vastgoed

- **Architect: bevestigd.** [bramvangrinsven.com/raum](https://www.bramvangrinsven.com/raum) ("Club Raum interieurontwerp"). Bram van Grinsven, "in samenwerking met Joaquin Valdes", opdrachtgever *Spielraum en Temporary Palaces*, periode 2023-2024, foto's Arjen Roos. Uit de tekst:
  > "Het gebouw uit 1968 kent een eenvoudige structuur van betonnen kolommen en vloeren die een volledig open plan toestaat. Het plan is ontworpen vanuit de routing, waarbij clubbezoekers avontuurlijke routes kunnen maken door het gebouw. Nauwe gangetjes met lounges en darkrooms worden afgewisseld met hoge industriële ruimtes. De toiletgroepen en routes zijn zo ontworpen dat de zalen zowel afzonderlijk als gezamenlijk als club kunnen functioneren. [...] Nieuwe toevoegingen zoals de bars en toiletgroepen zijn opgetrokken uit gemetselde betonblokken en glazen bouwstenen."

  De pagina heeft 10 foto's: interieur, glazen-bouwsteenbar, Arena-podium, toiletgang, buitengevel met schoorsteen, toegangsdeur. Er staat **geen plattegrond** op, ook niet in de Squarespace-JSON. Voor Joaquin Valdes is geen eigen site gevonden.
- **Nexus (2026):** ook Valdes en Van Grinsven, met Ben Kreukniet en Albert van Abbe (licht), en Chrissie Quast (akoestiek, Funktion-One). Het idee is de plattegrond van een kathedraal: "the booth becomes the altar. Around it, corridors wind off and connect different parts of the dancefloor", "Downstairs, Nexus" ([clubraum.nl/news](https://www.clubraum.nl/news/the-official-opening-of-our-new-room)). Nexus heeft een eigen bar en toiletten "connected by passageways and alleyways" ([ADE](https://www.amsterdam-dance-event.nl/en/news/30-years-ade-iconic-venues-club-raum-and-its-ever-evolving-community/2832422/)).
- **Temporary Palaces** (temporarypalaces.nl, WP-API doorzocht op basisweg/raum/spielraum/sloterdijk): geen pagina voor Basisweg 35. Hun "Studio Sloterdijk" is Kabelweg 22-24, dus een ander pand.
- **Vastgoedbrochures:** Funda in Business heeft niets voor Basisweg 33/35, alleen buurpanden (Basisweg 34, 61). Over Boekbinderij Kloosterman is online niets gevonden (geen site of veiling).
- **TenderNed** (publicatie-API, search=): "Club Raum" 0 hits, "Basisweg" alleen niet-gerelateerde hits. De onderzoeken van Westerveld Advies waren onderhandse opdrachten.
- **Monument:** niet van toepassing (bedrijfspand uit 1968-69).
- **Indeling:** nee, alleen een beschrijving.

## Route 6: bouwdossiers Stadsarchief (alleen metadata; geen toegang gevraagd en geen scans geopend)

Bron: `https://bouwdossiers.amsterdam.nl/iiif-metadata/bouwdossier/?pand=0363100012134632` (publieke metadata). Er zijn 23 dossiers aan het pand gekoppeld. Voor het clubpand gaat het om de dossiers met het adres **Basisweg 35**:

| Dossier | Datum | Type | BWT-nr. | Inhoud (subdossiers) | Status |
|---|---|---|---|---|---|
| **SQ_19685** | 1968 | oprichting | 51231/00/5806/1968 | aanvraag, 2× tekeningen, 2× **revisietekeningen**, berekeningen, adviezen brandweer/welstand | PUBLIC |
| SQ_21871 / 21873 / 21876 | sep-nov 1968 | deelgoedkeuring | idem | deelgoedkeuringstekeningen (1+1+3), berekeningen (56 bestanden) | PUBLIC |
| SQ_19686 / 19687 | 1969 / 1972 | reclame | | | PUBLIC |
| SQ_19684 / XY_01743 | 1969 | adresbeschikking | | | PUBLIC |
| SQ_19690 | 1971 | verbouwing | 51231/00/7855/1970 | 1 tekening, adviezen | PUBLIC |
| **SQ_19688** | 1987 | **verbouwing** | 51231/01/8380/1987 | **10 tekeningen**, berekeningen (47), adviezen | PUBLIC (1 aanvraagstuk RESTRICTED) |
| SQ_19689 | 1988 | verbouwing | 51231/01/9728/1988 | 2 tekeningen, berekeningen (7) | PUBLIC (1 aanvraagstuk RESTRICTED) |

De dossiers **SQ_17376 tot 17386 en XY_00598** (2002-2005, "Humberweg 3 - 7; Rhôneweg 12 - 14", Bijeenkomstfunctie) komen alleen in de lijst door de huisnummerreeks. Ze gaan vrijwel zeker over het buurpand op de hoek Rhôneweg/Humberweg (het partycentrum, nu H7 Warehouse, pand 0363100012145742), niet over de club.

De vergunningen van 2022-2024 (evenementenruimte en brandcompartimentering) zitten **nog niet** in het Stadsarchief. Ze liggen bij VTH Nieuw-West.

**Voor Joris om zelf te bekijken:** via data.amsterdam.nl, adres Basisweg 35, rubriek "Bouwdossiers", dossiers SQ_19685 (casco 1968: kolomraster, trappen, verdieping) en SQ_19688 (verbouwing 1987). Die laten de constructie zien, niet de clubindeling van 2024 of 2026.

## Route 7: webarchieven

- **web.archive.org, CDX clubraum.nl\*:** ca. 2000 URL's (vooral events). De homepage van 2023-09-27 had alleen PDF's met huisregels en code of conduct. De pagina's about, about-the-club, contact (17 versies 2024 tot 2026) en socials hebben geen plattegrond en geen eerdere verhuurdeck. De link naar de verhuurdeck verschijnt pas in de versie van 07-10-2026.
- **temporarypalaces.nl in het archief:** de CDX-API gaf een timeout. De WP-API op de live site gaf niets.
- **Vorige gebruikers** (Boekbinderij Kloosterman; in 2020 een "organisatie-adviesbureau"): geen site gevonden.
- **Indeling:** nee.

## Route 8: event- en productiemateriaal

- **Verhuurdeck "RENTALS 2026"** (publiek gelinkt op [clubraum.nl/contact](https://www.clubraum.nl/contact) → [Google Slides](https://docs.google.com/presentation/d/1kCxdlgbGV8wlhk3-y0PDvA0wGqZydm3Ql9SeGpURO6g/)). Geëxporteerd als PDF naar `diep/partnerships-deck.pdf`. Ook als pptx gecontroleerd: 13 dia's, geen verborgen dia's, 13 afbeeldingen, geen tekening. Inhoud:
  - Totaal **1600 m² vloer, 1500 personen, "five distinct rooms"** (er worden er vier genoemd)
  - **Studio** 345 m², 350-400 p.: "Climb a flight of stairs ... our largest space, complete with **360° dj booth**, Martin Audio, ... iconic, fully equipped **glass brick bar**".
  - **Nexus** 345 m², 350-400 p. Let op: deze dia hergebruikt de foto's en cijfers van de Studio-dia, dus het getal is onbetrouwbaar.
  - **Arena** 101 m², 150-200 p.: "built-in seating all around". Op de foto's: geribbelde glazen (polycarbonaat) wanden, verhoogd podium tegenover een deur.
  - **Boutique** 130 m², 150-200 p.: "**Fully accessible** and conveniently located **next to the restrooms** ... under a dazzling neon star". Op de foto's: betonnen kolommen, lintramen en een podium.
  - Disclaimer op elke dia: *"These images are for internal use only and can't be shared online without permission"*. **De foto's dus niet in de app gebruiken.**
- **Tech rider, stage plot, productiehandboek:** niet gevonden (WebSearch en een scan van alle 37 sitemap-URL's van clubraum.nl op pdf/docs-links). De "Technical specifications"-dia's zijn alleen tekst.
- **Timetable SPIELRAUM 55HRS** (clubraum.nl, al gebruikt in precisie-05): zalen STUDIO, NEXUS, ARENA en bars "Studio bar" en "Expo bar".

## Route 9: media

- **ADE "30 years iconic venues"**: "When Club RAUM opened in 2024, **Studio occupied the upper floor while Expo served as the second dance floor downstairs** ... Expo was relatively compact". Nexus heeft "more volume, greater verticality ... its own bar and toilets, connected by passageways and alleyways".
- **10 Magazine (2025)**: "ground floor's Expo room", "Upstairs in the Studio". Arena is "a third dance floor" en ontstond uit "the second chill-out space", "designed as an amphitheater, flanked by glass walls". Verder: "walkways between dance floors", "gridded glass bars", "a pared-back, concrete cafe space", "red ... locker room and toilet area".
- **AmsterdamNow (20-04-2026)**: "The building has two floors. On the first floor is the main dancefloor, upstairs is the Studio", met de oude nietjes van de boekbinderij in de vloer van de Studio. Ontwerp: "alternatives to narrow corridors, thoughtful routing".
- **Mixmag, RA, DJ Mag, Dazed, GayVillage**: "maze-like corridors", "labyrinthine design". Er is geen video-rondleiding of 360-tour gevonden (fotoverbod binnen).
- **Indeling:** alleen een beschrijving.

---

## Wat we nu zeker weten over de indeling (voor een volgende tekenronde)

| Feit | Bron | Zekerheid |
|---|---|---|
| Pand 49 × 50 m, footprint 2438 m², VBO 2683 m²; boekbinderij bvo 2925 m² (2012) | BAG, inventarisatie Sloterdijk II | hoog |
| Clubdeel ca. 1500 tot 1600 m² (niet het hele pand) | aanvraag 2022, verhuurdeck | hoog |
| **Twee bouwlagen alleen in het NW-voorblok aan de Basisweg, ca. 26 m (oost-west) × 17 m (noord-zuid), dak ca. 7,0 m**. De rest is één laag met dak 5,1 tot 5,5 m | 3D BAG LoD2.2 (dakvlakken 424 m² en 2032 m²) | hoog |
| Studio (345 m², "flight of stairs") ligt boven, dus in dat voorblok. De huidige tekening (25 × 15,5 m linksboven) klopt | 3D BAG, deck, ADE, 10 Mag | hoog |
| Studio: 360°-booth (vrij in de ruimte, niet tegen een wand), bar van glazen bouwstenen | deck | hoog (positie onbekend) |
| Nexus beneden, vervangt Expo; booth als "altaar" met gangen eromheen; eigen bar en wc's | clubraum.nl/news, ADE | hoog (positie in de hal onbekend) |
| Arena 101 m², amfitheater met tribune rondom, glazen wanden | deck, 10 Mag | hoog (positie onbekend) |
| Boutique 130 m², rolstoeltoegankelijk (begane grond), naast de toiletten, betonkolommen | deck | hoog (positie onbekend) |
| Bouwstructuur: betonkolommen en -vloeren (1968), open plan | architect | hoog |
| Toegangsdeur: grijze stalen deur naast een nis met witte geglazuurde steen in de bakstenen gevel | deck + architect | foto; welke gevel is niet zeker |

Ligging van Nexus, Arena, Boutique, lockers, wc's en ingang binnen de hal blijft **onbekend**. De huidige tekening (precisie-05, confidence laag) blijft een schatting. Eén verbetering is wel onderbouwd: de oude notitie "hogere oosthal" uit precisie-05 klopt niet. Volgens 3D BAG is alleen het NW-voorblok hoger. De rest is één hal van ca. 5,3 m.

## Conclusie

**Is er een bruikbare plattegrond? Nee.** Geen openbare bron toont de echte indeling. Wat er is: oppervlakten per zaal (verhuurdeck), de ligging van de Studio (3D BAG plus beschrijvingen) en ontwerpprincipes (architect).

**Beste resterende routes, in volgorde:**

1. **Stukken van de verleende omgevingsvergunning "aanpassen brandcompartimentering"** (Z2024-023654, DSO 2024081300744, verleend 03-09-2024) opvragen bij **vthsdnw@amsterdam.nl**, met zaakadres Basisweg 35, 1043 AN, zaaknummer en DSO-nummer. Dat is precies de route die het Gemeenteblad zelf aanbiedt. Deze stukken bevatten zeker plattegronden met compartimenten en vluchtwegen van de club (stand 2024, met Expo, Studio, Arena, Boutique, wc's en lockers). In dezelfde mail kunnen de stukken van **Z2022-NW002985 / OLO 7114215** mee (evenementenruimte 1.500 m², 2022-23).
2. **Woo-verzoek** aan gemeente Amsterdam (VTH Nieuw-West) voor:
   (a) de *melding brandveilig gebruik* Basisweg 35/Humberweg 3 met plattegronden, plus het brandweeradvies van 18-10-2023 en het verslag van 05-02-2024 ("capaciteit verdiepingen", extra vluchtweg), en een eventuele gewijzigde melding voor Nexus (2026);
   (b) de akoestische rapporten van Westerveld Advies V2 tot en met V6 (2023-24), die meestal een plattegrond met bronposities per zaal hebben.
   Persoonsgegevens en bedrijfsgevoelige stukken zullen worden gelakt, maar plattegronden worden meestal verstrekt.
3. **Stadsarchief** (zelf bekijken, niet via AI): SQ_19685 (1968) en SQ_19688 (1987) voor het kolomraster, de trappen en de verdieping van het voorblok. Daarmee kan de casco-tekening exact, ook als de clubindeling ontbreekt.
4. Alleen als Joris dat zelf wil: de club heeft in de deck aangeboden "further details upon request" (partnerships@clubraum.nl). Ik heb geen contact opgenomen.

## Bestanden in `data/sources/club-raum/diep/`

- `partnerships-deck.pdf`: RENTALS 2026, verhuurdeck van de club (13 p.; foto's "internal use only")
- `ra-feitenrelaas-vergunningverlening-2025.pdf` + `ra-feitenrelaas.txt`: feitenrelaas Van de Bunt (22-03-2024)
- `ra-evaluatie-club-raum-20241202.pdf`, `ra-rib-evaluatie-club-raum-2025.pdf`, `ra-bijlage1-rib-club-raum-20240326.pdf`, `ra-voordracht-ro-20240410.pdf`, `ra-voordracht-ro-20250521.pdf`, `ra-beantwoording-schriftelijke-vragen.pdf`, `ra-beantwoording-raadsadres.pdf`, `ra-raadsadres-club-raum-2023.pdf`, `ra-rib-afdoening-raadsadressen.pdf` (elk met .txt-extract)
- `sdc-nw-agenda-20231121.pdf`, `sdc-nw-afsprakenlijst-20231121.pdf`: stadsdeelcommissie Nieuw-West
- `verkeersbesluit-fietsparkeren-2023-1..3.png`: situatietekeningen bij gmb-2023-503367 (alleen straatniveau)
- `bvg/bvg-raum-01..10.jpg`: projectfoto's van bramvangrinsven.com/raum (Arjen Roos)
