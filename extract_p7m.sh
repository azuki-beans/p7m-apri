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
