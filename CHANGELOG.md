# Diario delle modifiche

Tutte le modifiche rilevanti al progetto sono annotate qui.

Il formato segue [Keep a Changelog](https://keepachangelog.com/it/1.1.0/) e il
progetto adotta il [versionamento semantico](https://semver.org/lang/it/).

## [Non rilasciato]

### Aggiunto

- Variabile `SITE_URL`: se valorizzata, canonical, `sitemap.xml` e
  `robots.txt` puntano sempre al dominio pubblico, anche quando il servizio
  risponde da altri host (es. l'URL `*.run.app` di Cloud Run).
- Supporto ai `.p7m` **annidati** (documento firmato più volte in cascata,
  es. `documento.pdf.p7m.p7m`): l'estrazione attraversa tutti i livelli fino
  al documento originale e riporta firmatari ed esito di integrità di ciascun
  livello. Riconosciute anche le **firme parallele** (più firmatari sullo
  stesso livello): prima veniva mostrato solo il primo. La verifica eIDAS
  viene eseguita per ogni livello e per ogni firmatario.
- `SECURE_PROXY_SSL_HEADER` nelle impostazioni: dietro un reverse proxy che
  termina l'HTTPS (Cloud Run, nginx) gli URL assoluti, come gli esempi API
  della pagina fatture, ora sono generati in `https://`.
- SEO: `robots.txt` e `sitemap.xml` generati dinamicamente sul dominio del
  deploy; pagina fatture con canonical, Open Graph, nuove domande frequenti
  e dati strutturati `FAQPage`; nuove FAQ in home (`.p7m` da PEC, `.p7m.p7m`).

- Flusso di sicurezza: `main` protetto (si entra solo da pull request),
  controlli automatici sulle PR (gitleaks, ruff regole `S`, osv-scanner),
  hook pre-commit, Dependabot, checklist di sicurezza nel template delle PR.
  Il rilascio ripete i controlli, accetta solo tag su commit di `main` e
  blocca le immagini con vulnerabilità gravi correggibili (Trivy).
  Per superare l'analisi, `pip` è rimosso dall'immagine finale: non serve a
  runtime e le sue librerie interne (certifi, urllib3) erano vulnerabili.

### Modificato

- Home, pagina fatture, `robots.txt` e `sitemap.xml` rispondono anche alle
  richieste `HEAD` (prima `405`), usate da crawler e strumenti SEO.
- Verifica eIDAS: quando la firma non è riconosciuta viene spiegato il
  motivo (es. certificato del firmatario scaduto, senza marca temporale;
  certificato revocato; CA fuori dalle EU Trusted List) invece del solo
  «catena riconosciuta: no».
- Log: gli esiti negativi della verifica non riempiono più i log di
  Cloud Run con un traceback a ogni firma; pyHanko registra solo gli errori.

- Il canonical della home è ora calcolato dalla richiesta, non più fisso.
- Immagine Docker più leggera (da ~490 a ~290 MB): build multi-stage con le
  dipendenze in un virtualenv copiato nell'immagine finale (Poetry resta solo
  nello stage di build), librerie di sistema ridotte al minimo richiesto da
  WeasyPrint (niente Cairo), traduzioni di Django limitate a italiano e
  inglese, `.dockerignore` più rigoroso (documentazione, esempi, CI esclusi).
- Dipendenze aggiornate: Django 6.0.9, fatturapa 0.2 (il prezzo unitario non
  viene più arrotondato a due decimali), gunicorn 26.2, pyHanko 0.38,
  WeasyPrint 70, Poetry 2.5.1; GitHub Actions alle ultime versioni major.
- Testi e meta description non dicono più che l'elaborazione avviene "dal
  browser": il file viene caricato ed elaborato sul server.

- File richiesti dalle Linee guida AGID per la pubblicazione come software
  open source: `publiccode.yml`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`,
  `SECURITY.md`, `AUTHORS.md`, questo diario e i modelli per issue e pull
  request.

## [0.1.3] — 2026-07-26

### Modificato

- Il parser del tracciato FatturaPA è stato estratto in una libreria a sé,
  [`fatturapa`](https://github.com/azuki-beans/fatturapa), pubblicata su PyPI e
  ora usata come dipendenza. `fatture/parser.py` resta come ponte per
  compatibilità.

## [0.1.2] — 2026-07-24

### Aggiunto

- Verifica della firma anche sulle fatture elettroniche: il visualizzatore
  accetta file `.p7m`, estraendo l'XML prima di impaginarlo.
- Passaggio diretto da una conversione `.p7m` alla visualizzazione della
  fattura come PDF.

## [0.1.1] — 2026-07-24

Prima versione con numero di versione: raccoglie tutto lo sviluppo iniziale
del progetto, avviato a giugno 2026.

### Aggiunto

- Visualizzatore di fatture elettroniche: da XML in tracciato FatturaPA 1.2 a
  PDF impaginato, con anteprima nel browser e download.
- API HTTP `POST /fatture/api/pdf/` per la conversione da altri sistemi.
- Personalizzazione del colore del tema e del logo tramite variabili
  d'ambiente.
- Estrazione del documento originale da file `.p7m` firmati (CMS/PKCS#7) con
  verifica dell'integrità della firma.
- Validazione legale eIDAS opzionale sulle EU Trusted List, con dettagli su
  firmatario, certificato e catena di certificazione.
- Interfaccia web in italiano, senza autenticazione, con cancellazione
  automatica dei documenti dopo un'ora.
- Distribuzione come immagine container multi-architettura su `ghcr.io`, con
  build automatica alla pubblicazione di un tag.
- Script di estrazione in blocco da riga di comando (`extract_p7m.sh`,
  `extract_p7m.py`).

[Non rilasciato]: https://github.com/azuki-beans/p7m-apri/compare/v0.1.3...HEAD
[0.1.3]: https://github.com/azuki-beans/p7m-apri/compare/v0.1.2...v0.1.3
[0.1.2]: https://github.com/azuki-beans/p7m-apri/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/azuki-beans/p7m-apri/releases/tag/v0.1.1
