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

Kurz testen (auf dem Server):

```bash
curl -s localhost:8000/api/config | head -c 80
```

## 4. Per Tailscale privat erreichbar machen

Tailscale läuft bei dir bereits auf dem Pi. Einmalig den Dienst veröffentlichen
(HTTPS, nur im Tailnet sichtbar – **kein** Funnel):

```bash
sudo tailscale serve --bg 8000
sudo tailscale serve status      # zeigt die URL
```

Ergebnis ist eine Adresse wie `https://<hostname>.<tailnet>.ts.net/`.
Diese im Browser/Handy öffnen → Webinterface. Auf dem Handy über „Zum
Startbildschirm hinzufügen" als PWA installieren – immer live, immer dieselbe DB.

> Funnel (öffentliches Internet) wird hier bewusst **nicht** benutzt. Falls du
> später doch öffentlichen Zugriff willst: `sudo tailscale funnel --bg 8000`.

## 5. Terminal von überall

`cli.py` läuft weiter lokal auf deinem PC, schreibt aber über die API in die
Server-DB. Nur die Server-Adresse setzen:

```bash
export SCHUMAG_API=https://<hostname>.<tailnet>.ts.net
python3 cli.py
```

(Dauerhaft z.B. in `~/.bashrc` bzw. `~/.config/fish/config.fish` setzen.)
Ohne die Variable spricht es `http://localhost:8000` an – praktisch zum lokalen
Testen.

## Updates

Code geändert? Neu bauen, die DB im `data/`-Volume bleibt erhalten:

```bash
docker compose up -d --build
```

## Backup

Menüpunkt *5 (Backup)* im Terminal oder `POST /api/backup` legt eine Kopie
**neben die DB** ab (`data/schumag_backup_<zeit>.db`). Das `data/`-Verzeichnis
zusätzlich in deine normale Server-Sicherung aufnehmen.
```
