#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Einmaliger Import der alten CSV-Dateien (zg21/zg23/zg24) in die Datenbank.

Logik:
- Zeilen, die mit "Durchmesser" (oder "DRM") beginnen, sind Durchmesser-
  Bereiche mit festen Spalten und wandern in die Kategorie  durchmesser.
- Alle übrigen Zeilen (SW1-Info, Sägeblattschmierung, Backen-Listen, ...)
  wandern als freier Text in  allgemeine_infos.

Der Import ist wiederholbar: vorhandene Einträge (gleiche Bezeichnung) werden
übersprungen, es entstehen also keine Doppelten.

Start:  python3 import_csv.py
"""

import csv
import os

from schumag_core import SchumagDB, felder_zu_infos

# Welche CSV gehört zu welcher Anlage?
CSV_ZU_ANLAGE = {
    "zg21data.csv": "ZG21",
    "zg23data.csv": "ZG23",
    "zg24data.csv": "ZG24",
}

# Spalten 1..6 der Durchmesser-Bereichszeilen -> Felder der Durchmesser-Vorlage
SPALTEN_ZU_FELD = {
    1: "Ziehbacken",
    2: "Rohre",
    3: "Lineale",
    4: "Trichter",
    5: "Einlaufdüse",
    6: "Scherenmesser",
}


def importiere_datei(db, datei, anlage):
    if not os.path.exists(datei):
        print(f"  übersprungen (nicht gefunden): {datei}")
        return 0, 0

    neu_durchmesser = 0
    neu_infos = 0
    with open(datei, newline="", encoding="utf-8") as f:
        for zeile in csv.reader(f):
            zellen = [z.strip() for z in zeile]
            if not zellen or not zellen[0]:
                continue
            key = zellen[0]
            kl = key.lower()

            if kl.startswith("durchmesser") or kl.startswith("drm"):
                # Bereichszeile -> Kategorie durchmesser
                werte = {}
                for idx, feld in SPALTEN_ZU_FELD.items():
                    if idx < len(zellen) and zellen[idx]:
                        werte[feld] = zellen[idx]
                infos = felder_zu_infos("durchmesser", werte)
                if db.hinzufuegen("durchmesser", key, infos, anlage):
                    neu_durchmesser += 1
            else:
                # Sonderzeile -> Kategorie allgemeine_infos (freier Text)
                rest = [z for z in zellen[1:] if z]
                infos = "\n".join(rest)
                if db.hinzufuegen("allgemeine_infos", key, infos, anlage):
                    neu_infos += 1

    return neu_durchmesser, neu_infos


def main():
    db = SchumagDB()
    try:
        print("CSV-Import startet ...\n")
        gesamt_d, gesamt_i = 0, 0
        for datei, anlage in CSV_ZU_ANLAGE.items():
            d, i = importiere_datei(db, datei, anlage)
            print(f"  {datei} -> {anlage}: {d} Durchmesser, {i} Allgemeine Infos neu")
            gesamt_d += d
            gesamt_i += i
        print(f"\nFertig. Insgesamt {gesamt_d} Durchmesser- und "
              f"{gesamt_i} Info-Einträge importiert.")
        print("(Bereits vorhandene Einträge wurden übersprungen.)")
    finally:
        db.close()


if __name__ == "__main__":
    main()
