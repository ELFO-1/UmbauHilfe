#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Erzeugt  static/seed.json  aus der aktuellen Datenbank.

Diese Datei ist die "Erstbefüllung" für die Offline-Android-App: beim ersten
Start lädt die App daraus ihre lokale Datenbank (IndexedDB). Danach lebt die
App-Datenbank auf dem Gerät und wird dort bearbeitet.

seed.json enthält:
  - "config"   : Anlagen / Kategorien / Felder (Quelle der Wahrheit = schumag_core.py)
  - "eintraege": alle vorhandenen Datensätze aus allen Kategorie-Tabellen

Vor jedem App-Build neu ausführen, damit der eingebaute Datenstand aktuell ist:
    python3 export_seed.py
"""

import json
import os

from schumag_core import SchumagDB, KATEGORIEN, ANLAGEN, GLOBALE_KATEGORIEN

ZIEL = os.path.join("static", "seed.json")


def main():
    db = SchumagDB()
    try:
        eintraege = []
        for kategorie, meta in KATEGORIEN.items():
            db.cursor.execute(f"SELECT * FROM {kategorie}")
            for row in db.cursor.fetchall():
                eintrag = {
                    "kategorie": kategorie,
                    "key": row[meta["key"]],
                    "infos": row["infos"] or "",
                    "updated": row["updated"],
                }
                if meta["anlage"]:
                    eintrag["anlage"] = row["anlage"]
                eintraege.append(eintrag)

        daten = {
            "config": {
                "anlagen": ANLAGEN,
                "kategorien": KATEGORIEN,
                "globale_kategorien": GLOBALE_KATEGORIEN,
            },
            "eintraege": eintraege,
        }

        with open(ZIEL, "w", encoding="utf-8") as f:
            json.dump(daten, f, ensure_ascii=False, indent=2)

        print(f"{ZIEL} geschrieben: {len(eintraege)} Einträge.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
