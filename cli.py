#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Terminal-Programm der Wieland-Umbau-Hilfe.

Benutzt die gemeinsame Datenschicht aus schumag_core.py – also dieselbe
Datenbank wie das Webinterface. Generisch über alle Kategorien, mit
geführter Feld-für-Feld-Eingabe (z.B. Durchmesser, Sonderlegierungen),
Suche, Backup und Löschen.

Start:  python3 cli.py
"""

from time import sleep

from schumag_core import (
    SchumagDB, KATEGORIEN, ANLAGEN, GLOBALE_KATEGORIEN,
    felder_zu_infos, infos_zu_felder,
)

# colorama ist optional – ohne läuft es einfach ohne Farben.
try:
    from colorama import init, Fore, Style
    init()

    def farbe(text, color):
        codes = {"red": Fore.RED, "green": Fore.GREEN, "yellow": Fore.YELLOW,
                 "blue": Fore.BLUE, "cyan": Fore.CYAN}
        return f"{codes.get(color, '')}{text}{Style.RESET_ALL}"
except ImportError:
    def farbe(text, color):
        return text


# ---------------------------------------------------------------------------
# Eingabe-Helfer
# ---------------------------------------------------------------------------

def infos_eingeben(kategorie, vorbelegung=None):
    """Fragt die Infos ab – feldweise, wenn die Kategorie Felder hat."""
    felder = KATEGORIEN[kategorie]["felder"]
    if felder:
        vorbelegung = vorbelegung or {}
        werte = {}
        for name in felder:
            alt = vorbelegung.get(name, "")
            hinweis = f" [{alt}]" if alt else ""
            eingabe = input(f"  {name}{hinweis}: ")
            werte[name] = eingabe if eingabe else alt
        return felder_zu_infos(kategorie, werte)
    else:
        return input("  Informationen: ")


def eintrag_anzeigen(eintrag):
    print(farbe(f"\n{eintrag['key']}", "yellow"))
    print(eintrag["infos"] or "(keine Infos)")
    print(farbe(f"Letztes Update: {eintrag['updated']}", "cyan"))


# ---------------------------------------------------------------------------
# Kategorie-Menü (für alle Kategorien gleich)
# ---------------------------------------------------------------------------

def kategorie_menue(db, kategorie, anlage=None):
    label = KATEGORIEN[kategorie]["label"]
    while True:
        print(farbe(f"\n— {label}" + (f" / {anlage}" if anlage else "") + " —", "green"))
        print("1 : Alle anzeigen")
        print("2 : Suchen")
        print("3 : Hinzufügen")
        print("4 : Bearbeiten")
        print("5 : Löschen")
        print("z : Zurück")
        wahl = input("\nAuswahl: ").strip().lower()

        if wahl == "1":
            eintraege = db.liste(kategorie, anlage)
            if eintraege:
                for e in eintraege:
                    eintrag_anzeigen(e)
            else:
                print("Keine Einträge gefunden.")
            input("\nEnter zum Fortfahren ...")

        elif wahl == "2":
            key = input("Bezeichnung: ")
            e = db.hole(kategorie, key, anlage)
            if e:
                eintrag_anzeigen(e)
            else:
                print("Nicht gefunden.")
            sleep(1)

        elif wahl == "3":
            key = input("Bezeichnung: ")
            if not key.strip():
                print("Abgebrochen.")
                continue
            infos = infos_eingeben(kategorie)
            if db.hinzufuegen(kategorie, key, infos, anlage):
                print(farbe("Hinzugefügt.", "green"))
            else:
                print(farbe("Existiert bereits – nichts geändert.", "red"))
            sleep(1)

        elif wahl == "4":
            key = input("Bezeichnung: ")
            e = db.hole(kategorie, key, anlage)
            if not e:
                print("Nicht gefunden.")
                sleep(1)
                continue
            print("Aktuelle Infos:")
            print(e["infos"])
            vorbelegung = infos_zu_felder(kategorie, e["infos"])
            neue_infos = infos_eingeben(kategorie, vorbelegung)
            if db.aktualisieren(kategorie, key, neue_infos, anlage):
                print(farbe("Aktualisiert.", "green"))
            else:
                print(farbe("Fehler beim Aktualisieren.", "red"))
            sleep(1)

        elif wahl == "5":
            key = input("Zu löschende Bezeichnung: ")
            if not db.hole(kategorie, key, anlage):
                print("Nicht gefunden.")
                sleep(1)
                continue
            if input(f"Wirklich '{key}' löschen? (j/n): ").strip().lower() == "j":
                db.loeschen(kategorie, key, anlage)
                print(farbe("Gelöscht.", "green"))
            sleep(1)

        elif wahl == "z":
            break


# ---------------------------------------------------------------------------
# Anlagen-Auswahl
# ---------------------------------------------------------------------------

def anlage_menue(db, anlage):
    kategorien = ANLAGEN[anlage]["kategorien"]
    while True:
        print(farbe(f"\nAnlage {anlage} ({ANLAGEN[anlage]['gruppe']})", "yellow"))
        for i, kat in enumerate(kategorien, start=1):
            print(f"{i} : {KATEGORIEN[kat]['label']}")
        print("z : Zurück")
        wahl = input("\nAuswahl: ").strip().lower()
        if wahl == "z":
            break
        if wahl.isdigit() and 1 <= int(wahl) <= len(kategorien):
            kategorie_menue(db, kategorien[int(wahl) - 1], anlage)


def anlage_auswahl(db):
    anlagen = list(ANLAGEN.keys())
    while True:
        print("\nVerfügbare Anlagen:")
        for i, name in enumerate(anlagen, start=1):
            print(f"{i} : {name}  ({ANLAGEN[name]['gruppe']})")
        print("z : Zurück")
        wahl = input("\nAuswahl: ").strip().lower()
        if wahl == "z":
            break
        if wahl.isdigit() and 1 <= int(wahl) <= len(anlagen):
            anlage_menue(db, anlagen[int(wahl) - 1])


# ---------------------------------------------------------------------------
# Globale Aktionen
# ---------------------------------------------------------------------------

def anlagen_uebersicht():
    print("\nAnlagenübersicht:")
    gruppen = {}
    for name, meta in ANLAGEN.items():
        gruppen.setdefault(meta["gruppe"], []).append(name)
    for gruppe, namen in gruppen.items():
        print(f"  {gruppe}: {', '.join(namen)}")
    input("\nEnter zum Fortfahren ...")


def meta_suche(db):
    begriff = input("\nSuchbegriff: ")
    treffer = db.suche(begriff)
    if not treffer:
        print("Keine Treffer.")
    else:
        for t in treffer:
            ort = f"{KATEGORIEN[t['kategorie']]['label']}"
            if "anlage" in t:
                ort += f" / {t['anlage']}"
            print(farbe(f"\n[{ort}] {t['key']}", "yellow"))
            print(t["infos"] or "(keine Infos)")
            print("-" * 40)
    input("\nEnter zum Fortfahren ...")


# ---------------------------------------------------------------------------
# Hauptmenü
# ---------------------------------------------------------------------------

def hauptmenue():
    print("\n╔════════════════════════════════════════╗")
    print("║        Wieland Umbau Hilfe (DB)        ║")
    print("║        Schumag Anlagen   v1.0          ║")
    print("╚════════════════════════════════════════╝")
    print("\n1 : Anlagenübersicht")
    print("2 : Anlage auswählen")
    print("3 : Meta-Suche (alles durchsuchen)")
    print("4 : Sonderlegierungen")
    print("5 : Backup erstellen")
    print("q : Beenden")
    return input("\nAuswahl: ").strip().lower()


def main():
    db = SchumagDB()
    try:
        while True:
            wahl = hauptmenue()
            if wahl == "1":
                anlagen_uebersicht()
            elif wahl == "2":
                anlage_auswahl(db)
            elif wahl == "3":
                meta_suche(db)
            elif wahl == "4":
                kategorie_menue(db, GLOBALE_KATEGORIEN[0])
            elif wahl == "5":
                ziel = db.backup()
                print(farbe(f"Backup erstellt: {ziel}", "green"))
                sleep(1)
            elif wahl == "q":
                print("Beendet.")
                break
            else:
                print("Ungültige Eingabe!")
                sleep(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
