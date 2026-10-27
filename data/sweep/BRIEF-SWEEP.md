# Sweep-controle: staat er echt een plattegrond van deze club in de gevonden documenten?

Een script (`tools/sweep/sweep.py`) heeft voor elke venue automatisch openbare overheidsbronnen doorzocht:
bestemmingsplanbijlagen (ruimtelijkeplannen.nl), bekendmakingen (officielebekendmakingen.nl) en Woo-documenten
(open.overheid.nl). Het heeft pagina's eruit gehaald die mogelijk een plattegrond zijn. Jij beoordeelt die pagina's
met je ogen en tekent de club opnieuw als er een echte indeling op staat.

ROOT = `C:\Users\JorisMerkx\OneDrive - Agyle\Documenten\Hassan RSA\ik-sta-hier`

## Wat je per venue hebt

`ROOT/data/sweep/<id>.json`, met o.a.:
- `kandidaten`: pagina's met tekst als "plattegrond", "begane grond", "indeling" of met tekening-achtige inhoud.
  Elk heeft `png` (render van de pagina), `pdf` (lokaal bestand), `pagina`, `url` (openbare bron) en `bron` (welk
  plan of welke bekendmaking, en waarom gekozen).
- `contactvellen`: PDF's zonder tekstlaag (scans) die bij dit adres horen. `vellen` zijn PNG's met miniaturen van 20
  pagina's, met het paginanummer linksboven.
- `figuren`: URL's van afbeeldingen uit de toelichting van een plan, vlakbij de plek waar het adres genoemd wordt.
- `plannen[].noemingen`: tekstfragmenten waarin het plan het pand noemt (handig voor context, jaar, oude naam).
- `huidig`: wat de app nu heeft (`basis`, `confidence`, aantal zalen). De huidige zalen staan in `data/venues.json`.

## Werkwijze

1. Bekijk elke `kandidaten[].png` en elk contactvel met de Read-tool. Zie je een pagina op een contactvel die een
   plattegrond of bouwtekening lijkt, render die scherp:
   `python -X utf8 tools/sweep/pagina.py <pdf> <pagina> ROOT/data/sources/<id>/sweep/p<pagina>.png 2400`
   (eventueel met een uitsnede, zie de uitleg in het script). Figuren mag je downloaden met curl naar
   `ROOT/data/sources/<id>/sweep/`.
2. Beslis per pagina: staat hier de **binnenindeling van dit pand** (zalen, wanden, bar, podium, trappen, ingangen)?
   Een kaart, luchtfoto, situatietekening van het terrein, verbeelding van het bestemmingsplan of een ander pand telt
   niet. Controleer dat het echt deze club is: adres of naam op de tekening of in de tekst eromheen.
3. Gevonden? Noteer het jaar van de tekening en of die nog klopt met de club van nu (vergelijk met de `note`,
   `source` en zalen in `data/venues.json`; verbouwingen, zalen die erbij of af zijn). Teken de zaal of zalen dan
   opnieuw volgens `ROOT/BRIEF-PRECISIE.md`, secties **Tekenen**, **Controleren** en **Output** (preview naast de
   bron leggen is verplicht). Schrijf het volledige venue-object naar `ROOT/data/batches/precisie-12-<id>.json`
   (JSON-array met één venue), met `basis: "plattegrond"` en:
   - `confidence: "hoog"` als de tekening actueel is en alle zalen van nu dekt;
   - `confidence: "middel"` als hij ouder is dan een bekende verbouwing of maar een deel van de zalen dekt.
   Heeft de venue al `basis: "plattegrond"` met `confidence: "hoog"`, vervang hem dan alleen als jouw document
   duidelijk recenter of vollediger is.
4. Schrijf voor **elke** venue die je kreeg een oordeel naar `ROOT/data/sweep/oordeel/<id>.json`:
   ```json
   {"id": "...", "gevonden": true, "document": "<openbare url>", "pagina": 33, "jaar": 2013,
    "wat": "plattegrond begane grond met 3 zalen, bar, entree", "actueel": "ja|nee|onbekend",
    "zalen_gedekt": ["Zaal 1", "Zaal 2"], "getekend": true, "opmerking": "..."}
   ```
   Niets gevonden: `"gevonden": false` en in `opmerking` kort wat de pagina's wel waren.

## Grenzen

- Open nooit scans van bouwdossiers (bouwdossiers.amsterdam.nl, `iiif`): de voorwaarden van het Stadsarchief
  verbieden AI op die scans. De sweep heeft alleen hun metadata opgehaald; laat die met rust.
- Geen WebSearch. Internet alleen voor de URL's die al in de sweep-JSON staan.
- Geen contact met personen of organisaties.
- Schrijf alleen naar `data/batches/precisie-12-<id>.json`, `data/sweep/oordeel/<id>.json`,
  `data/sources/<id>/` en `_preview/`. Draai `tools/merge.py` niet (ook niet stap 3 van Controleren in
  BRIEF-PRECISIE): er werken meerdere agents tegelijk en de orchestrator merget aan het eind.

## Rapport terug (kort)

Per venue één regel: gevonden ja/nee, welk document en pagina, jaar, getekend ja/nee.
