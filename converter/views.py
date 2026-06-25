from datetime import timedelta

from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

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
    })


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
    )
    context = {
        "conversion": conversion,
        "download_url": reverse("download", args=[conversion.id]),
    }
    # Validazione legale (eIDAS) solo se richiesta: è lenta e richiede rete.
    if request.POST.get("validate") == "on":
        context["validation"] = validate_signature(raw)
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
