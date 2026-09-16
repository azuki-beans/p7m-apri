"""Estrazione e verifica firma dei file .p7m tramite OpenSSL.

Un .p7m può essere "annidato": il documento viene firmato (→ .p7m), poi il
.p7m stesso viene firmato da un altro soggetto (→ .p7m.p7m) e così via.
``extract()`` spacchetta tutti i livelli fino ad arrivare al documento
originale, riportando per ogni livello i firmatari e l'esito di integrità.
Ogni livello può inoltre portare più firmatari ("firme parallele").
"""
import re
import subprocess
import tempfile
from dataclasses import dataclass, field

# Livelli massimi di annidamento spacchettati (protezione da file patologici).
MAX_DEPTH = 10


@dataclass
class SignatureLayer:
    """Un livello di firma. Il livello 1 è il più esterno (apposto per ultimo)."""
    level: int
    signers: list[str]
    verified: bool


@dataclass
class ExtractResult:
    content: bytes
    verified: bool        # True solo se tutti i livelli sono integri
    signer: str           # firmatari di tutti i livelli, separati da virgola
    content_type: str
    output_name: str
    layers: list[SignatureLayer] = field(default_factory=list)
    # Bytes CMS di ogni livello (dal più esterno), per la validazione eIDAS.
    cms_layers: list[bytes] = field(default_factory=list)


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
    # Un file annidato può chiamarsi documento.pdf.p7m.p7m: via tutti i .p7m.
    while name.lower().endswith(".p7m"):
        name = name[:-4]
    # Se il nome interno non aveva estensione, usiamo quella rilevata.
    if "." not in name and ext:
        name += ext
    return name or "documento"


def _signers(pem_path: str) -> list[str]:
    """CN di ogni certificato firmatario (file PEM scritto da ``-signer``
    in fase di verifica: contiene solo i certificati dei firmatari)."""
    try:
        pkcs7 = subprocess.run(
            ["openssl", "crl2pkcs7", "-nocrl", "-certfile", pem_path],
            capture_output=True, timeout=30,
        )
        proc = subprocess.run(
            ["openssl", "pkcs7", "-print_certs", "-noout"],
            input=pkcs7.stdout, capture_output=True, timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        return []
    signers = []
    # Gestisce sia "CN=..." che "CN = ..." (formati OpenSSL diversi).
    for line in proc.stdout.decode("utf-8", "replace").splitlines():
        if line.strip().lower().startswith("subject"):
            m = re.search(r"CN\s*=\s*([^,/\n]+)", line)
            if m:
                signers.append(m.group(1).strip())
    return signers


def _unwrap(p7m_bytes: bytes) -> tuple[bytes, bool, list[str]] | None:
    """Spacchetta un singolo livello CMS: (contenuto, integro, firmatari).

    Restituisce None se OpenSSL non riesce a estrarre il contenuto
    (file non valido o non firmato in CMS/PKCS#7).
    """
    with tempfile.NamedTemporaryFile(suffix=".p7m") as inf, \
            tempfile.NamedTemporaryFile() as outf, \
            tempfile.NamedTemporaryFile(suffix=".pem") as signers_f:
        inf.write(p7m_bytes)
        inf.flush()
        try:
            proc = subprocess.run(
                ["openssl", "smime", "-verify", "-in", inf.name,
                 "-inform", "DER", "-noverify", "-out", outf.name,
                 "-signer", signers_f.name],
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
        signers = _signers(signers_f.name)
    return content, verified, signers


def extract(p7m_bytes: bytes, original_name: str) -> ExtractResult | None:
    """Estrae il documento originale attraversando tutti i livelli di firma.

    Restituisce None se il primo livello non è un CMS/PKCS#7 valido.
    """
    layers: list[SignatureLayer] = []
    cms_layers: list[bytes] = []
    content = p7m_bytes
    while len(layers) < MAX_DEPTH:
        # Dopo il primo livello proviamo a spacchettare solo se il contenuto
        # sembra DER (SEQUENCE): evita di lanciare OpenSSL su un PDF.
        if layers and not content.startswith(b"\x30"):
            break
        step = _unwrap(content)
        if step is None:
            break
        cms_layers.append(content)
        content, verified, signers = step
        layers.append(SignatureLayer(len(layers) + 1, signers, verified))
    if not layers:
        return None

    all_signers = [s for layer in layers for s in layer.signers]
    ctype, ext = _detect(content)
    return ExtractResult(
        content=content,
        verified=all(layer.verified for layer in layers),
        signer=", ".join(dict.fromkeys(all_signers))[:255],
        content_type=ctype,
        output_name=_output_name(original_name, ext),
        layers=layers,
        cms_layers=cms_layers,
    )
