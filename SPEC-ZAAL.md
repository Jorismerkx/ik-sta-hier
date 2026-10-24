# Zaal-spec voor plattegronden

Elke venue heeft 1 of meer zalen. Elke zaal is een versimpelde plattegrond in Lowlands-stijl:
effen kleur, witte muren, podium/DJ als wit kader met tekst, bars als dikke witte streep op de muur,
ingangen als gat in de muur. Alleen wat je nodig hebt om aan een vriend te zeggen waar je staat.

## Conventies

- Coördinaten in een vrij grid (meestal 0..100 breed, hoogte naar verhouding, bijv. 0..130 voor een langwerpige zaal).
  De renderer schaalt alles passend. Verhoudingen kloppen dus, absolute maten niet.
- **Oriëntatie: DJ/podium bovenaan (y klein), hoofdingang van de zaal onderaan of aan de zijkant.** Zo kijkt iedereen naar dezelfde kant: "voorin" = boven.
- Muren = `outline` (polygon, gesloten). Ronde zaal = `round: {cx,cy,r}`.
- Features liggen óp of ín de outline. Een bar langs de linkermuur: `a:[0,30], b:[0,60]`.
- `side` (1 of -1) kiest aan welke kant van de lijn het label komt (bar/ingang). Standaard 1 = rechts van de richting a→b. Probeer labels binnen de zaal te houden, buiten mag als er ruimte is.
- Houd het leeg. Max ~10 features per zaal. Geen meubels, geen toiletten tenzij ze een herkenpunt zijn.

## Features

| t | velden | betekenis |
|---|---|---|
| `dj` | x,y,w,h, label? | DJ-booth (kader met "DJ") |
| `stage` | x,y,w,h, label? | podium (kader met "PODIUM") |
| `bar` | a,b, side?, label? | bar, dikke streep |
| `in` | a,b, side?, label? | ingang/doorgang: gat in de muur, label "IN" (of "NAAR ZAAL 2", "TRAP", "ROOKRUIMTE") |
| `wc` | x,y | label WC |
| `smoke` | x,y | label ROKEN |
| `stairs` | x,y, label? | label TRAP |
| `cloak` | x,y | label GARDEROBE |
| `pillar` | x,y | paal (wit vierkantje) |
| `line` | a,b, dash?, o? | dunne lijn (verhoging, balkonrand, scheiding) |
| `poly` | pts, text?, dash? | dunne gesloten lijn met optioneel label (balkon, verhoging, dansvloer-rand, buitenterras) |
| `label` | x,y, text, size? | vrije tekst |

## Voorbeeld

```json
{
  "name": "Grote Zaal",
  "outline": [[0,0],[100,0],[100,130],[0,130]],
  "features": [
    {"t":"stage","x":15,"y":4,"w":70,"h":22},
    {"t":"bar","a":[0,60],"b":[0,100]},
    {"t":"bar","a":[100,60],"b":[100,100],"side":-1},
    {"t":"in","a":[40,130],"b":[60,130]},
    {"t":"pillar","x":30,"y":70},{"t":"pillar","x":70,"y":70}
  ]
}
```

## Venue-object

```json
{
  "id": "paradiso",
  "name": "Paradiso",
  "address": "Weteringschans 6-8, 1017 SG Amsterdam",
  "area": "Centrum",
  "lat": 52.3624, "lng": 4.8838,
  "website": "https://www.paradiso.nl",
  "source": "korte bron/opmerking: officiële plattegrond, foto's, bezoekersbeschrijving, of 'indicatief'",
  "confidence": "hoog|middel|laag",
  "note": "optionele tekst voor in de app (bv. 'Kleine Zaal is via de trap links van de bar')",
  "rooms": [ ... ]
}
```
