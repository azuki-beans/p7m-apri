FROM python:3.12-slim

# openssl è l'unica dipendenza di sistema necessaria all'estrazione.
RUN apt-get update \
    && apt-get install -y --no-install-recommends openssl \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DJANGO_DB_PATH=/data/db.sqlite3 \
    TRUST_LIST_CACHE_DIR=/data/trust-lists

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Il DB SQLite vive in /data così da poter essere montato come volume.
RUN mkdir -p /data
VOLUME /data

# In locale ascolta sulla 8000; su Cloud Run (e simili) si adatta a $PORT.
EXPOSE 8000

CMD ["sh", "-c", "python manage.py migrate --noinput && exec gunicorn config.wsgi:application -b 0.0.0.0:${PORT:-8000} --workers 2 --timeout 120"]
