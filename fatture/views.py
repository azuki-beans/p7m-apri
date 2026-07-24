from datetime import timedelta

from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from converter.extractor import extract
from converter.models import Conversion

from .models import Fattura
from .pdf import render_pdf

# Le fatture generate più vecchie di questo intervallo vengono cancellate.
RETENTION = timedelta(hours=1)


def _cleanup():
    Fattura.objects.filter(
        created_at__lt=timezone.now() - RETENTION
    ).delete()


def _pdf_name(original_name: str) -> str:
    """documento.xml -> documento.pdf (mantiene il nome, cambia estensione)."""
    base = original_name.rsplit(".", 1)[0] if "." in original_name else original_name
    # Toglie anche un eventuale secondo suffisso .p7m (documento.xml.p7m).
    base = base.rsplit(".", 1)[0] if base.lower().endswith(".xml") else base
    return f"{base or 'fattura'}.pdf"


def _to_invoice_xml(raw: bytes, name: str = "") -> tuple[bytes, dict | None]:
    """Restituisce `(xml, firma)`.

    Se l'input è un .p7m (per estensione o per firma DER, primo byte 0x30) lo
    estrae con OpenSSL e `firma` è un dict con l'esito della verifica
    (`verified`) e il firmatario (`signer`); altrimenti `firma` è None e l'XML
    è passato così com'è. Solleva `ValueError` se il .p7m non è estraibile.
    """
    looks_p7m = name.lower().endswith(".p7m") or raw[:1] == b"\x30"
    if looks_p7m:
        result = extract(raw, name or "documento.p7m")
        if result is None:
            raise ValueError(
                "File .p7m non valido o non firmato in formato CMS/PKCS#7."
            )
        firma = {"verified": result.verified, "signer": result.signer}
        return bytes(result.content), firma
    return raw, None


@require_GET
def index(request):
    return render(request, "fatture/index.html", {
        "umami_src": settings.UMAMI_SRC,
        "umami_website_id": settings.UMAMI_WEBSITE_ID,
        "api_url": request.build_absolute_uri(reverse("api_fattura_pdf")),
    })


@require_POST
def render_view(request):
    _cleanup()
    upload = request.FILES.get("file")
    if not upload:
        return render(request, "fatture/result.html",
                      {"error": "Nessun file selezionato."})
    name = upload.name.lower()
    if not (name.endswith(".xml") or name.endswith(".p7m")):
        return render(request, "fatture/result.html",
                      {"error": "Il file deve avere estensione .xml o .p7m."})

    raw = upload.read()
    try:
        xml, firma = _to_invoice_xml(raw, upload.name)
        pdf = render_pdf(xml)
    except ValueError as exc:
        return render(request, "fatture/result.html", {"error": str(exc)})
    except Exception:
        return render(request, "fatture/result.html", {
            "error": "Impossibile generare il PDF della fattura.",
        })

    fattura = Fattura.objects.create(
        original_name=upload.name,
        output_name=_pdf_name(upload.name),
        content=pdf,
    )
    return render(request, "fatture/result.html", {
        "fattura": fattura,
        "firma": firma,
        "view_url": reverse("fattura_pdf", args=[fattura.id]),
        "download_url": reverse("fattura_pdf", args=[fattura.id]) + "?dl=1",
    })


@require_GET
def pdf_view(request, pk):
    """Serve il PDF: inline per l'anteprima in <iframe>, allegato con ?dl=1."""
    fattura = get_object_or_404(Fattura, pk=pk)
    response = HttpResponse(bytes(fattura.content), content_type="application/pdf")
    disposition = "attachment" if request.GET.get("dl") else "inline"
    response["Content-Disposition"] = (
        f'{disposition}; filename="{fattura.output_name}"'
    )
    return response


@require_GET
def from_conversion(request, pk):
    """Visualizza come fattura un file .p7m già estratto in home (Conversion)."""
    _cleanup()
    conversion = get_object_or_404(Conversion, pk=pk)
    # La Conversion nasce sempre da un .p7m: mostriamo l'esito della firma.
    context = {"firma": {
        "verified": conversion.verified,
        "signer": conversion.signer,
    }}
    try:
        pdf = render_pdf(bytes(conversion.content))
    except ValueError as exc:
        context["error"] = str(exc)
    except Exception:
        context["error"] = "Impossibile generare il PDF della fattura."
    else:
        fattura = Fattura.objects.create(
            original_name=conversion.output_name,
            output_name=_pdf_name(conversion.output_name),
            content=pdf,
        )
        context.update(
            fattura=fattura,
            view_url=reverse("fattura_pdf", args=[fattura.id]),
            download_url=reverse("fattura_pdf", args=[fattura.id]) + "?dl=1",
        )
    return render(request, "fatture/view.html", context)


@csrf_exempt
@require_POST
def api_pdf(request):
    """API: fattura XML (o .p7m) -> PDF.

    Input: file nel campo multipart `file`, oppure i byte grezzi nel corpo
    (con `?filename=` opzionale). Parametri query: `accent` (HEX, sovrascrive il
    tema), `dl=1` per forzare il download. Risposta: `application/pdf`, oppure
    JSON `{"error": ...}` con stato 4xx/5xx.
    """
    upload = request.FILES.get("file")
    if upload is not None:
        raw, name = upload.read(), upload.name
    else:
        raw, name = request.body, request.GET.get("filename", "")

    if not raw:
        return JsonResponse(
            {"error": "Nessun contenuto: invia il campo 'file' o i byte nel corpo."},
            status=400,
        )
    try:
        xml, _firma = _to_invoice_xml(raw, name)
        pdf = render_pdf(xml, accent=request.GET.get("accent"))
    except ValueError as exc:
        return JsonResponse({"error": str(exc)}, status=422)
    except Exception:
        return JsonResponse(
            {"error": "Impossibile generare il PDF della fattura."}, status=500
        )

    response = HttpResponse(pdf, content_type="application/pdf")
    disposition = "attachment" if request.GET.get("dl") else "inline"
    response["Content-Disposition"] = (
        f'{disposition}; filename="{_pdf_name(name or "fattura.xml")}"'
    )
    return response
