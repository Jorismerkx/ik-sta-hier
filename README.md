# Ik sta hier

Versimpelde plattegronden (Lowlands-stijl) van alle clubs en dance-venues in Amsterdam.
Zet je puntje op de zaal, deel het plaatje via WhatsApp. Werkt ook met slecht bereik: de
plattegronden zitten in de app, delen gaat als gewoon plaatje.

## Lokaal draaien

```
cd ik-sta-hier
python -m http.server 8765
```

Open http://localhost:8765 op de desktop (iPhone-frame) of op je telefoon in hetzelfde wifi-netwerk
via http://<ip-van-je-pc>:8765. Delen via WhatsApp werkt alleen op een echte telefoon (Web Share API);
in de desktopbrowser wordt het plaatje gedownload.

## Structuur

- `index.html`, `style.css`, `app.js` — de app (lijst, kaart, zalen, pen, delen)
- `plan.js` — renderer: zaal-spec (JSON) → SVG-kaartje 900x1600
- `data/venues.json` — alle venues (samengevoegd)
- `data/batches/*.json` — bronbestanden per batch, zie `SPEC-ZAAL.md`
- `tools/merge.py` — batches samenvoegen + controleren
- `tools/geocode.py` — ontbrekende coördinaten ophalen (Nominatim)
- `tools/shot.py` — screenshots/test via Playwright

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
