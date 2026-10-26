# Blinde reconstructie van een clubzaal uit openbare data

Dit is een **meetproef**. We willen weten hoe goed een volledig automatische methode een clubzaal kan
reconstrueren uit alleen openbare gebouwdata, straatbeelden en videoframes. Jouw tekening wordt daarna
automatisch vergeleken met een officiële plattegrond die jij niet mag zien. Eerlijkheid is belangrijker dan
een mooie score: teken alleen wat je kunt onderbouwen.

ROOT = `C:\Users\JorisMerkx\OneDrive - Agyle\Documenten\Hassan RSA\ik-sta-hier`

## Wat je WEL mag gebruiken

Alleen de map `ROOT/data/auto/<id>/`:
- `context.json`: gebouw uit de BAG (`polygon_m` in meters, x = oost, y = zuid, noord boven), dakhoogtes
  uit 3D BAG, BAG-units in het pand (adres, gebruiksdoel, m², punt), OSM-punten (ingangen), lijst van
  straatbeelden met positie en kijkrichting, lijst van video's met titels en framebestanden.
- `luchtfoto.png` (rood = pand, groen = OSM-ingang, schaalbalk 10 m) en `hoogte.png` (AHN-hoogtekaart:
  hogere delen lichter/anders gekleurd; laat zien waar de hoge zaal zit).
- `street/*.jpg`: straatbeelden rond het pand (gevel, deur, logo).
- `frames/*.jpg`: keyframes uit openbare video's die in de club zijn opgenomen.

Plus de hulpmiddelen: `ROOT/SPEC-ZAAL.md` (tekenformaat), `ROOT/tools/geom.py`, `ROOT/tools/preview.py`.

## Wat je NIET mag gebruiken (anders is de proef waardeloos)

- Niet openen: `data/batches/`, `data/venues.json`, `data/sources/`, `data/footprints/`, `_preview/`,
  `_shots/`, `img/`, `BRIEF-PRECISIE.md`, git-geschiedenis, of de `data/auto/`-mappen van andere clubs.
- Geen WebSearch, WebFetch, curl of andere internettoegang.
- Geen voorkennis: ook als je de club kent, teken niets uit je geheugen. Elk getekend element moet steunen
  op een beeld of op de gebouwdata, en je noemt dat bewijs.

## Werkwijze

1. **Gebouw.** Lees `context.json`, bekijk `luchtfoto.png` en `hoogte.png`. Welk deel van het pand is de zaal
   (hoge hal, unit met bijeenkomstfunctie en het grootste aantal m²)? Hoe groot is die ongeveer?
2. **Ingang.** Bekijk de straatbeelden: waar zit de clubdeur, het logo of de rij? Combineer met de OSM-ingang
   en het adrespunt. Leg vast aan welke gevel de ingang ligt.
3. **Frames.** Bekijk alle frames (Read-tool). Schrijf per frame kort op wat je ziet: waar staat de camera,
   is de DJ-booth of het podium te zien, bars, balkon, trappen, pilaren, ramen, deuren, plafond, en in welke
   richting t.o.v. het podium. Sla frames zonder bruikbare info over (close-ups, overlays, zwart).
   Bewaar dit als `ROOT/data/auto/<id>/observaties.json` (lijst van {frame, gezien, richting}).
4. **Reconstructie.** Combineer gebouw, ingang en frames tot een plattegrond van de **hoofdzaal** (de grootste
   dansvloer). Voeg alleen een tweede zaal toe als de frames duidelijk een andere ruimte laten zien.
   - Werk in meters. Oriëntatie: podium of DJ boven (`rotate` uit geom.py).
   - Gebruik de echte omtrek of een deel ervan als buitenmuur als dat logisch is.
   - Features volgens SPEC-ZAAL.md: dj/stage, bar, in, stairs, pillar, poly (balkon/verhoging).
   - Zet bij elk feature twee extra velden: `"conf": "hoog|middel|laag"` en `"bewijs": ["frame of bron", ...]`.
5. **Controle.** Schrijf het resultaat en render: `python -X utf8 tools/preview.py data/auto/<id>/auto.json`.
   Bekijk de preview met Read. Klopt hij met wat jij in de frames zag? Labels leesbaar? Pas aan.

## Output

`ROOT/data/auto/<id>/auto.json`: een JSON-array met één venue-object:
`[{"id": "<id>", "name": "<naam>", "rooms": [ {hoofdzaal}, ... ], "methode": "auto-blind",
"samenvatting": "2-4 zinnen: waar is de reconstructie op gebaseerd en wat is het zwakst"}]`.
`rooms[0]` is altijd de hoofdzaal.

## Rapport terug (kort)

Hoeveel frames bruikbaar waren, wat je zeker weet en wat geschat is, en hoeveel tijd/beelden je meer
nodig zou hebben om het beter te doen. Schrijf niets buiten `ROOT/data/auto/<id>/` en `ROOT/_preview/`.
