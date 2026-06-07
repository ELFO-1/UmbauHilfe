"use strict";
/*
 * Lokale Datenschicht für die Offline-App (Android / Browser).
 *
 * Spiegelt die Server-API (schumag_core.py / webserver.py) wider, speichert die
 * Daten aber im Gerät via IndexedDB. So funktioniert dieselbe Oberfläche
 * (app.js) auch ohne Python-Server – inklusive Bearbeiten.
 *
 * Bereitgestellt wird ein Objekt  LocalBackend  mit denselben zwei Methoden,
 * die app.js sonst gegen den Server benutzt:
 *     await LocalBackend.get(pfad)            // wie fetch(pfad).json()
 *     await LocalBackend.post(pfad, daten)    // wie fetch(pfad, {POST}).json()
 *
 * Erststart: lädt seed.json in die lokale DB. Danach lebt alles lokal.
 */

const LocalBackend = (() => {
  const DB_NAME = "wuh_local";
  const DB_VERSION = 1;
  const STORE = "eintraege";       // ein Eintrag-Objektspeicher für alle Kategorien
  const META = "meta";             // für Config + "seed schon geladen?"

  let _config = null;

  // -- IndexedDB öffnen ----------------------------------------------------
  function openDB() {
    return new Promise((resolve, reject) => {
      const req = indexedDB.open(DB_NAME, DB_VERSION);
      req.onupgradeneeded = () => {
        const db = req.result;
        if (!db.objectStoreNames.contains(STORE)) {
          // Schlüssel: kategorie|anlage|key  (anlage leer bei globalen Kat.)
          db.createObjectStore(STORE, { keyPath: "id" });
        }
        if (!db.objectStoreNames.contains(META)) {
          db.createObjectStore(META, { keyPath: "name" });
        }
      };
      req.onsuccess = () => resolve(req.result);
      req.onerror = () => reject(req.error);
    });
  }

  function tx(db, store, mode) {
    return db.transaction(store, mode).objectStore(store);
  }
  function asPromise(req) {
    return new Promise((resolve, reject) => {
      req.onsuccess = () => resolve(req.result);
      req.onerror = () => reject(req.error);
    });
  }

  // -- Schlüssel/Helfer ----------------------------------------------------
  function makeId(kategorie, anlage, key) {
    return kategorie + "|" + (anlage || "") + "|" + (key || "").toUpperCase();
  }
  function jetzt() {
    // Format wie SQLite CURRENT_TIMESTAMP: "YYYY-MM-DD HH:MM:SS" (lokale Zeit)
    const d = new Date();
    const p = (n) => String(n).padStart(2, "0");
    return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ` +
           `${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}`;
  }
  function felderZuInfos(kategorie, felderWerte) {
    const felder = _config.kategorien[kategorie].felder || [];
    return felder.map((name) => `${name}: ${felderWerte[name] || ""}`).join("\n");
  }
  function infosZuFelder(kategorie, infos) {
    const felder = _config.kategorien[kategorie].felder || [];
    const erg = {};
    felder.forEach((n) => (erg[n] = ""));
    (infos || "").split("\n").forEach((zeile) => {
      const idx = zeile.indexOf(": ");
      if (idx >= 0) {
        const name = zeile.slice(0, idx);
        if (name in erg) erg[name] = zeile.slice(idx + 2);
      }
    });
    return erg;
  }
  function eintragAusgabe(kategorie, rec) {
    const meta = _config.kategorien[kategorie];
    const d = { kategorie, key: rec.key, infos: rec.infos, updated: rec.updated };
    if (meta.anlage) d.anlage = rec.anlage;
    if (meta.felder) d.felder = infosZuFelder(kategorie, rec.infos);
    return d;
  }

  // -- Erstbefüllung aus seed.json ----------------------------------------
  async function init() {
    const db = await openDB();
    const geladen = await asPromise(tx(db, META, "readonly").get("seed_geladen"));

    // Die CONFIG (Anlagen/Kategorien/Felder) folgt IMMER der App-Version aus
    // seed.json – so erscheinen neue Kategorien/Felder auch nach einem Update,
    // ohne die App-Daten zu löschen. Die DATEN werden dagegen nur EINMAL
    // eingespielt (seed_geladen), damit eigene Eingaben erhalten bleiben.
    let seed = null;
    try {
      seed = await (await fetch("seed.json")).json();
    } catch (e) {
      // Offline ohne gebündelte seed.json: gespeicherte Config weiterverwenden.
    }

    if (seed) {
      _config = seed.config;
      await asPromise(tx(db, META, "readwrite").put({ name: "config", value: _config }));
    } else {
      const cfgRec = await asPromise(tx(db, META, "readonly").get("config"));
      _config = cfgRec ? cfgRec.value : null;
    }

    if (geladen) return;   // Daten bereits vorhanden -> nicht erneut seeden

    // Erstbefüllung der Einträge aus seed.json.
    const store = tx(db, STORE, "readwrite");
    for (const e of (seed ? seed.eintraege : [])) {
      const rec = {
        id: makeId(e.kategorie, e.anlage, e.key),
        kategorie: e.kategorie,
        anlage: e.anlage || "",
        key: e.key,
        infos: e.infos || "",
        updated: e.updated || jetzt(),
      };
      store.put(rec);
    }
    await asPromise(tx(db, META, "readwrite").put({ name: "seed_geladen", value: true }));
  }

  // -- Lesezugriffe --------------------------------------------------------
  async function liste(kategorie, anlage) {
    const db = await openDB();
    const alle = await asPromise(tx(db, STORE, "readonly").getAll());
    const meta = _config.kategorien[kategorie];
    return alle
      .filter((r) => r.kategorie === kategorie &&
                     (!meta.anlage || r.anlage === (anlage || "")))
      .sort((a, b) => a.key.localeCompare(b.key))
      .map((r) => eintragAusgabe(kategorie, r));
  }

  async function hole(kategorie, key, anlage) {
    const db = await openDB();
    const rec = await asPromise(
      tx(db, STORE, "readonly").get(makeId(kategorie, anlage, key)));
    return rec ? eintragAusgabe(kategorie, rec) : null;
  }

  async function suche(begriff) {
    begriff = (begriff || "").toUpperCase();
    if (!begriff) return [];
    const db = await openDB();
    const alle = await asPromise(tx(db, STORE, "readonly").getAll());
    return alle
      .filter((r) => (r.key || "").toUpperCase().includes(begriff) ||
                     (r.infos || "").toUpperCase().includes(begriff))
      .map((r) => eintragAusgabe(r.kategorie, r));
  }

  // -- Schreibzugriffe -----------------------------------------------------
  async function hinzufuegen(kategorie, key, infos, anlage) {
    if (!key || !key.trim()) return { ok: false, fehler: "Bezeichnung fehlt" };
    const db = await openDB();
    const id = makeId(kategorie, anlage, key);
    const vorhanden = await asPromise(tx(db, STORE, "readonly").get(id));
    if (vorhanden) return { ok: false, fehler: "Eintrag existiert bereits" };
    await asPromise(tx(db, STORE, "readwrite").put({
      id, kategorie, anlage: anlage || "", key: key.toUpperCase(),
      infos: infos || "", updated: jetzt(),
    }));
    return { ok: true, fehler: null };
  }

  async function aktualisieren(kategorie, key, infos, anlage) {
    const db = await openDB();
    const id = makeId(kategorie, anlage, key);
    const rec = await asPromise(tx(db, STORE, "readonly").get(id));
    if (!rec) return { ok: false };
    rec.infos = infos || "";
    rec.updated = jetzt();
    await asPromise(tx(db, STORE, "readwrite").put(rec));
    return { ok: true };
  }

  async function loeschen(kategorie, key, anlage) {
    const db = await openDB();
    await asPromise(tx(db, STORE, "readwrite").delete(makeId(kategorie, anlage, key)));
    return { ok: true };
  }

  // -- Router: bildet die Server-API nach ----------------------------------
  function parse(pfad) {
    const u = new URL(pfad, "http://local");
    const p = (k) => u.searchParams.get(k);
    return { path: u.pathname, p };
  }

  async function get(pfad) {
    if (!_config) await init();
    const { path, p } = parse(pfad);
    if (path === "/api/config") return _config;
    if (path === "/api/list") return liste(p("kat"), p("anlage"));
    if (path === "/api/get") return (await hole(p("kat"), p("key"), p("anlage"))) || {};
    if (path === "/api/search") return suche(p("q"));
    return { fehler: "Unbekannter Endpunkt" };
  }

  function infosAus(kategorie, daten) {
    if (_config.kategorien[kategorie].felder && "felder" in daten) {
      return felderZuInfos(kategorie, daten.felder || {});
    }
    return daten.infos || "";
  }

  async function post(pfad, daten) {
    if (!_config) await init();
    const { path } = parse(pfad);
    const kat = daten.kat;
    if (path === "/api/add")
      return hinzufuegen(kat, daten.key || "", infosAus(kat, daten), daten.anlage);
    if (path === "/api/update")
      return aktualisieren(kat, daten.key || "", infosAus(kat, daten), daten.anlage);
    if (path === "/api/delete")
      return loeschen(kat, daten.key || "", daten.anlage);
    if (path === "/api/backup")
      return { ok: false, fehler: "Backup in der App nicht verfügbar" };
    return { fehler: "Unbekannter Endpunkt" };
  }

  return { get, post, init };
})();
