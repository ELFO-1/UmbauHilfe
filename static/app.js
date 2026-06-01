"use strict";

// ---------------------------------------------------------------------------
// Backend-Wahl: lokal (Offline-App) oder Server (PC/Web)
// ---------------------------------------------------------------------------
// Lokal wird benutzt, wenn ...
//   - die App in Capacitor läuft (capacitor:// oder file://), ODER
//   - die URL  ?local=1  enthält (zum Testen im normalen Browser).
// Sonst (normaler Aufruf von webserver.py) wird der Server per fetch benutzt.
const USE_LOCAL =
    (window.Capacitor && window.Capacitor.isNativePlatform && window.Capacitor.isNativePlatform()) ||
    location.protocol === "capacitor:" ||
    location.protocol === "file:" ||
    new URLSearchParams(location.search).get("local") === "1" ||
    window.__FORCE_LOCAL__ === true;

// ---------------------------------------------------------------------------
// Kleine Helfer
// ---------------------------------------------------------------------------
async function apiGet(pfad) {
    if (USE_LOCAL) return LocalBackend.get(pfad);
    const r = await fetch(pfad);
    return r.json();
}
async function apiPost(pfad, daten) {
    if (USE_LOCAL) return LocalBackend.post(pfad, daten);
    const r = await fetch(pfad, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(daten),
    });
    return r.json();
}
function esc(s) {
    return (s ?? "").toString()
        .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}
function qs(name) {
    return new URLSearchParams(location.search).get(name);
}

let CONFIG = null;

// ---------------------------------------------------------------------------
// Startseite (index.html)
// ---------------------------------------------------------------------------
async function initIndex() {
    CONFIG = await apiGet("/api/config");

    // Anlagen nach Gruppe sortiert anzeigen
    const gruppen = {};
    for (const [name, meta] of Object.entries(CONFIG.anlagen)) {
        (gruppen[meta.gruppe] = gruppen[meta.gruppe] || []).push(name);
    }
    const bereich = document.getElementById("anlagen-bereich");
    let html = "";
    for (const [gruppe, namen] of Object.entries(gruppen)) {
        html += `<h2 class="gruppe-titel">${esc(gruppe)}</h2><div class="button-grid">`;
        for (const name of namen) {
            html += `<a href="anlage.html?a=${encodeURIComponent(name)}"><button>${esc(name)}</button></a>`;
        }
        html += `</div>`;
    }
    bereich.innerHTML = html;

    // Suche
    const feld = document.getElementById("suchfeld");
    const starten = () => sucheStarten(feld.value);
    document.getElementById("such-btn").addEventListener("click", starten);
    feld.addEventListener("keydown", (e) => { if (e.key === "Enter") starten(); });
}

async function sucheStarten(begriff) {
    const ziel = document.getElementById("suchergebnisse");
    if (!begriff.trim()) { ziel.innerHTML = ""; return; }
    const treffer = await apiGet("/api/search?q=" + encodeURIComponent(begriff));
    if (!treffer.length) {
        ziel.innerHTML = `<div class="karte">Keine Treffer für „${esc(begriff)}“.</div>`;
        return;
    }
    ziel.innerHTML = treffer.map((t) => {
        const ort = CONFIG.kategorien[t.kategorie].label + (t.anlage ? " / " + t.anlage : "");
        return `<div class="karte">
            <h3>${esc(t.key)}</h3>
            <div class="meta">${esc(ort)} · Stand ${esc(t.updated)}</div>
            <pre>${esc(t.infos)}</pre>
        </div>`;
    }).join("");
}

// ---------------------------------------------------------------------------
// Anlagen-/Kategorie-Seite (anlage.html)
// ---------------------------------------------------------------------------
let AKTUELLE_ANLAGE = null;   // z.B. "ZG21" oder null bei globalen Kategorien
let AKTUELLE_KAT = null;

async function initAnlage() {
    CONFIG = await apiGet("/api/config");

    const anlage = qs("a");
    const global = qs("global");
    let kategorien;

    if (global) {
        AKTUELLE_ANLAGE = null;
        kategorien = [global];
        document.getElementById("titel").textContent = CONFIG.kategorien[global].label;
    } else {
        AKTUELLE_ANLAGE = anlage;
        const meta = CONFIG.anlagen[anlage];
        if (!meta) {
            document.getElementById("titel").textContent = "Unbekannte Anlage";
            return;
        }
        kategorien = meta.kategorien;
        document.getElementById("titel").textContent =
            `Umbau Hilfe für ${anlage} (${meta.gruppe})`;
    }

    // Tabs
    const tabs = document.getElementById("tabs");
    tabs.innerHTML = kategorien.map((k) =>
        `<button data-kat="${k}">${esc(CONFIG.kategorien[k].label)}</button>`).join("");
    tabs.querySelectorAll("button").forEach((b) =>
        b.addEventListener("click", () => kategorieWaehlen(b.dataset.kat)));

    kategorieWaehlen(kategorien[0]);
}

function kategorieWaehlen(kat) {
    AKTUELLE_KAT = kat;
    document.querySelectorAll("#tabs button").forEach((b) =>
        b.classList.toggle("aktiv", b.dataset.kat === kat));
    formularZeigen();           // leeres "Hinzufügen"-Formular
    listeLaden();
}

