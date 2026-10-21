# --- Stage 1: dipendenze Python in un virtualenv isolato ---------------------
# Poetry serve solo qui: nell'immagine finale si copia il venv già pronto, così
# Poetry e le sue dipendenze (~50 MB) non arrivano in produzione.
FROM python:3.14-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    POETRY_VERSION=2.5.1 \
    POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_CREATE=false \
    POETRY_CACHE_DIR=/tmp/poetry_cache \
    VIRTUAL_ENV=/opt/venv \
    PATH=/opt/venv/bin:$PATH

RUN pip install "poetry==${POETRY_VERSION}" \
    && python -m venv --without-pip "$VIRTUAL_ENV"

WORKDIR /app
COPY pyproject.toml poetry.lock ./
# Con il venv attivo (VIRTUAL_ENV + PATH) Poetry installa lì dentro.
# Le traduzioni di Django (~20 MB) servono solo in italiano: si tengono it/en.
RUN poetry install --only main --no-root --no-ansi \
    && rm -rf "$POETRY_CACHE_DIR" \
    && find "$VIRTUAL_ENV"/lib/python*/site-packages/django -type d \
        -path "*/locale/*" ! -path "*/locale/*/*" ! -name it ! -name en -prune -exec rm -rf {} +

# --- Stage 2: runtime ---------------------------------------------------------
FROM python:3.14-slim

# openssl: estrazione dei .p7m. Pango + HarfBuzz (+font) servono a WeasyPrint
# per rendere in PDF le fatture elettroniche (elenco minimo della doc ufficiale:
# niente Cairo, WeasyPrint non lo usa più).
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        openssl \
        libpango-1.0-0 \
        libpangoft2-1.0-0 \
        libharfbuzz-subset0 \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH=/opt/venv/bin:$PATH \
    DJANGO_DB_PATH=/data/db.sqlite3 \
    TRUST_LIST_CACHE_DIR=/data/trust-lists

COPY --from=builder /opt/venv /opt/venv

WORKDIR /app
COPY . .

# Il DB SQLite vive in /data così da poter essere montato come volume.
RUN mkdir -p /data
VOLUME /data

# In locale ascolta sulla 8000; su Cloud Run (e simili) si adatta a $PORT.
EXPOSE 8000

CMD ["sh", "-c", "python manage.py migrate --noinput && exec gunicorn config.wsgi:application -b 0.0.0.0:${PORT:-8000} --workers 2 --timeout 120"]
