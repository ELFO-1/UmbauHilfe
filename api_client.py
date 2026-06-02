#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HTTP-Client für die Wieland-Umbau-Hilfe.

Spricht GENAU dieselbe REST-API wie das Webinterface (siehe webserver.py) und
stellt dieselben Methoden bereit wie die lokale Datenschicht SchumagDB. Dadurch
arbeitet das Terminal-Programm (cli.py) gegen DIESELBE Datenbank wie Web und
Handy – egal von welchem Rechner aus. Es gibt nur noch eine Quelle der Wahrheit:
die Datenbank auf dem Server.

Nur Python-Standardbibliothek, keine Installation nötig.

Server-Adresse über Umgebungsvariable SCHUMAG_API setzen, z.B.:
    export SCHUMAG_API=https://umbauhilfe.dein-tailnet.ts.net
Standard ist  http://localhost:8000  (lokaler Webserver).
"""

import json
import os
import urllib.error
import urllib.parse
import urllib.request

DEFAULT_URL = os.environ.get("SCHUMAG_API", "http://localhost:8000")


class APIError(Exception):
    """Server nicht erreichbar oder hat einen Fehler gemeldet."""


class SchumagAPI:
    """Gleiche Schnittstelle wie SchumagDB, aber über HTTP statt SQLite."""

    def __init__(self, base_url=DEFAULT_URL):
        self.base = base_url.rstrip("/")

    # -- interne Helfer -----------------------------------------------------
    def _do(self, req):
        try:
            with urllib.request.urlopen(req, timeout=10) as antwort:
                body = antwort.read().decode("utf-8")
                return json.loads(body) if body else {}
        except urllib.error.HTTPError as e:
            # z.B. 404 bei /api/get ("nicht gefunden") liefert leeres JSON –
            # das ist kein Verbindungsfehler, sondern ein normales Ergebnis.
            try:
                return json.loads(e.read().decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError, ValueError):
                return {}
        except urllib.error.URLError as e:
            raise APIError(f"Server nicht erreichbar ({self.base}): {e.reason}")

    def _get(self, pfad, **params):
        gefiltert = {k: v for k, v in params.items() if v is not None}
        qs = urllib.parse.urlencode(gefiltert)
        url = f"{self.base}{pfad}" + (f"?{qs}" if qs else "")
        return self._do(urllib.request.Request(url))

    def _post(self, pfad, payload):
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{self.base}{pfad}", data=data,
            headers={"Content-Type": "application/json"})
        return self._do(req)

    # -- Lesen --------------------------------------------------------------
    def liste(self, kategorie, anlage=None):
        res = self._get("/api/list", kat=kategorie, anlage=anlage)
        return res if isinstance(res, list) else []

    def hole(self, kategorie, key, anlage=None):
        res = self._get("/api/get", kat=kategorie, key=key, anlage=anlage)
        if isinstance(res, dict) and res and "fehler" not in res:
            return res
        return None

    def suche(self, begriff):
        res = self._get("/api/search", q=begriff)
        return res if isinstance(res, list) else []

    # -- Schreiben ----------------------------------------------------------
    def hinzufuegen(self, kategorie, key, infos, anlage=None):
        res = self._post("/api/add", {
            "kat": kategorie, "key": key, "infos": infos, "anlage": anlage})
        return bool(res.get("ok"))

    def aktualisieren(self, kategorie, key, neue_infos, anlage=None):
        res = self._post("/api/update", {
            "kat": kategorie, "key": key, "infos": neue_infos, "anlage": anlage})
        return bool(res.get("ok"))

    def loeschen(self, kategorie, key, anlage=None):
        res = self._post("/api/delete", {
            "kat": kategorie, "key": key, "anlage": anlage})
        return bool(res.get("ok"))

    def backup(self):
        res = self._post("/api/backup", {})
        return res.get("datei", "(unbekannt)")

    # -- Verbindung ---------------------------------------------------------
    def ping(self):
        """Prüft, ob der Server erreichbar ist. Wirft APIError, wenn nicht."""
        self._get("/api/config")

    def close(self):
        pass  # nichts zu schließen – HTTP ist zustandslos
