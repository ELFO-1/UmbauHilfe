# Betrieb auf dem Server (Docker + Tailscale)

Ziel: **eine** Datenbank auf dem Pi5 als zentrale Quelle. PC-Browser,
Terminal (`cli.py`) und Handy bearbeiten alle dieselben Daten – erreichbar
**privat im eigenen Tailnet** (nicht öffentlich im Internet).

```
Handy/PWA  ─┐
PC-Browser ─┼──►  https://umbauhilfe.<tailnet>.ts.net   (Tailscale Serve)
Terminal   ─┘                 │
                              ▼
                    Container :8000  (webserver.py)
                              │
                              ▼
                    /data/schumag.db   (Volume = einzige Quelle)
```

## 1. Dateien auf den Server bringen

Den Projektordner auf den Pi kopieren (z.B. nach `~/umbauhilfe`), oder in
Portainer einen Git-Stack auf dieses Repo zeigen lassen.

## 2. Bestehende Datenbank übernehmen

Vor dem ersten Start die aktuelle DB ins Daten-Verzeichnis legen:

```bash
mkdir -p ~/umbauhilfe/data
cp schumag.db ~/umbauhilfe/data/schumag.db
```

Ohne diesen Schritt startet der Dienst mit einer **leeren** (aber voll
funktionierenden) Datenbank.

## 3. Container starten

Mit Compose:

```bash
cd ~/umbauhilfe
docker compose up -d --build
```

Oder in **Portainer**: *Stacks → Add stack*, Inhalt der `docker-compose.yml`
einfügen, deployen. Der Port ist absichtlich nur an `127.0.0.1` gebunden – im
LAN ist nichts offen, nur Tailscale kommt dran.

**Host-Port:** Standard ist 8000. Ist der belegt (auf diesem Pi z.B. durch
Portainer), den Port per `.env` neben der `docker-compose.yml` setzen:

```bash
echo "HOST_PORT=8088" > ~/umbauhilfe/.env
```

Kurz testen (auf dem Server, hier mit 8088):

```bash
curl -s localhost:8088/api/config | head -c 80
```

## 4. Per Tailscale privat erreichbar machen

Tailscale läuft bei dir bereits auf dem Pi. Einmalig den Dienst veröffentlichen
(HTTPS, nur im Tailnet sichtbar – **kein** Funnel). Hier auf eigenem HTTPS-Port
**8443**, weil Port 443 schon vom Immich-Funnel belegt ist:

```bash
sudo tailscale serve --bg --https=8443 http://127.0.0.1:8088
sudo tailscale serve status      # zeigt beide Mappings (Immich + Umbauhilfe)
```

Ergebnis ist die Adresse `https://lucy.tail14c57a.ts.net:8443/`.
Diese im Browser/Handy öffnen → Webinterface. Auf dem Handy über „Zum
Startbildschirm hinzufügen" als PWA installieren – immer live, immer dieselbe DB.

> Ist Port 443 frei, geht auch der einfache `sudo tailscale serve --bg 8088`
> (dann URL ohne Port). Funnel (öffentliches Internet) wird hier bewusst
> **nicht** benutzt.

## 5. Terminal von überall

`cli.py` läuft weiter lokal auf deinem PC, schreibt aber über die API in die
Server-DB. Nur die Server-Adresse setzen:

```bash
export SCHUMAG_API=https://lucy.tail14c57a.ts.net:8443
python3 cli.py
```

Dauerhaft (fish): `set -Ux SCHUMAG_API https://lucy.tail14c57a.ts.net:8443`.
Ohne die Variable spricht es `http://localhost:8000` an – praktisch zum lokalen
Testen.

## Updates

Vom Arbeitsrechner aus per Skript (überträgt den Code und baut neu; das
`data/`-Volume und die `.env` bleiben unberührt):

```bash
./deploy.sh
```

Oder direkt auf dem Server:

```bash
cd ~/umbauhilfe && docker compose up -d --build
```

## Backup

Menüpunkt *5 (Backup)* im Terminal oder `POST /api/backup` legt eine Kopie
**neben die DB** ab (`data/schumag_backup_<zeit>.db`). Das `data/`-Verzeichnis
zusätzlich in deine normale Server-Sicherung aufnehmen.
```
