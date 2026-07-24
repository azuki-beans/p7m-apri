FROM python:3.14-slim

# openssl: estrazione dei .p7m. Le librerie Pango/Cairo/HarfBuzz (+font)
# servono a WeasyPrint per rendere in PDF le fatture elettroniche.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        openssl \
        libpango-1.0-0 \
        libpangocairo-1.0-0 \
        libpangoft2-1.0-0 \
        libharfbuzz0b \
        libffi8 \
        shared-mime-info \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DJANGO_DB_PATH=/data/db.sqlite3 \
    TRUST_LIST_CACHE_DIR=/data/trust-lists \
    POETRY_VERSION=2.2.1 \
    POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_CREATE=false

# Poetry gestisce le dipendenze (pyproject.toml + poetry.lock); niente virtualenv
# nel container, installa direttamente nel Python di sistema.
RUN pip install --no-cache-dir "poetry==${POETRY_VERSION}"

WORKDIR /app

COPY pyproject.toml poetry.lock ./
RUN poetry install --only main --no-root

COPY . .

# Il DB SQLite vive in /data così da poter essere montato come volume.
RUN mkdir -p /data
VOLUME /data

# In locale ascolta sulla 8000; su Cloud Run (e simili) si adatta a $PORT.
EXPOSE 8000

CMD ["sh", "-c", "python manage.py migrate --noinput && exec gunicorn config.wsgi:application -b 0.0.0.0:${PORT:-8000} --workers 2 --timeout 120"]
