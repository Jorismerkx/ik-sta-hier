# Ik sta hier

Versimpelde plattegronden (Lowlands-stijl) van alle clubs en dance-venues in Amsterdam.
Zet je puntje op de zaal, deel het plaatje via WhatsApp. Werkt ook met slecht bereik: de
plattegronden zitten in de app, delen gaat als gewoon plaatje.

## Lokaal draaien

```
cd ik-sta-hier/server
npm install
node server.js
```

Open http://localhost:8787 op de desktop (iPhone-frame) of op je telefoon in hetzelfde wifi-netwerk
via http://<ip-van-je-pc>:8787. De server levert de app én de API voor vrienden en events.
Alleen de plattegronden bekijken kan ook zonder server: `python -m http.server 8765` in de hoofdmap.
Delen via WhatsApp werkt alleen op een echte telefoon (Web Share API); in de desktopbrowser wordt het plaatje gedownload.

## Vrienden, events en "Waar sta je?"

- **Profiel**: alleen een naam. De server geeft een token terug dat op het toestel blijft; geen wachtwoord, geen GPS.
- **Vrienden**: via je vriendlink (WhatsApp) of je code van 6 tekens. Vriendschap geldt altijd twee kanten op.
- **Event**: club, zalen (alle of een paar), datum en tijd, vrienden. Uitgenodigde vrienden zien het event meteen
  (live via SSE, en als melding). Anderen doen mee via de uitnodigingslink (`#e/<code>`) in WhatsApp.
- **Feed** van een event: geen chat. Alleen *Waar zijn jullie?* (ping met SOS-trilling) en *Ik sta hier* (puntje op de
  plattegrond, met automatische omschrijving zoals "rechts voor, bij de bar"). Tik een puntje aan om het groot te zien,
  samen met de laatste plek van de anderen.
- **De knop in het midden** (*Waar sta je?*) werkt op het event van vanavond (12:00 tot 08:00 de ochtend erna).
- **Zonder bereik** gaan pings en puntjes in een wachtrij en worden ze verstuurd zodra er verbinding is; voor het puntje
  biedt de app ook een kant-en-klare sms aan.
- **Meldingen**: web-push (VAPID). Werkt in Chrome op Android en in Safari op iPhone als de app op het beginscherm staat
  (iOS 16.4+). In de native Capacitor-app zijn pushmeldingen nog niet aangesloten (vereist APNs/FCM); daar komen
  updates binnen zolang de app open is.

Server: `server/server.js` (Node 22.13+, ingebouwde SQLite, alleen `web-push` als pakket). Data in `DATA_DIR`
(standaard `server/data/`): `ish.db` en `vapid.json`. Test: `python -X utf8 tools/social_test.py` (drie gebruikers,
start zelf een tijdelijke server).

**Online zetten**: de `Dockerfile` bouwt server + app in één container (Railway, Render, Fly.io). Zet een volume op
`/data`. Draait de app ergens anders (GitHub Pages, de iOS/Android-app), vul dan in `config.js` bij `api` het adres van
de server in.

## Structuur

- `index.html`, `style.css`, `app.js` — de app (lijst, kaart, zalen, pen, delen)
- `social.js` — vrienden, events, feed, wachtrij zonder bereik, meldingen; `config.js` — adres van de server
- `server/` — API, live updates (SSE), web-push, en de webapp zelf
- `plan.js` — renderer: zaal-spec (JSON) → SVG-kaartje 900x1600, plus puntjes van vrienden en `Plan.where()`
- `data/venues.json` — alle venues (samengevoegd)
- `data/batches/*.json` — bronbestanden per batch, zie `SPEC-ZAAL.md`
- `tools/merge.py` — batches samenvoegen + controleren
- `tools/geocode.py` — ontbrekende coördinaten ophalen (Nominatim)
- `tools/shot.py` — screenshots/test via Playwright; `tools/social_test.py` — end-to-end test vrienden/events

## Werkwijze data

1. Venue + zalen beschrijven in een batchbestand volgens `SPEC-ZAAL.md`.
2. `python tools/merge.py`
3. `python tools/geocode.py data/venues.json` als er coördinaten ontbreken.

## Foto's

- `tools/photos.py` haalt per venue de og:image van de eigen site, verkleint naar 800x800 in `img/venues/<id>.jpg`.
- Handmatige foto-URL's in `data/photos.json` (`{"<id>": "<url>"}`) winnen altijd; daarna `python tools/photos.py --force <id>` of zonder argumenten voor alle ontbrekende.
- `merge.py` zet `photo: true` als het bestand bestaat; zonder foto toont de app een gekleurd blok met initialen.

## App installeren (PWA)

Open de URL in Safari op iPhone en kies "Zet op beginscherm". `manifest.webmanifest` + `sw.js` zorgen dat schil, data,
foto's en bekeken kaarttegels offline beschikbaar zijn. Hosten kan op elke statische host (GitHub Pages, Netlify, Render);
Web Share (WhatsApp) vereist https.

## Echte app (iOS en Android) via Capacitor

Dezelfde code draait als native app in een WebView, met native deelvenster (WhatsApp) via `@capacitor/share`.

- `python tools/build-www.py` kopieert de webapp naar `www/`; `npx cap sync` zet dat in `android/` en `ios/`.
- Iconen en splash: `resources/` → `npx @capacitor/assets generate`.
- **Android**: GitHub Actions (`.github/workflows/apps.yml`) bouwt bij elke push een debug-APK (artifact "ik-sta-hier-android-debug.apk").
  Lokaal: Android Studio openen op `android/`. Voor de Play Store: signed release-build + Google Play-account (25 dollar eenmalig).
- **iOS**: bouwen kan alleen met Xcode (Mac) of de macOS-runner in GitHub Actions. Op een iPhone zetten en in de App Store
  vereist een Apple Developer-account (99 dollar per jaar). Workflow: `ios/App/App.xcworkspace` openen in Xcode, team kiezen, Run.
- **Website/PWA**: `.github/workflows/pages.yml` zet `www/` op GitHub Pages (Settings > Pages > Source: GitHub Actions).
