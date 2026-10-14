from datetime import timedelta

from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from fatture.parser import is_fattura

from .extractor import extract
from .models import Conversion
from .validation import validate_signature

# Le conversioni più vecchie di questo intervallo vengono cancellate.
RETENTION = timedelta(hours=1)


def _cleanup():
    Conversion.objects.filter(
        created_at__lt=timezone.now() - RETENTION
    ).delete()


@require_GET
def index(request):
    return render(request, "converter/index.html", {
        "umami_src": settings.UMAMI_SRC,
        "umami_website_id": settings.UMAMI_WEBSITE_ID,
        "canonical": request.build_absolute_uri(reverse("index")),
    })


# Pagine pubbliche da indicizzare (sitemap.xml).
SITEMAP_PAGES = ["index", "fatture"]


@require_GET
def robots_txt(request):
    sitemap = request.build_absolute_uri(reverse("sitemap"))
    body = (
        "User-agent: *\n"
        # Endpoint di elaborazione e download: niente da indicizzare.
        "Disallow: /verify/\n"
        "Disallow: /download/\n"
        "Disallow: /fatture/render/\n"
        "Disallow: /fatture/pdf/\n"
        "Disallow: /fatture/da-conversione/\n"
        "Disallow: /fatture/api/\n"
        f"Sitemap: {sitemap}\n"
    )
    return HttpResponse(body, content_type="text/plain")


@require_GET
def sitemap_xml(request):
    urls = "".join(
        f"<url><loc>{request.build_absolute_uri(reverse(name))}</loc></url>"
        for name in SITEMAP_PAGES
    )
    body = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        f"{urls}</urlset>"
    )
    return HttpResponse(body, content_type="application/xml")


@require_POST
def verify(request):
    _cleanup()
    upload = request.FILES.get("file")
    if not upload:
        return render(request, "converter/result.html",
                      {"error": "Nessun file selezionato."})
    if not upload.name.lower().endswith(".p7m"):
        return render(request, "converter/result.html",
                      {"error": "Il file deve avere estensione .p7m."})

    raw = upload.read()
    result = extract(raw, upload.name)
    if result is None:
        return render(request, "converter/result.html", {
            "error": "Impossibile estrarre il file: non è un .p7m valido "
                     "o non è firmato in formato CMS/PKCS#7.",
        })

    conversion = Conversion.objects.create(
        original_name=upload.name,
        output_name=result.output_name,
        content=result.content,
        content_type=result.content_type,
        verified=result.verified,
        signer=result.signer,
        signatures=[
            {"level": layer.level, "signers": layer.signers,
             "verified": layer.verified}
            for layer in result.layers
        ],
    )
    context = {
        "conversion": conversion,
        "download_url": reverse("download", args=[conversion.id]),
    }
    # Se il contenuto estratto è una fattura elettronica, offri di visualizzarla.
    if is_fattura(bytes(result.content)):
        context["fattura_url"] = reverse(
            "fattura_da_conversione", args=[conversion.id]
        )
    # Validazione legale (eIDAS) solo se richiesta: è lenta e richiede rete.
    # Nei .p7m annidati ogni livello viene validato separatamente.
    if request.POST.get("validate") == "on":
        context["validations"] = [
            outcome
            for level, cms_bytes in enumerate(result.cms_layers, start=1)
            for outcome in validate_signature(cms_bytes, level=level)
        ]
    return render(request, "converter/result.html", context)


@require_GET
def download(request, pk):
    conversion = get_object_or_404(Conversion, pk=pk)
    response = HttpResponse(
        bytes(conversion.content), content_type=conversion.content_type
    )
    response["Content-Disposition"] = (
        f'attachment; filename="{conversion.output_name}"'
    )
    return response
