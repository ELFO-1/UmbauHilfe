# Wieland Umbau Hilfe – Schumag Anlagen

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Nachschlage- und Pflege-Tool für die Umbau-/Einstelldaten der Schumag-Anlagen
(Rund-, Profil- und Spezialschumag). Die beiden früheren Projekte (HTML+CSV
und Python+SQLite) sind jetzt **ein** Programm mit **einer** Datenbank.

## Aufbau

| Datei | Aufgabe |
|-------|---------|
| `schumag_core.py` | Gemeinsame Datenschicht + Konfiguration (Anlagen, Kategorien, Felder). Wird von Terminal **und** Web benutzt. |
| `cli.py` | Terminal-Programm |
| `webserver.py` | Webserver (REST-API + liefert das Webinterface) |
| `static/` | Webinterface (HTML/CSS/JS) + PWA (Manifest, Service-Worker, Icons) + Offline-Logik (`db_local.js`, `seed.json`) |
| `import_csv.py` | Einmaliger Import der alten CSV-Dateien in die DB |
| `export_seed.py` | Erzeugt `static/seed.json` (Datenstand für die Offline-App) |
| `schumag.db` | SQLite-Datenbank (Quelle der Wahrheit am PC) |
| `android/` | Capacitor-Android-Projekt (erzeugt die .apk) |
| `UmbauHilfe-debug.apk` | Fertige Android-App (Offline, lokal bearbeitbar) |

Es werden **keine** externen Bibliotheken benötigt (nur Python-Standardlib).
`colorama` macht das Terminal bunt, ist aber optional.

## Benutzung

**Terminal:**
```
python3 cli.py
```

**Webinterface:**
```
python3 webserver.py
```
Danach im Browser `http://localhost:8000` öffnen. Im selben Netzwerk (z.B. vom
Handy/Tablet in der Werkstatt) über `http://<IP-des-Rechners>:8000`.

**Alte CSV-Daten importieren** (schon erledigt, aber wiederholbar/ungefährlich):
```
python3 import_csv.py
```

## Datenmodell

Jede Kategorie ist eine Tabelle mit Bezeichnung + `infos` (Text) + `updated`.
Kategorien mit festen Feldern (Durchmesser, Sonderlegierungen) speichern die
`infos` als `Feld: Wert`-Zeilen – dadurch funktionieren geführte Eingabe im
Terminal und Formular im Web mit demselben Format.

## Altlasten

Die alten Dateien (`server.py`, `wieland_schumag_datenbank.py`, alte
`index.html`, `zg*index.html`, `zg*data.csv`) sowie die alten Unterordner
(`zg21/`, `zg23/`, `zg24/`, `wieland_umbau_hilfe/`) wurden nach `_alt_archiv/`
verschoben. Sie werden nicht mehr gebraucht – wenn alles weiter läuft, kann
`_alt_archiv/` komplett gelöscht werden.

Eine Sicherung der DB von vor dem CSV-Import liegt unter
`schumag.db.vor_import_backup`.

## PWA – „App“ ohne Installation aus dem Store

Das Webinterface ist eine **PWA** (Progressive Web App): installierbar und
offline-fähig. Dazu liegen in `static/`:

- `manifest.webmanifest` – Name, Farben, Icons, Vollbild-Modus
- `service-worker.js` – cacht die App-Hülle + zuletzt geladene Daten
- `icons/` – App-Icons (192/512 px, maskable, Apple-Touch-Icon)

**So installiert man sie auf dem Handy/Tablet (Werkstatt):**

1. `python3 webserver.py` auf dem Rechner starten.
2. Am Gerät im selben WLAN `http://<IP-des-Rechners>:8000` im Browser öffnen.
3. Browsermenü → **„Zum Startbildschirm hinzufügen“ / „App installieren“**.
4. Danach startet die App über ein eigenes Icon im Vollbild. Einmal geladene
   Anlagen/Daten sind auch **offline** abrufbar (Lesen). Zum Speichern/Ändern
   muss der Server erreichbar sein.

