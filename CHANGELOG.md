# Diario delle modifiche

Tutte le modifiche rilevanti al progetto sono annotate qui.

Il formato segue [Keep a Changelog](https://keepachangelog.com/it/1.1.0/) e il
progetto adotta il [versionamento semantico](https://semver.org/lang/it/).

## [Non rilasciato]

### Aggiunto

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
