/* config.js — waar de server van Ik sta hier staat (accounts, vrienden, events, meldingen).
   Lokaal (node server/server.js) en op Render levert dezelfde server de app en de API: dan blijft api leeg.
   Op GitHub Pages en in de iOS/Android-app praat de app met de server op Render. */
(function () {
  const lokaal = !window.Capacitor && /^(localhost|127\.0\.0\.1)$/.test(location.hostname);
  const render = /\.onrender\.com$/.test(location.hostname);
  window.ISH_CONFIG = {
    api: lokaal || render ? '' : 'https://ik-sta-hier.onrender.com',
    demo: /\.github\.io$/.test(location.hostname), // tot de server online staat: GitHub Pages in demostand (demo.js)
    web: lokaal ? '' : 'https://jorismerkx.github.io/ik-sta-hier/', // uitnodigingslinks wijzen naar de app op GitHub Pages
  };
})();
