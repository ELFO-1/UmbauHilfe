#!/usr/bin/env bash
# Spielt den aktuellen Stand auf den Server und baut den Container neu.
#
# Das Daten-Volume (data/ mit schumag.db + Backups) bleibt dabei unberührt –
# es wird weder übertragen noch gelöscht.
#
# Ziel per Umgebungsvariablen überschreibbar:
#   PI_HOST   SSH-Ziel        (Standard: lucy@192.168.0.120)
#   PI_DIR    Verzeichnis     (Standard: ~/umbauhilfe)
#
# Benutzung:
#   ./deploy.sh

set -euo pipefail

PI_HOST="${PI_HOST:-lucy@192.168.0.120}"
PI_DIR="${PI_DIR:-~/umbauhilfe}"

# Verzeichnis dieses Skripts = Projektwurzel (egal von wo aufgerufen)
SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/"

echo "==> Übertrage Code nach ${PI_HOST}:${PI_DIR}"
rsync -az --delete \
  --exclude '.git' --exclude 'node_modules' --exclude 'android' \
  --exclude '_alt_archiv' --exclude '__pycache__' --exclude 'screenshots' \
  --exclude '.claude' --exclude '*.apk' --exclude 'schumag.db.vor_import_backup' \
  --exclude 'data' --exclude '.env' \
  "${SRC}" "${PI_HOST}:${PI_DIR}/"

echo "==> Baue & starte Container neu (Daten bleiben erhalten)"
ssh "${PI_HOST}" "cd ${PI_DIR} && docker compose up -d --build"

echo "==> Status"
ssh "${PI_HOST}" "cd ${PI_DIR} && docker compose ps"

echo "==> Fertig. Erreichbar unter  https://lucy.tail14c57a.ts.net:8443"