Hinweis: Service-Worker laufen nur über `http://localhost` oder `https://`.
Im lokalen Netz per `http://<IP>` kann es sein, dass „Installieren“
angeboten wird, der Offline-Cache aber erst ab HTTPS voll greift – fürs reine
Nachschlagen im WLAN reicht es trotzdem. Für vollen Offline-Betrieb die Seite
über HTTPS ausliefern (z.B. Reverse-Proxy) oder die echte .apk bauen (unten).

Beim Ändern von Dateien in `static/` die `CACHE_VERSION` in
`service-worker.js` hochzählen, damit Geräte die neue Version laden.

## Android-.apk – Offline-App mit lokaler Datenbank

Die App ist **offline-fähig und auf dem Gerät bearbeitbar** (mit Capacitor
verpackt). Architektur: Der Python-Webserver läuft NICHT auf dem Handy. Die
Daten liegen lokal in der **IndexedDB** des Geräts; die Logik dafür steckt in
`static/db_local.js` und bildet exakt dieselbe API nach wie `webserver.py`.

`static/app.js` wählt das Backend automatisch:
- **in der App** (Capacitor erkannt) → lokale DB (`db_local.js`)
- **im Browser über `webserver.py`** → Server-API (`/api/...`)
- zum Testen im Browser erzwingbar mit `?local=1` in der URL

Die fertige Datei liegt als **`UmbauHilfe-debug.apk`** im Projektordner
(Debug-Build, direkt aufs Handy kopieren und installieren – „Installation aus
unbekannten Quellen“ erlauben).

### Daten in die App bekommen / aktualisieren

Beim ersten Start lädt die App `static/seed.json` in ihre lokale DB. Das ist
der **eingebaute Datenstand**. Workflow zum Aktualisieren:

```bash
# 1) Daten am PC pflegen (Terminal oder Web), dann Snapshot exportieren:
python3 export_seed.py            # schreibt static/seed.json

# 2) Snapshot in die App kopieren und neu bauen:
npx cap sync android
cd android
JAVA_HOME=/usr/lib/jvm/java-21-openjdk \
ANDROID_HOME=$HOME/Android/Sdk \
  ./gradlew assembleDebug --no-daemon
# Ergebnis: android/app/build/outputs/apk/debug/app-debug.apk
```

Wichtig: Auf einem Gerät, das die App schon installiert hat, **überschreibt
seed.json die lokalen Änderungen NICHT** (die App lädt seed nur beim ersten
Start). Soll der neue Stand sicher übernommen werden, vorher die App-Daten
löschen (Android-Einstellungen → App → Speicher → Daten löschen) oder neu
installieren.

### Build-Voraussetzungen (auf diesem Rechner erfüllt)

- **JDK 21** (Capacitor 8 braucht source-level 21): `/usr/lib/jvm/java-21-openjdk`
- **Android SDK** mit Platform 36 + build-tools: `~/Android/Sdk`
- **Node.js** für `npx cap`
- `android/local.properties` enthält `sdk.dir=$HOME/Android/Sdk`

### Alternative: Online-App

Statt lokaler DB könnte die App auch das Webinterface zeigen und über
`http(s)://<server>` mit einer zentralen `webserver.py`-API sprechen
(gemeinsame DB für alle, aber Netz nötig). Dafür in `app.js` `USE_LOCAL` auf
`false` zwingen und die feste Server-Adresse in `apiGet`/`apiPost` eintragen.

### Hinweis zu Debug vs. Release

`UmbauHilfe-debug.apk` ist ein **Debug-Build** – ideal zum Ausprobieren, aber
mit Debug-Schlüssel signiert. Für eine „richtige“ Verteilung später einen
Release-Build mit eigenem Keystore signieren (`./gradlew assembleRelease` +
`apksigner`).
