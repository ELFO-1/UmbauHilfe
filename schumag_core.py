#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gemeinsame Datenschicht für die Wieland-Umbau-Hilfe (Schumag Anlagen).

Diese Datei ist das Herzstück: Terminal-Programm (cli.py) UND Webserver
(webserver.py) benutzen GENAU diese Klasse + Konfiguration. Dadurch gibt es
nur eine Datenbank und keine doppelte Logik mehr (vorher: CSV fürs Web,
SQLite fürs Terminal).

Es werden keine externen Bibliotheken benötigt (nur Python-Standardlib).
"""

import sqlite3

DB_NAME = "schumag.db"


# ---------------------------------------------------------------------------
# Konfiguration: Anlagen, Kategorien und Eingabe-Felder
# ---------------------------------------------------------------------------
#
# KATEGORIEN beschreibt jede Tabelle:
#   label   – Anzeigename
#   key     – Name der "Bezeichnungs"-Spalte in der Tabelle
#   anlage  – True, wenn die Einträge zu einer Anlage gehören
#   felder  – feste Unterfelder (für geführte Eingabe + Web-Formular) oder None
#
# Der Inhalt ("infos") wird einheitlich als Text gespeichert. Hat eine
# Kategorie "felder", dann im Format  "<Feld>: <Wert>"  je Zeile – so wie es
# das ursprüngliche Terminal-Programm schon gemacht hat. Dadurch sind die
# bereits vorhandenen Daten weiter lesbar.

DURCHMESSER_FELDER = [
    "Schweißdaten", "Hämmerbacken", "Einstoßbacken", "Ziehstein",
    "Einlaufdüse", "Ziehbacken", "Trichter", "Wirbelstrom", "Ultraschall",
    "Scherenmesser", "Rollen", "Rohrkasten", "Rohre", "Lineale", "Stempel",
    "Sonstige Infos",
]

SONDERLEGIERUNG_FELDER = [
    "Allgemeine Infos", "Schmierung", "Stempel", "Spezielle Ziehsteine",
]

KATEGORIEN = {
    "durchmesser":       {"label": "Durchmesser",      "key": "durchmesser",  "anlage": True,  "felder": DURCHMESSER_FELDER},
    "profile":           {"label": "Profile",          "key": "bezeichnung",  "anlage": True,  "felder": None},
    "flachkant":         {"label": "Flachkant",        "key": "bezeichnung",  "anlage": True,  "felder": None},
    "vierkant":          {"label": "Vierkant",         "key": "bezeichnung",  "anlage": True,  "felder": None},
    "ring_auf_stange":   {"label": "Ring auf Stange",  "key": "typ",          "anlage": True,  "felder": None},
    "ring_auf_ring":     {"label": "Ring auf Ring",    "key": "typ",          "anlage": True,  "felder": None},
    "allgemeine_infos":  {"label": "Allgemeine Infos", "key": "titel",        "anlage": True,  "felder": None},
    "sonderlegierungen": {"label": "Sonderlegierungen","key": "name",         "anlage": False, "felder": SONDERLEGIERUNG_FELDER},
}

# Welche Kategorien hat welche Anlage? (Gruppen wie im Original-Terminal.)
ANLAGEN = {
    "ZG25": {"gruppe": "Rundschumag",   "kategorien": ["durchmesser", "allgemeine_infos"]},
    "ZG23": {"gruppe": "Rundschumag",   "kategorien": ["durchmesser", "allgemeine_infos"]},
    "ZG24": {"gruppe": "Rundschumag",   "kategorien": ["durchmesser", "allgemeine_infos"]},
    "ZG21": {"gruppe": "Rundschumag",   "kategorien": ["durchmesser", "allgemeine_infos"]},
    "ZG19": {"gruppe": "Profilschumag", "kategorien": ["profile", "flachkant", "vierkant", "allgemeine_infos"]},
    "ZG26": {"gruppe": "Profilschumag", "kategorien": ["profile", "flachkant", "vierkant", "allgemeine_infos"]},
    "ZG10": {"gruppe": "Spezialschumag","kategorien": ["ring_auf_stange", "ring_auf_ring", "allgemeine_infos"]},
}

# Globale Kategorien (gehören zu keiner einzelnen Anlage)
GLOBALE_KATEGORIEN = ["sonderlegierungen"]


# ---------------------------------------------------------------------------
# Hilfsfunktionen für das einheitliche "infos"-Format
# ---------------------------------------------------------------------------

def felder_zu_infos(kategorie, felder_werte):
    """dict {Feldname: Wert}  ->  Text  "Feld: Wert" je Zeile."""
    felder = KATEGORIEN[kategorie]["felder"] or []
    zeilen = [f"{name}: {felder_werte.get(name, '')}" for name in felder]
    return "\n".join(zeilen)


def infos_zu_felder(kategorie, infos):
    """Text  "Feld: Wert"  ->  dict {Feldname: Wert}. Robust gegen fehlende Felder."""
    felder = KATEGORIEN[kategorie]["felder"] or []
    ergebnis = {name: "" for name in felder}
    if not infos:
        return ergebnis
    for zeile in infos.splitlines():
        if ": " in zeile:
            name, _, wert = zeile.partition(": ")
            if name in ergebnis:
                ergebnis[name] = wert
    return ergebnis


# ---------------------------------------------------------------------------
# Datenbankklasse
# ---------------------------------------------------------------------------

class SchumagDB:
    """Generische Datenschicht über allen Kategorien-Tabellen."""

    def __init__(self, db_name=DB_NAME):
        self.conn = sqlite3.connect(db_name)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        self.setup_database()

    # -- Aufbau -------------------------------------------------------------
    def setup_database(self):
        """Legt alle Tabellen an, falls sie noch nicht existieren."""
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS hauptgruppen (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE)""")
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS anlagen (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                hauptgruppe_id INTEGER,
                FOREIGN KEY (hauptgruppe_id) REFERENCES hauptgruppen (id))""")

        for kat, meta in KATEGORIEN.items():
            spalten = ["id INTEGER PRIMARY KEY AUTOINCREMENT"]
            if meta["anlage"]:
                spalten.append("anlage TEXT NOT NULL")
            spalten.append(f"{meta['key']} TEXT NOT NULL")
            spalten.append("infos TEXT")
            spalten.append("updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
            self.cursor.execute(
                f"CREATE TABLE IF NOT EXISTS {kat} ({', '.join(spalten)})")
        self.conn.commit()

    # -- interne Helfer -----------------------------------------------------
    @staticmethod
    def _check(kategorie):
        if kategorie not in KATEGORIEN:
            raise ValueError(f"Unbekannte Kategorie: {kategorie}")
        return KATEGORIEN[kategorie]

    def _row_to_dict(self, kategorie, row):
        meta = KATEGORIEN[kategorie]
        d = {
            "kategorie": kategorie,
            "key": row[meta["key"]],
            "infos": row["infos"],
            "updated": row["updated"],
        }
        if meta["anlage"]:
            d["anlage"] = row["anlage"]
        if meta["felder"]:
            d["felder"] = infos_zu_felder(kategorie, row["infos"])
        return d

    # -- Lesen --------------------------------------------------------------
    def liste(self, kategorie, anlage=None):
        meta = self._check(kategorie)
        if meta["anlage"]:
            self.cursor.execute(
                f"SELECT * FROM {kategorie} WHERE anlage = ? ORDER BY {meta['key']}",
                (anlage,))
        else:
            self.cursor.execute(
                f"SELECT * FROM {kategorie} ORDER BY {meta['key']}")
        return [self._row_to_dict(kategorie, r) for r in self.cursor.fetchall()]

    def hole(self, kategorie, key, anlage=None):
        meta = self._check(kategorie)
        if meta["anlage"]:
            self.cursor.execute(
                f"SELECT * FROM {kategorie} WHERE anlage = ? AND {meta['key']} = ?",
                (anlage, key.upper()))
        else:
            self.cursor.execute(
                f"SELECT * FROM {kategorie} WHERE {meta['key']} = ?", (key.upper(),))
        row = self.cursor.fetchone()
        return self._row_to_dict(kategorie, row) if row else None

    # -- Schreiben ----------------------------------------------------------
    def hinzufuegen(self, kategorie, key, infos, anlage=None):
        meta = self._check(kategorie)
        if not key or not key.strip():
            return False
        if self.hole(kategorie, key, anlage):
            return False  # existiert schon
        if meta["anlage"]:
            self.cursor.execute(
                f"INSERT INTO {kategorie} (anlage, {meta['key']}, infos) VALUES (?, ?, ?)",
                (anlage, key.upper(), infos))
        else:
            self.cursor.execute(
                f"INSERT INTO {kategorie} ({meta['key']}, infos) VALUES (?, ?)",
                (key.upper(), infos))
        self.conn.commit()
        return True

    def aktualisieren(self, kategorie, key, neue_infos, anlage=None):
        meta = self._check(kategorie)
        if meta["anlage"]:
            self.cursor.execute(
                f"UPDATE {kategorie} SET infos = ?, updated = CURRENT_TIMESTAMP "
                f"WHERE anlage = ? AND {meta['key']} = ?",
                (neue_infos, anlage, key.upper()))
        else:
            self.cursor.execute(
                f"UPDATE {kategorie} SET infos = ?, updated = CURRENT_TIMESTAMP "
                f"WHERE {meta['key']} = ?",
                (neue_infos, key.upper()))
        self.conn.commit()
        return self.cursor.rowcount > 0

    def loeschen(self, kategorie, key, anlage=None):
        meta = self._check(kategorie)
        if meta["anlage"]:
            self.cursor.execute(
                f"DELETE FROM {kategorie} WHERE anlage = ? AND {meta['key']} = ?",
                (anlage, key.upper()))
        else:
            self.cursor.execute(
                f"DELETE FROM {kategorie} WHERE {meta['key']} = ?", (key.upper(),))
        self.conn.commit()
        return self.cursor.rowcount > 0

    # -- Suche über alles ---------------------------------------------------
    def suche(self, begriff):
        begriff = (begriff or "").upper()
        treffer = []
        if not begriff:
            return treffer
        for kategorie, meta in KATEGORIEN.items():
            self.cursor.execute(f"SELECT * FROM {kategorie}")
            for row in self.cursor.fetchall():
                key = row[meta["key"]] or ""
                infos = row["infos"] or ""
                if begriff in key.upper() or begriff in infos.upper():
                    treffer.append(self._row_to_dict(kategorie, row))
        return treffer

    # -- Backup -------------------------------------------------------------
    def backup(self):
        import shutil
        from datetime import datetime
        ziel = f"schumag_backup_{datetime.now():%Y%m%d_%H%M%S}.db"
        shutil.copy2(DB_NAME, ziel)
        return ziel

    def close(self):
        self.conn.close()
