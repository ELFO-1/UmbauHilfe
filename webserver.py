#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Webserver der Wieland-Umbau-Hilfe.

- Liefert das Webinterface aus dem Ordner  static/
- Bietet eine kleine JSON-/REST-API auf  /api/...  die GENAU dieselbe
  Datenbank/Logik (schumag_core.py) benutzt wie das Terminal-Programm.

Nur Python-Standardbibliothek, keine Installation nötig.

Start:   python3 webserver.py
Dann:    http://localhost:8000  im Browser öffnen
         (im Netzwerk:  http://<deine-ip>:8000 )
"""

import json
import os
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

from schumag_core import (
    SchumagDB, KATEGORIEN, ANLAGEN, GLOBALE_KATEGORIEN, felder_zu_infos,
)

PORT = 8000
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")


class Handler(SimpleHTTPRequestHandler):
    # Statische Dateien aus dem static/-Ordner ausliefern.
    # MIME-Typen ergänzen, die manche Python-Versionen nicht kennen
    # (.webmanifest muss als manifest+json kommen, sonst lehnt der Browser
    #  das PWA-Manifest ab).
    extensions_map = {
        **SimpleHTTPRequestHandler.extensions_map,
        ".webmanifest": "application/manifest+json",
        ".js": "text/javascript",
        ".json": "application/json",
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=STATIC_DIR, **kwargs)

    # -- Antwort-Helfer -----------------------------------------------------
    def _json(self, daten, status=200):
        body = json.dumps(daten, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _body_json(self):
        laenge = int(self.headers.get("Content-Length", 0))
        if not laenge:
            return {}
        try:
            return json.loads(self.rfile.read(laenge).decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return {}

    @staticmethod
    def _infos_aus_request(kategorie, data):
        """Nimmt entweder fertige 'infos' oder ein 'felder'-dict entgegen."""
        if KATEGORIEN[kategorie]["felder"] and "felder" in data:
            return felder_zu_infos(kategorie, data.get("felder") or {})
        return data.get("infos", "")

    # -- GET ----------------------------------------------------------------
    def do_GET(self):
        pfad = urlparse(self.path).path
        if pfad.startswith("/api/"):
            return self._api_get(pfad)
        # sonst: statische Datei
        if pfad == "/":
            self.path = "/index.html"
        return super().do_GET()

    def _api_get(self, pfad):
        params = parse_qs(urlparse(self.path).query)
        einzel = lambda k: params.get(k, [None])[0]
        db = SchumagDB()
        try:
            if pfad == "/api/config":
                return self._json({
                    "anlagen": ANLAGEN,
                    "kategorien": KATEGORIEN,
                    "globale_kategorien": GLOBALE_KATEGORIEN,
                })
            if pfad == "/api/list":
                kat = einzel("kat")
                if kat not in KATEGORIEN:
                    return self._json({"fehler": "Unbekannte Kategorie"}, 400)
                return self._json(db.liste(kat, einzel("anlage")))
            if pfad == "/api/get":
                kat = einzel("kat")
                if kat not in KATEGORIEN:
                    return self._json({"fehler": "Unbekannte Kategorie"}, 400)
                eintrag = db.hole(kat, einzel("key"), einzel("anlage"))
                return self._json(eintrag or {}, 200 if eintrag else 404)
            if pfad == "/api/search":
                return self._json(db.suche(einzel("q")))
            return self._json({"fehler": "Unbekannter Endpunkt"}, 404)
        except Exception as e:  # robuste Fehlermeldung statt Absturz
            return self._json({"fehler": str(e)}, 500)
        finally:
            db.close()

    # -- POST (add / update / delete / backup) ------------------------------
    def do_POST(self):
        pfad = urlparse(self.path).path
        if not pfad.startswith("/api/"):
            return self._json({"fehler": "Nur /api/ erlaubt"}, 404)
        data = self._body_json()
        db = SchumagDB()
        try:
            if pfad == "/api/add":
                kat = data.get("kat")
                if kat not in KATEGORIEN:
                    return self._json({"fehler": "Unbekannte Kategorie"}, 400)
                infos = self._infos_aus_request(kat, data)
                ok = db.hinzufuegen(kat, data.get("key", ""), infos, data.get("anlage"))
                return self._json({"ok": ok,
                                   "fehler": None if ok else "Eintrag existiert bereits oder Bezeichnung fehlt"})
            if pfad == "/api/update":
                kat = data.get("kat")
                if kat not in KATEGORIEN:
                    return self._json({"fehler": "Unbekannte Kategorie"}, 400)
                infos = self._infos_aus_request(kat, data)
                ok = db.aktualisieren(kat, data.get("key", ""), infos, data.get("anlage"))
                return self._json({"ok": ok})
            if pfad == "/api/delete":
                kat = data.get("kat")
                if kat not in KATEGORIEN:
                    return self._json({"fehler": "Unbekannte Kategorie"}, 400)
                ok = db.loeschen(kat, data.get("key", ""), data.get("anlage"))
                return self._json({"ok": ok})
            if pfad == "/api/backup":
                return self._json({"ok": True, "datei": db.backup()})
            return self._json({"fehler": "Unbekannter Endpunkt"}, 404)
        except Exception as e:
            return self._json({"fehler": str(e)}, 500)
        finally:
            db.close()

    # Logausgabe etwas ruhiger
    def log_message(self, fmt, *args):
        pass


def main():
    SchumagDB().close()  # stellt sicher, dass die DB/Tabellen existieren
    server = ThreadingHTTPServer(("", PORT), Handler)
    print(f"Webinterface läuft auf  http://localhost:{PORT}")
    print("Beenden mit  Strg+C")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer beendet.")


if __name__ == "__main__":
    main()
