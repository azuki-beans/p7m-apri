# p7m-apri

Estrai il documento originale (di solito un PDF) da un file `.p7m`, cioè un file
firmato digitalmente — quelli che in Italia hanno valore legale. Carichi il
`.p7m`, l'app tira fuori il documento e verifica la firma. Tutto nel browser, in
pochi secondi.

> Nessun file viene conservato: i documenti estratti sono cancellati automaticamente dopo un'ora.

Spuntando l'opzione **«Verifica anche la validità legale della firma (eIDAS)»**
l'app non si limita a controllare l'integrità, ma verifica che il certificato
del firmatario sia riconosciuto dalle EU Trusted List (i prestatori qualificati,
inclusi quelli italiani accreditati AgID). Questa verifica è più lenta e
richiede connessione a Internet.

![Schermata iniziale di p7m-apri](docs/screenshot.png)

## Avvio rapido (in locale)

Serve solo [Docker](https://docs.docker.com/get-docker/) **oppure**
[Podman](https://podman.io/). Non devi installare né scaricare altro: l'immagine
è già pronta su GitHub.

```bash
# Docker
docker run --rm -p 8000:8000 -v p7m-apri-data:/data ghcr.io/azuki-beans/p7m-apri:latest

# Podman
podman run --rm -p 8000:8000 -v p7m-apri-data:/data ghcr.io/azuki-beans/p7m-apri:latest
```

Poi apri il browser su **<http://localhost:8000>** e carica il tuo `.p7m`.

## Metterlo su un server (Docker Compose)

```bash
git clone https://github.com/azuki-beans/p7m-apri.git
cd p7m-apri

cp .env.example .env       # imposta almeno DJANGO_SECRET_KEY
docker compose up -d       # con Podman: podman compose up -d
```

Il servizio si riavvia da solo (`restart: unless-stopped`) e conserva il proprio
database nel volume `p7m-apri-data`. Per aggiornarlo all'ultima versione:
`docker compose pull && docker compose up -d`.

### Variabili d'ambiente

| Variabile | A cosa serve |
|---|---|
| `DJANGO_SECRET_KEY` | Chiave segreta (obbligatoria in produzione). |
| `DJANGO_ALLOWED_HOSTS` | Domini consentiti, es. `p7m.azienda.it`. |
| `CSRF_TRUSTED_ORIGINS` | Origini fidate con schema, es. `https://p7m.azienda.it`. |
| `DJANGO_DEBUG` | `1`/`0` (default `0`). |
| `DJANGO_DB_PATH` | Percorso del database SQLite. |
| `TRUST_LIST_CACHE_DIR` | Cache delle EU Trusted List per la validazione eIDAS. |
| `TRUST_LIST_TERRITORIES` | Paesi delle Trusted List, es. `IT` (default) o `IT,FR`; vuoto = tutta la UE. |
| `SIGNATURE_REVOCATION_MODE` | Controllo revoca: `soft-fail` (default), `hard-fail`, `require`. |

## Compilare l'immagine da sorgente

Se vuoi buildare tu invece di usare quella pubblica:

```bash
git clone https://github.com/azuki-beans/p7m-apri.git
cd p7m-apri
docker build -t p7m-apri .
docker run --rm -p 8000:8000 -v p7m-apri-data:/data p7m-apri
```

## Come funziona (sotto il cofano)

Dietro le quinte è una sola chiamata a OpenSSL:

```bash
openssl smime -verify -in documento.pdf.p7m -inform DER -noverify -out documento.pdf
```

- `-inform DER` — i `.p7m` sono codificati in DER.
- `-noverify` — salta la validazione della catena di certificati CA (così non
  servono i certificati root installati), ma l'integrità della firma viene
  comunque verificata.
- Il nome dell'output mantiene l'estensione interna: `documento.pdf.p7m` →
  `documento.pdf`. Se il `.p7m` non la conteneva (`documento.p7m`), l'output sarà
  `documento` e dovrai aggiungere l'estensione a mano.

## Licenza

Distribuito con licenza [MIT](LICENSE). © azuki-beans.
