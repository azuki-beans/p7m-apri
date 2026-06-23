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
