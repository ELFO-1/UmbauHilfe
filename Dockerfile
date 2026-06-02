# Wieland-Umbau-Hilfe – Webserver (REST-API + Webinterface/PWA)
# Reine Python-Standardbibliothek, daher genügt das schlanke Slim-Image.
# Multi-Arch: läuft auch auf arm64 (Raspberry Pi 5).
FROM python:3.12-slim

WORKDIR /app

# Nur das, was der Server zum Laufen braucht. cli.py & Co. werden hier nicht
# benötigt (das Terminal läuft beim Nutzer und spricht die API über das Netz).
COPY schumag_core.py webserver.py ./
COPY static/ ./static/

# DB liegt im gemounteten Volume, nicht im Image.
ENV SCHUMAG_DB=/data/schumag.db
VOLUME ["/data"]

EXPOSE 8000

CMD ["python3", "webserver.py"]
