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
