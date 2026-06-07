/*
 * Service-Worker der Wieland-Umbau-Hilfe (PWA).
 *
 * Aufgabe:
 *  - Die "App-Hülle" (HTML/CSS/JS/Icons) wird zwischengespeichert, damit die
 *    Seite auch offline startet und sich wie eine App installieren lässt.
 *  - Die DATEN (/api/...) werden NICHT blind gecacht: sie kommen live vom
 *    Server. Geht der Server/das Netz nicht, greift ein Fallback auf die
 *    zuletzt gesehene Antwort (damit man offline wenigstens lesen kann).
 *
 * Wichtig: Beim Ändern der App-Dateien die CACHE_VERSION hochzählen, dann
 * holt sich der Browser die neuen Dateien.
 */

const CACHE_VERSION = "wuh-v4";
const APP_SHELL = [
  "./",
  "./index.html",
  "./anlage.html",
  "./app.js",
  "./db_local.js",
  "./seed.json",
  "./style.css",
  "./manifest.webmanifest",
  "./icons/icon-192.png",
  "./icons/icon-512.png",
];

// Installieren: App-Hülle einlagern.
self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_VERSION).then((cache) => cache.addAll(APP_SHELL))
  );
  self.skipWaiting();
});

// Aktivieren: alte Cache-Versionen aufräumen.
self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE_VERSION).map((k) => caches.delete(k)))
    )
  );
  self.clients.claim();
});

// Anfragen abfangen.
self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);

  // Nur GET behandeln; POST (Speichern/Löschen) immer direkt ans Netz.
  if (event.request.method !== "GET") {
    return; // Standardverhalten (Browser macht das Netz-Fetch)
  }

  // API-Daten: "network-first" mit Cache-Fallback (offline lesen möglich).
  if (url.pathname.startsWith("/api/")) {
    event.respondWith(
      fetch(event.request)
        .then((antwort) => {
          const kopie = antwort.clone();
          caches.open(CACHE_VERSION).then((c) => c.put(event.request, kopie));
          return antwort;
        })
        .catch(() => caches.match(event.request))
    );
    return;
  }

  // App-Hülle: "cache-first" (schneller Start, offline-fähig).
  event.respondWith(
    caches.match(event.request).then((treffer) => treffer || fetch(event.request))
  );
});
