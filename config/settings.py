"""Impostazioni Django minimali per p7m-apri."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY", "dev-insecure-key-change-me-in-produzione"
)
DEBUG = os.environ.get("DJANGO_DEBUG", "0") == "1"
ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "*").split(",")

CSRF_TRUSTED_ORIGINS = [
    o for o in os.environ.get("CSRF_TRUSTED_ORIGINS", "").split(",") if o
]

INSTALLED_APPS = [
    "converter",
]

# Analytics opzionale (Umami): se entrambe le variabili sono valorizzate, la
# home page carica lo script. Vuote = nessun tracciamento.
UMAMI_SRC = os.environ.get("UMAMI_SRC", "")
UMAMI_WEBSITE_ID = os.environ.get("UMAMI_WEBSITE_ID", "")

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {"context_processors": []},
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": os.environ.get("DJANGO_DB_PATH", BASE_DIR / "db.sqlite3"),
    }
}

# I file caricati/estratti restano in memoria/DB: nessuna scrittura su disco.
DATA_UPLOAD_MAX_MEMORY_SIZE = 50 * 1024 * 1024  # 50 MB
FILE_UPLOAD_MAX_MEMORY_SIZE = 50 * 1024 * 1024

# Validazione eIDAS opzionale (converter.validation): cache su disco delle EU
# Trusted List e modalità di controllo revoca.
TRUST_LIST_CACHE_DIR = os.environ.get(
    "TRUST_LIST_CACHE_DIR", str(BASE_DIR / "trust-lists")
)
# 'soft-fail' (default): la revoca non raggiungibile non invalida la firma.
# 'hard-fail' / 'require': più rigorose, richiedono CRL/OCSP raggiungibili.
SIGNATURE_REVOCATION_MODE = os.environ.get(
    "SIGNATURE_REVOCATION_MODE", "soft-fail"
)
# Tolleranza temporale (in secondi) usata nei controlli di revoca OCSP/CRL.
# pyHanko di default tollera 1s: se l'orologio del server è indietro rispetto
# all'ora reale, una risposta OCSP appena emessa sembra "troppo recente" e la
# validazione fallisce. Un valore generoso assorbe piccoli sfasamenti di clock.
# La cura vera resta sincronizzare l'orologio del server (NTP).
SIGNATURE_TIME_TOLERANCE = int(
    os.environ.get("SIGNATURE_TIME_TOLERANCE", "60")
)
# Limita le EU Trusted List ai paesi indicati (codici ISO separati da virgola,
# es. "IT,FR"). Default "IT": l'app valida firme italiane, così la prima
# validazione è molto più rapida. pyHanko vuole un set di codici MAIUSCOLI;
# set vuoto (env vuota) = scarica tutte le liste UE.
TRUST_LIST_TERRITORIES = {
    t.strip().upper()
    for t in os.environ.get("TRUST_LIST_TERRITORIES", "IT").split(",")
    if t.strip()
}

LANGUAGE_CODE = "it-it"
TIME_ZONE = "Europe/Rome"
USE_I18N = True
USE_TZ = True

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