// -- Formular (Hinzufügen / Bearbeiten) -------------------------------------
function felderInputs(kat, werte) {
    werte = werte || {};
    const felder = CONFIG.kategorien[kat].felder;
    if (felder) {
        return felder.map((f) =>
            `<label>${esc(f)}</label>
             <input data-feld="${esc(f)}" value="${esc(werte[f] || "")}">`).join("");
    }
    return `<label>Informationen</label>
            <textarea data-infos>${esc(werte.__infos || "")}</textarea>`;
}

function formularZeigen(eintrag) {
    const kat = AKTUELLE_KAT;
    const bearbeiten = !!eintrag;
    const keyLabel = CONFIG.kategorien[kat].label;

    let werte = {};
    if (bearbeiten) {
        werte = eintrag.felder || {};
        if (!CONFIG.kategorien[kat].felder) werte = { __infos: eintrag.infos || "" };
    }

    const bereich = document.getElementById("formular-bereich");
    bereich.innerHTML = `
        <div class="formular">
            <h3>${bearbeiten ? "Eintrag bearbeiten" : "Neuer Eintrag"}</h3>
            <label>Bezeichnung</label>
            <input id="feld-key" value="${bearbeiten ? esc(eintrag.key) : ""}"
                   ${bearbeiten ? "readonly" : ""} placeholder="${esc(keyLabel)} ...">
            <div id="feld-infos">${felderInputs(kat, werte)}</div>
            <div class="aktionen">
                <button id="speichern-btn">Speichern</button>
                ${bearbeiten ? '<button id="abbrechen-btn" class="sekundaer">Abbrechen</button>' : ""}
            </div>
        </div>`;

    document.getElementById("speichern-btn").addEventListener("click", () =>
        speichern(bearbeiten));
    if (bearbeiten) {
        document.getElementById("abbrechen-btn").addEventListener("click", () =>
            formularZeigen());
    }
}

function formularDatenLesen() {
    const kat = AKTUELLE_KAT;
    const daten = { kat, key: document.getElementById("feld-key").value };
    if (AKTUELLE_ANLAGE) daten.anlage = AKTUELLE_ANLAGE;

    if (CONFIG.kategorien[kat].felder) {
        const felder = {};
        document.querySelectorAll("#feld-infos input[data-feld]").forEach((i) =>
            felder[i.dataset.feld] = i.value);
        daten.felder = felder;
    } else {
        daten.infos = document.querySelector("#feld-infos textarea[data-infos]").value;
    }
    return daten;
}

async function speichern(bearbeiten) {
    const daten = formularDatenLesen();
    if (!daten.key.trim()) { alert("Bitte eine Bezeichnung eingeben."); return; }
    const antwort = await apiPost(bearbeiten ? "/api/update" : "/api/add", daten);
    if (antwort.ok) {
        formularZeigen();        // zurück zum leeren Formular
        listeLaden();
    } else {
        alert(antwort.fehler || "Speichern fehlgeschlagen.");
    }
}

// -- Liste ------------------------------------------------------------------
async function listeLaden() {
    const kat = AKTUELLE_KAT;
    let pfad = "/api/list?kat=" + encodeURIComponent(kat);
    if (AKTUELLE_ANLAGE) pfad += "&anlage=" + encodeURIComponent(AKTUELLE_ANLAGE);
    const eintraege = await apiGet(pfad);

    const bereich = document.getElementById("liste-bereich");
    if (!eintraege.length) {
        bereich.innerHTML = `<div class="hinweis">Noch keine Einträge.</div>`;
        return;
    }
    bereich.innerHTML = eintraege.map((e, i) => `
        <div class="karte">
            <h3>${esc(e.key)}</h3>
            <div class="meta">Stand ${esc(e.updated)}</div>
            <pre>${esc(e.infos)}</pre>
            <div class="aktionen">
                <button class="sekundaer" data-edit="${i}">Bearbeiten</button>
                <button class="gefahr" data-del="${i}">Löschen</button>
            </div>
        </div>`).join("");

    bereich.querySelectorAll("[data-edit]").forEach((b) =>
        b.addEventListener("click", () => {
            formularZeigen(eintraege[b.dataset.edit]);
            window.scrollTo({ top: 0, behavior: "smooth" });
        }));
    bereich.querySelectorAll("[data-del]").forEach((b) =>
        b.addEventListener("click", () => loeschen(eintraege[b.dataset.del])));
}

async function loeschen(eintrag) {
    if (!confirm(`Eintrag „${eintrag.key}“ wirklich löschen?`)) return;
    const daten = { kat: AKTUELLE_KAT, key: eintrag.key };
    if (AKTUELLE_ANLAGE) daten.anlage = AKTUELLE_ANLAGE;
    const antwort = await apiPost("/api/delete", daten);
    if (antwort.ok) listeLaden();
    else alert("Löschen fehlgeschlagen.");
}

// ---------------------------------------------------------------------------
// PWA: Service-Worker registrieren (macht die App installierbar/offline-fähig)
// ---------------------------------------------------------------------------
// In der nativen App nicht nötig (Dateien sind eingebaut) und könnte beim
// Update alte Dateien cachen -> nur im echten Browser/PWA registrieren.
if ("serviceWorker" in navigator && !USE_LOCAL) {
    window.addEventListener("load", () => {
        navigator.serviceWorker.register("service-worker.js").catch((e) =>
            console.warn("Service-Worker konnte nicht registriert werden:", e));
    });
}

// ---------------------------------------------------------------------------
// Start
// ---------------------------------------------------------------------------
if (document.body.dataset.page === "index") initIndex();
else if (document.body.dataset.page === "anlage") initAnlage();
