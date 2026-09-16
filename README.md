<p align="center">
  <img src="brand/azuki-beans-logo.svg" alt="azuki-beans" width="300">
</p>

<p align="center">
  <a href="https://github.com/azuki-beans/p7m-apri/tags"><img src="https://img.shields.io/github/v/tag/azuki-beans/p7m-apri?sort=semver&label=versione&color=8A2230" alt="Ultima versione"></a>
  <a href="https://github.com/azuki-beans/p7m-apri/pkgs/container/p7m-apri"><img src="https://img.shields.io/badge/ghcr.io-p7m--apri-2496ED?logo=docker&logoColor=white" alt="Immagine Docker su ghcr.io"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/licenza-MIT-informational" alt="Licenza MIT"></a>
</p>

# p7m-apri

Estrai il documento originale (di solito un PDF) da un file `.p7m`, cioè un file
firmato digitalmente — quelli che in Italia hanno valore legale. Carichi il
`.p7m`, l'app tira fuori il documento e verifica la firma. Tutto nel browser, in
pochi secondi.

> **Demo online:** <https://p7m.azukibeans.dev>
> — provala subito, senza installare nulla. È un'istanza dimostrativa: non
> caricare documenti riservati e tieni presente che la prima verifica eIDAS può
> essere lenta (l'istanza scala a zero quando inutilizzata).

> Nessun file viene conservato: i documenti estratti sono cancellati automaticamente dopo un'ora.

Spuntando l'opzione **«Verifica anche la validità legale della firma (eIDAS)»**
l'app non si limita a controllare l'integrità, ma verifica che il certificato
del firmatario sia riconosciuto dalle EU Trusted List (i prestatori qualificati,
inclusi quelli italiani accreditati AgID). Questa verifica è più lenta e
richiede connessione a Internet.

![Schermata iniziale di p7m-apri](docs/screenshot.png)

Ecco il risultato di una verifica andata a buon fine — i dati del firmatario
sono **fittizi**, generati con un certificato di test:

![Risultato di una verifica riuscita](docs/esempio/p7m_done.png)

> Vuoi provare senza usare un tuo documento? Nel repo c'è un file di esempio già
> firmato con un'identità inventata:
> [`docs/esempio/documento-esempio.pdf.p7m`](docs/esempio/documento-esempio.pdf.p7m).
> Caricalo nell'app per riprodurre lo screenshot qui sopra.

### Firme annidate e multiple

Capita che un documento già firmato venga firmato di nuovo da un altro soggetto
(`documento.pdf.p7m.p7m`, e così via, una "cipolla" di firme): l'app spacchetta
tutti i livelli fino al documento originale e mostra, per ciascun livello, i
firmatari e l'esito dell'integrità. Il livello 1 è il più esterno, cioè la firma
apposta per ultima. Sono riconosciute anche le **firme parallele** (più
firmatari sullo stesso livello) e, con la verifica eIDAS attiva, ogni livello e
ogni firmatario vengono validati separatamente.

![Risultato con firma annidata a due livelli](docs/esempio/p7m_annidato.png)

> Per provare: [`docs/esempio/documento-esempio.pdf.p7m.p7m`](docs/esempio/documento-esempio.pdf.p7m.p7m)
> è il file di esempio qui sopra firmato una seconda volta da un'altra identità
> inventata.

## Visualizzare le fatture elettroniche (XML → PDF)

La stessa app include un **visualizzatore di fatture elettroniche**: carichi una
fattura **FatturaPA** in formato `.xml` (o `.p7m` firmato) e la vedi impaginata
come apparirebbe **su carta**, pronta da scaricare in PDF. La trovi su
**`/fatture/`** o dal link in home.

<p align="center">
  <img src="docs/fatture-home.png" alt="Pagina di caricamento della fattura" width="430">
  &nbsp;
  <img src="docs/fattura-pdf.png" alt="Fattura FatturaPA impaginata in PDF" width="330">
</p>

> **Provalo:** nel repo ci sono alcune fatture di esempio (i tracciati ufficiali
> dell'Agenzia delle Entrate) in [`test_samples/`](test_samples/) — caricane una
> `.xml` per riprodurre lo screenshot qui sopra.

### Da un `.p7m` alla sua fattura

Le fatture arrivano spesso firmate come `.p7m`. Se apri un `.p7m` dalla home e il
contenuto è una fattura, l'app se ne accorge e ti propone di **visualizzarla in
PDF** con un clic, senza estrazione manuale (in alternativa puoi caricare il
`.p7m` direttamente su `/fatture/`). Nel repo c'è un esempio già firmato con
un'identità inventata:
[`test_samples/fattura-firmata-esempio.xml.p7m`](test_samples/fattura-firmata-esempio.xml.p7m).

<p align="center">
  <img src="docs/fatture-da-p7m.png" alt="Bottone per visualizzare come PDF la fattura estratta da un .p7m" width="430">
</p>

### Personalizzare l'aspetto

Il PDF si adatta al brand aziendale tramite due variabili d'ambiente:
`FATTURA_ACCENT` (colore principale in HEX) e `FATTURA_LOGO_URL` (URL del logo
mostrato in intestazione). Vedi la tabella più sotto.

### Usarlo come API

Lo stesso servizio è disponibile via HTTP: invia una fattura `.xml` o `.p7m` in
`POST` e ricevi il PDF.

```bash
# file multipart
curl -F file=@fattura.xml http://localhost:8000/fatture/api/pdf/ -o fattura.pdf

# byte grezzi nel corpo, con colore del tema personalizzato (%23 = '#')
curl --data-binary @fattura.xml.p7m \
     "http://localhost:8000/fatture/api/pdf/?accent=%231D4ED8" -o fattura.pdf
```

Parametri query opzionali: `accent` (HEX del tema), `dl=1` per forzare il
download, `filename` per il corpo grezzo. In caso di errore la risposta è JSON
`{"error": …}`.

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
| `SIGNATURE_TIME_TOLERANCE` | Tolleranza in secondi sui tempi OCSP/CRL (default `60`); alza il valore se l'orologio del server è impreciso. |
| `FATTURA_ACCENT` | Colore principale del PDF fattura in HEX (default `#8A2230`). |
| `FATTURA_LOGO_URL` | URL assoluto del logo aziendale mostrato in intestazione fattura. |
| `PORT` | Porta su cui ascoltare (default `8000`); Cloud Run e simili la impostano da soli. |
| `UMAMI_SRC` | URL dello script Umami (es. `https://cloud.umami.is/script.js`); vuoto = nessun analytics. |
| `UMAMI_WEBSITE_ID` | ID del sito su Umami; va valorizzato insieme a `UMAMI_SRC`. |

## Deploy gratuito su Google Cloud Run

Cloud Run esegue il container senza volumi e scala a zero quando nessuno lo usa
(rientra nel free tier). Bastano l'[SDK gcloud](https://cloud.google.com/sdk/docs/install)
e un progetto GCP, poi `gcloud run deploy p7m-apri --source .`.

👉 **Guida passo-passo:** [docs/deploy-cloud-run.md](docs/deploy-cloud-run.md) —
primo deploy, dominio/CSRF e chiave segreta con Secret Manager.

## Compilare l'immagine da sorgente

Se vuoi buildare tu invece di usare quella pubblica:

```bash
git clone https://github.com/azuki-beans/p7m-apri.git
cd p7m-apri
docker build -t p7m-apri .
docker run --rm -p 8000:8000 -v p7m-apri-data:/data p7m-apri
```

## Rilasci (versioni)

La versione mostrata dal badge in cima è l'ultimo **tag Git** `vX.Y.Z`. La
pubblicazione di un tag è anche ciò che **avvia la build**: il workflow GitHub
Actions builda l'immagine multi-arch e la pubblica su `ghcr.io` taggata con la
versione (`vX.Y.Z`, `X.Y.Z`) e `latest`.

Per rilasciare una nuova versione:

```bash
# allinea la versione nel pyproject.toml, poi crea e pubblica il tag
git tag v0.1.0
git push origin v0.1.0
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
- Per un `.p7m` annidato (`documento.pdf.p7m.p7m`) il comando va ripetuto una
  volta per livello: l'output del primo passaggio è a sua volta un `.p7m`.

## Contribuire

Segnalazioni, proposte e pull request sono benvenute. Come partecipare,
convenzioni di codice e tempi di risposta sono in
[CONTRIBUTING.md](CONTRIBUTING.md); partecipando accetti il [codice di
condotta](CODE_OF_CONDUCT.md).

Per le **vulnerabilità di sicurezza non aprire una issue pubblica**: segui la
procedura riservata in [SECURITY.md](SECURITY.md).

Le modifiche di ogni versione sono annotate in [CHANGELOG.md](CHANGELOG.md).

## Software open source per la Pubblica Amministrazione

Il progetto è pubblicato secondo le [Linee guida su acquisizione e riuso di
software per le pubbliche
amministrazioni](https://docs.italia.it/italia/developers-italia/lg-acquisizione-e-riuso-software-per-pa-docs/)
di AGID. I metadati sono descritti in
[`publiccode.yml`](publiccode.yml) secondo lo [standard
publiccode.yml](https://yml.publiccode.tools/), il formato usato dal catalogo
[Developers Italia](https://developers.italia.it/).

Una pubblica amministrazione può quindi **riusare liberamente** questo
software: la licenza MIT ne consente uso, modifica e ridistribuzione senza
autorizzazioni preventive né costi di licenza. L'applicazione si installa come
singola immagine container e non richiede componenti proprietari.

## Licenza

Distribuito con licenza [MIT](LICENSE). © azuki-beans.
