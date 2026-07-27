# Politica di sicurezza

## Versioni supportate

Le correzioni di sicurezza vengono applicate all'ultima versione rilasciata.
Chi usa una versione precedente è invitato ad aggiornare prima di segnalare un
problema.

| Versione | Supportata |
| -------- | ---------- |
| 0.1.x    | sì         |

## Segnalare una vulnerabilità

**Non aprire una issue pubblica.** Una vulnerabilità resta riservata finché non
esiste una correzione disponibile, per non esporre chi ha già installato
l'applicazione.

Puoi segnalarla in due modi:

1. **GitHub Security Advisory** (consigliato): dalla scheda *Security* del
   repository, «Report a vulnerability». La discussione resta privata fino
   alla pubblicazione.
2. **Email** a `marco.pavanelli@gmail.com`, con oggetto che inizia per
   `[SECURITY] p7m-apri`.

Nella segnalazione includi, per quanto ti è possibile:

- il tipo di problema e il componente interessato;
- i passi per riprodurlo, con un file di prova **non contenente dati reali**;
- la versione dell'applicazione e come è distribuita;
- l'impatto che ritieni possibile.

## Cosa aspettarti

- **Presa in carico entro due giorni lavorativi.**
- Una valutazione della gravità e, se confermata, un piano di correzione
  condiviso con chi ha segnalato.
- Il rilascio di una versione correttiva, seguito dalla **pubblicazione di un
  advisory** che descrive il problema, le versioni interessate e la
  correzione: una volta disponibile la patch, l'informazione è utile a tutti
  gli altri utilizzatori.
- Il riconoscimento pubblico di chi ha segnalato, salvo diversa richiesta.

Ti chiediamo di non divulgare i dettagli finché la correzione non è
disponibile.

## Perimetro

Sono considerate rilevanti, fra le altre:

- possibilità di far scrivere su disco i documenti caricati, o di accedere ai
  documenti caricati da altri utenti;
- aggiramento dei limiti sulle dimensioni o sul tipo dei file accettati;
- esecuzione di codice o comandi tramite un file caricato appositamente
  costruito (`.p7m`, XML), incluse le entità esterne XML e le richieste di rete
  innescate dalla generazione del PDF;
- iniezione nei parametri dell'API (per esempio il colore del tema);
- risultati di validazione della firma errati, in particolare una firma non
  valida riportata come valida.

**Non rientrano nel perimetro** i comportamenti documentati come tali:

- l'opzione `-noverify` di OpenSSL nell'estrazione, che salta di proposito la
  validazione della catena dei certificati — la verifica legale è una funzione
  separata e opzionale;
- l'assenza di autenticazione: l'applicazione è pensata per un uso pubblico e
  senza account;
- l'istanza dimostrativa online, che non offre garanzie di riservatezza e sulla
  quale non vanno caricati documenti riservati.

## Sicurezza delle dipendenze

Le dipendenze sono dichiarate in `pyproject.toml` e bloccate in `poetry.lock`.
I manutentori monitorano i rilasci delle dipendenze e recepiscono gli
aggiornamenti di sicurezza, dando priorità a quelli che riguardano il
trattamento dei file caricati (OpenSSL, pyHanko, WeasyPrint, Django).
