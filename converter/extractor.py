"""Estrazione e verifica firma dei file .p7m tramite OpenSSL."""
import re
import subprocess
import tempfile
from dataclasses import dataclass


@dataclass
class ExtractResult:
    content: bytes
    verified: bool
    signer: str
    content_type: str
    output_name: str


# Firme magiche più comuni → (content_type, estensione)
_SIGNATURES = [
    (b"%PDF", "application/pdf", ".pdf"),
    (b"PK\x03\x04", "application/zip", ".zip"),
    (b"\xd0\xcf\x11\xe0", "application/msword", ".doc"),
    (b"{\\rtf", "application/rtf", ".rtf"),
    (b"<?xml", "application/xml", ".xml"),
]


def _detect(content: bytes) -> tuple[str, str]:
    for magic, ctype, ext in _SIGNATURES:
        if content.startswith(magic):
            return ctype, ext
    return "application/octet-stream", ""


def _output_name(original_name: str, ext: str) -> str:
    name = original_name
    if name.lower().endswith(".p7m"):
        name = name[:-4]
    # Se il nome interno non aveva estensione, usiamo quella rilevata.
    if "." not in name and ext:
        name += ext
    return name or "documento"


def _signer(p7m_path: str) -> str:
    """Estrae il CN del firmatario dal certificato incluso nel .p7m."""
    try:
        proc = subprocess.run(
            ["openssl", "pkcs7", "-inform", "DER", "-in", p7m_path,
             "-print_certs", "-noout"],
            capture_output=True, text=True, timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    # Gestisce sia "CN=..." che "CN = ..." (formati OpenSSL diversi).
    for line in proc.stdout.splitlines():
        if line.strip().lower().startswith("subject"):
            m = re.search(r"CN\s*=\s*([^,/\n]+)", line)
            if m:
                return m.group(1).strip()
    return ""


def extract(p7m_bytes: bytes, original_name: str) -> ExtractResult | None:
    """Estrae il file originale e verifica l'integrità della firma.

    Restituisce None se OpenSSL non riesce a estrarre il contenuto
    (file non valido o non firmato in CMS/PKCS#7).
    """
    with tempfile.NamedTemporaryFile(suffix=".p7m") as inf, \
            tempfile.NamedTemporaryFile() as outf:
        inf.write(p7m_bytes)
        inf.flush()
        try:
            proc = subprocess.run(
                ["openssl", "smime", "-verify", "-in", inf.name,
                 "-inform", "DER", "-noverify", "-out", outf.name],
                capture_output=True, text=True, timeout=60,
            )
        except (OSError, subprocess.SubprocessError):
            return None
        if proc.returncode != 0:
            return None
        outf.seek(0)
        content = outf.read()
        if not content:
            return None
        # -noverify salta la catena CA ma verifica comunque l'integrità.
        verified = "Verification successful" in proc.stderr
        signer = _signer(inf.name)

    ctype, ext = _detect(content)
    return ExtractResult(
        content=content,
        verified=verified,
        signer=signer,
        content_type=ctype,
        output_name=_output_name(original_name, ext),
    )
