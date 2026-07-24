"""Rendering della fattura in PDF.

Il tracciato XML viene analizzato (`fatture.parser`), impaginato con un template
HTML Django (`fatture/invoice.html`) e convertito in PDF da WeasyPrint.

`render_pdf()` restituisce i byte del PDF; solleva `ValueError` (dal parser) se
l'XML non è una fattura riconoscibile. L'import di WeasyPrint è differito così
che l'app parta anche senza la dipendenza installata.

Colore d'accento e logo si personalizzano via variabili d'ambiente
(`FATTURA_ACCENT`, `FATTURA_LOGO_URL`, vedi settings); un colore passato come
argomento (es. dall'API) ha la precedenza ma viene validato come HEX per non
iniettare CSS arbitrario nel `<style>` del template.
"""
from __future__ import annotations

import re

from django.conf import settings
from django.template.loader import render_to_string

from .parser import parse

# Colore d'accento di default (usato se né l'argomento né l'env sono validi).
DEFAULT_ACCENT = "#8A2230"
_HEX = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$")


def _safe_accent(accent: str | None) -> str:
    """Primo colore HEX valido tra argomento ed env, altrimenti il default."""
    for candidate in (accent, getattr(settings, "FATTURA_ACCENT", "")):
        if candidate and _HEX.match(candidate.strip()):
            return candidate.strip()
    return DEFAULT_ACCENT


def render_html(
    raw: bytes, accent: str | None = None, logo_url: str | None = None
) -> str:
    """XML della fattura -> HTML impaginato (senza passare per il PDF)."""
    documenti = parse(raw)
    if logo_url is None:
        logo_url = getattr(settings, "FATTURA_LOGO_URL", "")
    return render_to_string(
        "fatture/invoice.html",
        {
            "documenti": documenti,
            "accent": _safe_accent(accent),
            "logo_url": logo_url,
        },
    )


def render_pdf(
    raw: bytes, accent: str | None = None, logo_url: str | None = None
) -> bytes:
    """XML della fattura -> byte del PDF impaginato."""
    from weasyprint import HTML  # import differito: dipendenza opzionale

    html = render_html(raw, accent=accent, logo_url=logo_url)
    return HTML(string=html).write_pdf()
