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
rilanciare il comando `gcloud run deploy --source .`, oppure automatizzare il
rilascio con GitHub Actions (vedi [sotto](#deploy-automatico-da-github-actions-opzionale)).

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

## Deploy automatico da GitHub Actions (opzionale)

Il workflow `.github/workflows/deploy.yml` parte **solo al push di un tag `v*`**:

1. **build**: pubblica l'immagine multi-arch su `ghcr.io` (sempre);
2. **deploy**: aggiorna il servizio Cloud Run con la nuova versione, ma solo dopo
   l'**approvazione manuale** nell'environment GitHub `production`. Se le variabili
   GCP non sono configurate (es. in un fork) il job viene saltato.

Cloud Run non legge da `ghcr.io`: l'immagine passa da un repository Artifact
Registry **remoto** che fa da proxy (`ghcr`). L'autenticazione usa la
**Workload Identity Federation**: nessuna chiave JSON, e GCP accetta solo token
emessi per l'environment `production` di questo repository.

```bash
PROJECT=IL-TUO-PROGETTO
PROJECT_NUMBER=$(gcloud projects describe $PROJECT --format='value(projectNumber)')
# ID numerici, non il nome: un repository rinominato o ricreato non eredita i permessi
read REPO_ID OWNER_ID < <(gh api repos/OWNER/p7m-apri --jq '"\(.id) \(.owner.id)"')

# 1. Proxy di ghcr.io su Artifact Registry
gcloud artifacts repositories create ghcr --project $PROJECT --location europe-west1 \
  --repository-format docker --mode remote-repository \
  --remote-docker-repo https://ghcr.io

# 2. Service account di deploy: aggiorna il servizio e lo esegue col suo service account
gcloud iam service-accounts create github-deploy --project $PROJECT
SA=github-deploy@$PROJECT.iam.gserviceaccount.com
RUNTIME_SA=$(gcloud run services describe p7m-apri --region europe-west1 --project $PROJECT \
  --format='value(spec.template.spec.serviceAccountName)')
gcloud run services add-iam-policy-binding p7m-apri --region europe-west1 --project $PROJECT \
  --member serviceAccount:$SA --role roles/run.developer
gcloud iam service-accounts add-iam-policy-binding $RUNTIME_SA --project $PROJECT \
  --member serviceAccount:$SA --role roles/iam.serviceAccountUser
gcloud artifacts repositories add-iam-policy-binding ghcr --location europe-west1 --project $PROJECT \
  --member serviceAccount:$SA --role roles/artifactregistry.reader

# 3. Workload Identity Federation, limitata a questo repository e all'environment production
gcloud iam workload-identity-pools create github --location global --project $PROJECT
gcloud iam workload-identity-pools providers create-oidc github \
  --workload-identity-pool github --location global --project $PROJECT \
  --issuer-uri https://token.actions.githubusercontent.com \
  --attribute-mapping "google.subject=assertion.sub,attribute.repository_id=assertion.repository_id,attribute.environment=assertion.environment" \
  --attribute-condition "assertion.repository_id == '$REPO_ID' && assertion.repository_owner_id == '$OWNER_ID' && assertion.environment == 'production'"
gcloud iam service-accounts add-iam-policy-binding $SA --project $PROJECT \
  --role roles/iam.workloadIdentityUser \
  --member "principalSet://iam.googleapis.com/projects/$PROJECT_NUMBER/locations/global/workloadIdentityPools/github/attribute.repository_id/$REPO_ID"
```

Nel repository GitHub:

- **Variables**: `GCP_PROJECT_ID`, `GCP_WIF_PROVIDER`
  (`projects/PROJECT_NUMBER/locations/global/workloadIdentityPools/github/providers/github`),
  `GCP_DEPLOY_SA`.
- **Environment `production`**: required reviewer, deployment limitati ai tag `v*`.
- **Tag ruleset** su `v*`: solo i maintainer possono creare tag.

Rilascio: `git tag v1.2.3 && git push origin v1.2.3`, poi approva il deploy dalla
pagina della run su GitHub.
