# p7m-apri

Estrae il file originale (tipicamente un PDF) da file `.p7m`, cioè documenti
firmati digitalmente in formato CMS/PKCS#7 — comuni in Italia per i documenti
con valore legale. Web app minimale: carichi un `.p7m`, l'app estrae il
documento, verifica la firma e te lo fa scaricare al volo.

Nessun file viene conservato: le conversioni sono cancellate dopo un'ora.

## Come funziona

Sotto il cofano è una sola chiamata a OpenSSL:

```bash
openssl smime -verify -in documento.pdf.p7m -inform DER -noverify -out documento.pdf
```

`-noverify` salta la validazione della catena CA (estrae il contenuto senza
bisogno dei certificati root), ma l'integrità della firma viene comunque
verificata.

## Eseguire l'immagine pubblica

L'immagine è pubblicata su GitHub Container Registry: non serve clonare né
buildare nulla.

```bash
# Docker
docker run --rm -p 8000:8000 -v p7m-apri-data:/data ghcr.io/azuki-beans/p7m-apri:latest

# Podman
podman run --rm -p 8000:8000 -v p7m-apri-data:/data ghcr.io/azuki-beans/p7m-apri:latest
```

Poi apri <http://localhost:8000>.

## Clonare e buildare in locale

```bash
git clone https://github.com/azuki-beans/p7m-apri.git
cd p7m-apri

docker build -t p7m-apri .
docker run --rm -p 8000:8000 -v p7m-apri-data:/data p7m-apri
# con Podman: podman build -t p7m-apri . && podman run --rm -p 8000:8000 -v p7m-apri-data:/data p7m-apri
```

Poi apri <http://localhost:8000>.

## Deploy con Docker Compose

Per metterlo su un server, usando l'immagine pubblica:

```bash
git clone https://github.com/azuki-beans/p7m-apri.git
cd p7m-apri

cp .env.example .env       # poi imposta almeno DJANGO_SECRET_KEY
docker compose up -d       # con Podman: podman compose up -d
```

Il servizio si riavvia da solo (`restart: unless-stopped`), persiste il DB nel
volume `p7m-apri-data` ed espone la porta `${PORT}` (default 8000). Per
aggiornare all'ultima immagine: `docker compose pull && docker compose up -d`.

## Variabili d'ambiente

`DJANGO_SECRET_KEY`, `DJANGO_DEBUG` (`1`/`0`), `DJANGO_ALLOWED_HOSTS`,
`CSRF_TRUSTED_ORIGINS`, `DJANGO_DB_PATH`.

## Note sull'output

- Il file estratto mantiene l'estensione interna: `documento.pdf.p7m` → `documento.pdf`.
- Se il nome era `documento.p7m` senza estensione interna, l'output sarà
  `documento` (aggiungere manualmente l'estensione).
