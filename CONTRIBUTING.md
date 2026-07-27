# Come contribuire

Grazie per l'interesse verso **p7m-apri**. Ogni contributo è benvenuto:
segnalazioni di bug, proposte di miglioramento, correzioni alla documentazione
e codice.

Questo documento descrive come partecipare e cosa aspettarsi dai manutentori,
secondo le *Linee guida su acquisizione e riuso di software per le pubbliche
amministrazioni* (AGID) — in particolare l'allegato B, «Guida alla manutenzione
di software open source».

## Codice di condotta

Partecipando al progetto accetti il [Codice di condotta](CODE_OF_CONDUCT.md).

## Segnalare un problema

Le segnalazioni si aprono nell'[issue tracker su
GitHub](https://github.com/azuki-beans/p7m-apri/issues).

Prima di aprirne una nuova, controlla se ne esiste già una analoga (anche fra
quelle chiuse). Se la trovi, aggiungi un commento invece di duplicarla.

Per un **bug** indica:

- cosa ti aspettavi e cosa è successo invece;
- i passi per riprodurlo;
- la versione usata (tag Git o tag dell'immagine Docker) e come la esegui
  (Docker, Podman, Cloud Run, locale);
- eventuali messaggi d'errore o log, incollati come testo.

> **Non allegare mai documenti reali.** Un `.p7m` o una fattura contengono dati
> personali e commerciali. Usa i file di esempio in `docs/esempio/` e
> `test_samples/`, oppure genera un file firmato di prova con un certificato
> autofirmato (istruzioni in fondo a questo documento).

Per una **proposta di miglioramento** spiega il problema concreto che vorresti
risolvere, prima ancora della soluzione tecnica: aiuta a valutare se rientra
negli obiettivi del progetto.

Per le **vulnerabilità di sicurezza non aprire una issue pubblica**: segui la
procedura riservata descritta in [SECURITY.md](SECURITY.md).

## Tempi di risposta

I manutentori si impegnano a dare un primo riscontro alle segnalazioni entro
**due giorni lavorativi**, anche solo per confermare la presa in carico quando
serve più tempo per l'analisi.

Una issue senza risposta da parte di chi l'ha aperta può essere chiusa dopo
**30 giorni** di inattività; resta sempre riapribile.

Prima di chiudere una issue risolta, viene chiesto a chi l'ha segnalata di
verificare la correzione.

## Proporre una modifica al codice

1. Se la modifica non è banale, **apri prima una issue** per concordare
   l'approccio: eviti di scrivere codice che potrebbe non essere integrato.
2. Fai un fork del repository e crea un branch con un nome breve e
   descrittivo della funzionalità (es. `validazione-timestamp`,
   `fix-nome-output`).
3. Scrivi i commit in modo comprensibile, uno per cambiamento logico.
4. Apri una pull request verso `main`, descrivendo *cosa* cambia e *perché*, e
   collegando la issue di riferimento.

Ogni pull request riceve una revisione. Se non può essere integrata, il motivo
viene spiegato per iscritto nella discussione: una proposta rifiutata resta
comunque utile come documentazione di una strada già valutata.

## Convenzioni del codice

- **Python 3.14**, stile idiomatico.
- Dipendenze gestite con **Poetry** (`pyproject.toml` + `poetry.lock`). Non
  esiste un `requirements.txt`: se aggiungi una dipendenza, aggiorna entrambi
  i file con `poetry add`.
- **Linting e formattazione con [ruff](https://docs.astral.sh/ruff/)**:
  ```bash
  poetry run ruff check .
  poetry run ruff format .
  ```
- **Testi in italiano**: interfaccia, documentazione e commenti. Il codice
  (nomi di variabili, funzioni, classi) resta in italiano o inglese secondo lo
  stile del file che stai modificando.
- **Migrazioni Django scritte a mano.** I file in `converter/migrations/` e
  `fatture/migrations/` sono mantenuti manualmente: se modifichi un modello,
  aggiorna la migrazione corrispondente (o rigenerala con `makemigrations`) in
  modo che lo step `migrate` del container resti allineato.
- **Il parser FatturaPA non è in questo repository.** Vive nella libreria
  indipendente [`fatturapa`](https://github.com/azuki-beans/fatturapa);
  `fatture/parser.py` è solo un ponte per compatibilità. Le modifiche al
  tracciato vanno proposte a monte, con i relativi test, e rientrano qui come
  aggiornamento di versione della dipendenza.
- **Non toccare `-noverify`** nella chiamata a OpenSSL senza discuterne: serve
  a estrarre il contenuto senza richiedere i certificati root di sistema. La
  validazione della catena è una funzione separata e opzionale
  (`converter/validation.py`).

## Preparare l'ambiente di sviluppo

```bash
git clone https://github.com/azuki-beans/p7m-apri.git
cd p7m-apri
poetry install
poetry run python manage.py migrate
poetry run python manage.py runserver
```

Serve `openssl` installato nel sistema. La visualizzazione delle fatture
richiede anche le librerie di sistema di WeasyPrint (Pango, Cairo, HarfBuzz e i
font); su macOS si installano con `brew install pango cairo harfbuzz`. In
alternativa si può lavorare direttamente nel container, dove sono già presenti.

### Generare un file `.p7m` di prova

Per non usare documenti reali durante lo sviluppo:

```bash
openssl req -x509 -newkey rsa:2048 -keyout k.pem -out c.pem -days 1 -nodes -subj "/CN=TEST"
openssl smime -sign -binary -in documento.pdf -signer c.pem -inkey k.pem \
  -outform DER -nodetach -out documento.pdf.p7m
```

## Licenza dei contributi

Proponendo un contributo accetti che venga distribuito con la stessa licenza
del progetto, la [licenza MIT](LICENSE).
