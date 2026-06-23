# p7m-apri

Utility per estrarre i file originali (tipicamente PDF) da file `.p7m` firmati digitalmente (CMS/PKCS#7).

## Dipendenze

- `openssl` (disponibile su Linux/macOS; su Windows via WSL o OpenSSL for Windows)

---

## Utilizzo rapido — singolo file

```bash
openssl smime -verify -in documento.pdf.p7m -inform DER -noverify -out documento.pdf
```

> `-noverify` ignora la validazione della catena di certificati (utile se non si ha il CA root installato). Rimuoverlo se si vuole verificare la firma.

---

## Script bash — estrazione multipla

```bash
#!/usr/bin/env bash
# extract_p7m.sh
# Estrae tutti i file .p7m nella directory corrente (o in quella passata come argomento)

INPUT_DIR="${1:-.}"
OUTPUT_DIR="${2:-./estratti}"

mkdir -p "$OUTPUT_DIR"

for f in "$INPUT_DIR"/*.p7m; do
    [ -f "$f" ] || continue
    base=$(basename "$f" .p7m)
    out="$OUTPUT_DIR/${base}"
    echo -n "Estraggo: $base ... "
    if openssl smime -verify -in "$f" -inform DER -noverify -out "$out" 2>/dev/null; then
        echo "OK → $out"
    else
        echo "ERRORE"
    fi
done

echo "Done. File estratti in: $OUTPUT_DIR"
```

### Uso

```bash
chmod +x extract_p7m.sh

# Estrae tutti i .p7m nella directory corrente
./extract_p7m.sh

# Specifica input e output
./extract_p7m.sh /path/to/p7m_files /path/to/output
```

---

## Script Python — estrazione multipla

```python
#!/usr/bin/env python3
"""
extract_p7m.py
Estrae tutti i file .p7m da una directory usando openssl via subprocess.
"""

import subprocess
import sys
from pathlib import Path


def extract_p7m(input_path: Path, output_path: Path) -> bool:
    result = subprocess.run(
        [
            "openssl", "smime",
            "-verify",
            "-in", str(input_path),
            "-inform", "DER",
            "-noverify",
            "-out", str(output_path),
        ],
        capture_output=True,
    )
    return result.returncode == 0


def main():
    input_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
    output_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("estratti")
    output_dir.mkdir(parents=True, exist_ok=True)

    p7m_files = list(input_dir.glob("*.p7m"))
    if not p7m_files:
        print(f"Nessun file .p7m trovato in: {input_dir}")
        sys.exit(0)

    ok, fail = 0, 0
    for f in p7m_files:
        out = output_dir / f.stem  # rimuove .p7m, mantiene es. .pdf
        print(f"Estraggo: {f.name} ...", end=" ")
        if extract_p7m(f, out):
            print(f"OK → {out.name}")
            ok += 1
        else:
            print("ERRORE")
            fail += 1

    print(f"\nCompletato: {ok} OK, {fail} errori. Output in: {output_dir}")


if __name__ == "__main__":
    main()
```

### Uso

```bash
# Directory corrente → ./estratti/
python3 extract_p7m.py

# Specifica input e output
python3 extract_p7m.py /path/to/p7m_files /path/to/output
```

---

## Applicazione web (Docker)

Web app minimale (Django + SQLite + HTMX) con un'unica pagina pubblica: carichi
un `.p7m`, l'app estrae il documento, verifica la firma e offre il download al
volo. Nessun file viene conservato: le conversioni sono cancellate dopo un'ora.

```bash
# Build
docker build -t p7m-apri .

# Run (DB SQLite persistito nel volume p7m-apri-data)
docker run --rm -p 8000:8000 -v p7m-apri-data:/data p7m-apri
```

Poi apri <http://localhost:8000>.

Sviluppo locale (senza Docker):

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python manage.py migrate
.venv/bin/python manage.py runserver
```

Variabili d'ambiente: `DJANGO_SECRET_KEY`, `DJANGO_DEBUG` (`1`/`0`),
`DJANGO_ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, `DJANGO_DB_PATH`.

---

## Note

- Il file estratto mantiene l'estensione originale (es. `.pdf`) se era inclusa nel nome del `.p7m` (es. `documento.pdf.p7m` → `documento.pdf`).
- Se il nome è `documento.p7m` senza estensione interna, l'output sarà `documento` — aggiungere manualmente l'estensione corretta.
- Per verificare effettivamente la firma (con catena CA): rimuovere `-noverify` e assicurarsi di avere i certificati root installati nel sistema.
