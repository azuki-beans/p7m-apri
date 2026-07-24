# Deploy gratuito su Google Cloud Run

[← Torna al README](../README.md)

Cloud Run esegue il container senza volumi e scala a zero quando nessuno lo usa
(rientra nel free tier). Il filesystem è effimero: il DB SQLite e la cache delle
Trusted List vivono solo finché l'istanza è attiva, quindi dopo un avvio a
freddo la **prima** verifica eIDAS torna lenta (riscarica la LOTL). Per
l'estrazione dei PDF non cambia nulla.

Serve l'[SDK gcloud](https://cloud.google.com/sdk/docs/install) e un progetto GCP.

```bash
# 1. Imposta il progetto e abilita le API necessarie
gcloud config set project IL-TUO-PROGETTO
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com

# 2. Primo deploy: builda dal Dockerfile e pubblica il servizio
gcloud run deploy p7m-apri \
  --source . \
  --region europe-west1 \
  --allow-unauthenticated \
  --memory 512Mi \
  --set-env-vars DJANGO_SECRET_KEY=$(python -c "import secrets;print(secrets.token_urlsafe(50))")
```

Al termine `gcloud` stampa l'URL del servizio (es.
`https://p7m-apri-xxxx.europe-west1.run.app`). Le richieste `POST` del form
hanno bisogno che quell'origine sia fidata, quindi aggiornala subito:

```bash
# 3. Comunica a Django il proprio dominio (usa l'URL ottenuto sopra)
gcloud run services update p7m-apri --region europe-west1 \
  --update-env-vars DJANGO_ALLOWED_HOSTS=p7m-apri-xxxx.europe-west1.run.app,CSRF_TRUSTED_ORIGINS=https://p7m-apri-xxxx.europe-west1.run.app
```

Per attivare gli analytics Umami aggiungi nello stesso modo
`UMAMI_SRC` e `UMAMI_WEBSITE_ID`. Per aggiornare l'app in futuro basta
rilanciare il comando `gcloud run deploy --source .`.

## Chiave segreta con Secret Manager (consigliato in produzione)

Passare `DJANGO_SECRET_KEY` tra le env la lascia in chiaro nella configurazione
del servizio. Meglio custodirla in **Secret Manager** e farla leggere a Cloud
Run a runtime.

```bash
# 1. Abilita l'API e crea il secret con un valore casuale
gcloud services enable secretmanager.googleapis.com
python -c "import secrets;print(secrets.token_urlsafe(50))" \
  | gcloud secrets create django-secret-key --data-file=-

# 2. Concedi al service account di Cloud Run il permesso di leggerlo
PROJECT_NUMBER=$(gcloud projects describe $(gcloud config get-value project) --format='value(projectNumber)')
gcloud secrets add-iam-policy-binding django-secret-key \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

# 3. Collega il secret alla variabile d'ambiente (al posto di --set-env-vars DJANGO_SECRET_KEY=...)
gcloud run services update p7m-apri --region europe-west1 \
  --update-secrets DJANGO_SECRET_KEY=django-secret-key:latest
```

`:latest` segue automaticamente l'ultima versione: per ruotare la chiave basta
aggiungere una nuova versione al secret (`gcloud secrets versions add
django-secret-key --data-file=-`) e riavviare il servizio. Lo stesso meccanismo
vale per qualsiasi altra variabile sensibile.
