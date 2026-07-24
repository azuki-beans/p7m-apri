# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

`p7m-apri` extracts the original file (typically a PDF) from `.p7m` files — documents signed with CMS/PKCS#7 digital signatures (common in Italy for legally-signed documents). Two things live here:

1. **Reference scripts** `extract_p7m.sh` / `extract_p7m.py` — checked-in CLI batch-extraction helpers (not referenced from the README, which is web-app/Docker focused).
2. **A Django web app** (`config/` project + `converter/` app): a single public page where a user uploads a `.p7m` and downloads the extracted file with signature confirmation. Stack is deliberately minimal — Django + SQLite + HTMX (from CDN), gunicorn in Docker. No DRF, no static pipeline, no JS build.
3. **An invoice viewer** (`fatture/` app, page `/fatture/`): upload a FatturaPA XML (electronic invoice) and get a paper-style PDF rendered inline in an `<iframe>` plus download. See "Fatture app" below.

The README and all user-facing text/comments are in Italian; keep it that way.

## Web app architecture

- `converter/validation.py` — **optional** eIDAS legal validation, separate from extraction. Where OpenSSL only confirms integrity, pyHanko establishes *trust*: it validates the signer's certificate against the EU Trusted Lists (LOTL, includes Italian AgID-accredited TSPs). API used: `async_validate_detached_cms()` on the enveloping SignedData, with a `ValidationContext` whose trust comes from `TSPTrustManager(tsp_registry=...)`, built once per process via `lotl_to_registry()` (restricted to `TRUST_LIST_TERRITORIES`, a **set of uppercase ISO codes** — default `{"IT"}` — passed as `only_territories` (pyHanko wants a `Set[str]`, not a string), so the cold-cache download is fast and skips foreign lists that trip parsing) + a `FileSystemTLCache` at `TRUST_LIST_CACHE_DIR` (default `/data/trust-lists` in Docker). `validate_signature()` is a sync wrapper (`asyncio.run`) that **never raises** — on any problem (no network, pyHanko/aiohttp missing, malformed file) it returns `ValidationOutcome(available=False, error=...)`. On success `ValidationOutcome` also carries detail fields (signer org/country/ID, cert validity dates, digest/signature algorithm, eIDAS `qualified` label from `qualification_result`, QTSP `service_name`, and the full `chain` via `validation_path.iter_certs`), rendered in an optional `<details>` panel in `result.html`. pyHanko imports are deferred inside functions so the app boots and extraction works even without the `pyhanko[etsi,async-http]` dependency installed. The first validation is slow (downloads + verifies the EUTL); keeping that cache warm is the job of the **planned Celery module** (not yet built). Revocation strictness is `SIGNATURE_REVOCATION_MODE` (default `soft-fail`). The `ValidationContext` also sets `time_tolerance=SIGNATURE_TIME_TOLERANCE` seconds (default 60, up from pyHanko's 1s) so a server clock running behind doesn't make a freshly-fetched OCSP response fail as "too recent" (`InsufficientRevinfoError` / `RevinfoUsabilityRating.TOO_NEW`) — the real cure is NTP on the host, this just absorbs small skew.
- `converter/extractor.py` — the only place that shells out to OpenSSL. `extract()` runs `smime -verify` (see Core operation), reports `verified` from the presence of `"Verification successful"` in stderr, and `_signer()` parses the firmatario CN via `openssl pkcs7 -print_certs`. File type/extension is sniffed from magic bytes in `_detect()` — it only recognizes PDF/ZIP/DOC/RTF/XML; anything else falls back to `application/octet-stream` with no extension, so `_output_name()` keeps whatever was inside the `.p7m` name. `extract()` returns `None` (not an exception) on any failure — invalid file, non-zero exit, or empty output.
- Two-step HTMX flow: `POST /verify/` extracts, stores the result row, and returns the `result.html` partial with a download link. The `validate` checkbox (off by default) additionally runs `validate_signature()` on the raw bytes and passes a `validation` `ValidationOutcome` to the template; `GET /download/<uuid>/` streams the bytes back. Extracted files are kept as a `BinaryField` BLOB in SQLite (model `Conversion`), **never written to disk**, and purged after 1h (`RETENTION`) by `_cleanup()` on each upload. The view rejects anything not ending in `.p7m` before calling `extract()`. Uploads are held entirely in memory and capped at 50 MB (`DATA_UPLOAD_MAX_MEMORY_SIZE` / `FILE_UPLOAD_MAX_MEMORY_SIZE` in `settings.py`).
- The migration `converter/migrations/0001_initial.py` is hand-maintained — if you change `models.py`, update it (or regenerate with `makemigrations`) so the Docker `migrate` step stays in sync.

## Fatture app (visualizzatore fatture elettroniche XML → PDF)

Separate from p7m extraction; shares nothing but the stack and the ephemeral-BLOB pattern.

- `fatture/parser.py` — turns FatturaPA v1.2 XML (`FPR12`/`FPA12`) into readable dataclasses. **Namespace-agnostic**: the invoice mixes the tracciato namespace, `xmlns=""` children and an embedded XAdES `ds:Signature`, so navigation is by *local tag name* (`_local`/`_find`/`_findall`), ignoring namespaces. Missing fields become empty strings/lists (no `None`, no exceptions on optional tags). One `FatturaElettronica` can hold **multiple `FatturaElettronicaBody`** (a lotto) → `parse()` returns `list[Documento]`. Codes (TipoDocumento, RegimeFiscale, Natura, ModalitaPagamento, CondizioniPagamento, EsigibilitaIVA) are decoded via module-level dicts; amounts/dates are formatted Italian-style (`1.234,56`, `20/01/2026`) by `_num`/`_qta`/`_data`. Document totals are summed from the **raw** riepilogo values in `parse()` (not the pre-formatted strings). `parse()` raises `ValueError` when the root isn't `<FatturaElettronica>` or there's no body.
- `fatture/pdf.py` — `render_pdf(raw, accent=...)` = `parse()` → `render_to_string("fatture/invoice.html")` → WeasyPrint `HTML(string=...).write_pdf()`. WeasyPrint is imported **deferred** inside `render_pdf`. `accent` (default `#8A2230`) is the one styling knob so far — the customization point for future themes. `render_html()` exposes the intermediate HTML.
- `fatture/templates/fatture/invoice.html` — the print template: `@page` A4 with page-number footer, one `<section class="fattura">` per body with `page-break-after`, header band + parties + line-items table (repeating `thead`, zebra rows) + VAT summary + totals + payment box. No custom template tags, no external fonts (uses Helvetica → DejaVu in Docker), fully self-contained CSS.
- Two-step HTMX flow mirrors converter: `POST /fatture/render/` parses+renders, stores a `Fattura` row (PDF as `BinaryField` BLOB, **never on disk**), returns `result.html` with the `<iframe>` preview; `GET /fatture/pdf/<uuid>/` serves it `inline` (preview) or `attachment` with `?dl=1` (download). Rows purged after 1h by `_cleanup()`. The view rejects non-`.xml` uploads.
- `fatture/migrations/0001_initial.py` is hand-maintained, same rule as converter.
- WeasyPrint needs system libs (Pango/Cairo/HarfBuzz + fonts) — installed in the Dockerfile apt step. Extraction still works without them; only the invoice viewer needs them.
- **Accepts `.p7m` too**: `fatture/views.py::_to_invoice_xml(raw, name)` returns the invoice XML, extracting first (via `converter.extractor.extract`) when the input is a `.p7m` (by extension or DER first byte `0x30`). Both `render_view` (web) and `api_pdf` route through it, so the viewer works on a signed XML without a manual extraction step.
- **HTTP API** `POST /fatture/api/pdf/` (`api_pdf`, `@csrf_exempt`): input is a multipart `file` field or raw request body (`?filename=` optional); output is `application/pdf` (`?dl=1` forces attachment) or JSON `{"error": …}` with 400/422/500. Query `accent` overrides the theme colour. Documented with live `curl` examples on the `/fatture/` page (view passes `api_url` via `request.build_absolute_uri`, since the `request` context processor is not enabled).
- **p7m → fattura bridge**: `converter/views.py::verify` calls `fatture.parser.is_fattura(bytes(result.content))` (lightweight root-tag check, no exceptions) and, when true, adds `fattura_url = reverse("fattura_da_conversione", <conv id>)` to the context; `converter/result.html` renders a "Visualizzala come PDF" button. `fatture/views.py::from_conversion(pk)` loads that `Conversion` BLOB, renders the PDF into a new `Fattura` row and returns the full-page `fatture/view.html` (which `{% include %}`s `result.html`). This couples `converter → fatture.parser` and `fatture → converter.models/extractor` — no import cycle (parser imports no views).
- **Branding via env** (`settings.py`): `FATTURA_ACCENT` (HEX theme colour, default `#8A2230`) and `FATTURA_LOGO_URL` (absolute logo URL shown in the invoice header). Both flow into `fatture/pdf.py`, which defaults from settings; `render_pdf(raw, accent=..., logo_url=...)` args win. `accent` is validated by `_safe_accent()` against a strict HEX regex before it reaches the template `<style>` (defends the API `?accent=` param from CSS injection); an invalid value silently falls back to the default. The logo is only settable via env/args, never via the API query, to avoid SSRF through WeasyPrint's URL fetcher. Passed to `invoice.html` as `logo_url`/`accent`.

## Core operation

Every code path wraps a single OpenSSL invocation:

```bash
openssl smime -verify -in <input>.p7m -inform DER -noverify -out <output>
```

Key details that matter when modifying any extraction logic:
- `-inform DER` — `.p7m` files are DER-encoded; without this OpenSSL assumes PEM and fails.
- `-noverify` — skips CA certificate-chain validation. The whole point is extracting the payload without needing root CAs installed. Removing it requires the system CA store to contain the signer's root, so do not remove it by default.
- Output naming convention: strip the trailing `.p7m` only. `documento.pdf.p7m` → `documento.pdf` (correct extension preserved); `documento.p7m` → `documento` (no extension — this is expected behavior, the user adds the extension manually).

## Dependencies

- `openssl` (the only runtime dependency for *extraction*)
- `python3` for the Python variant (stdlib only — `subprocess`, `pathlib`)
- `pyhanko[etsi,async-http]` — only for the optional eIDAS validation (`converter/validation.py`); extraction works without it.

## Running

```bash
# Single file
openssl smime -verify -in documento.pdf.p7m -inform DER -noverify -out documento.pdf

# Batch (bash): args are INPUT_DIR (default .) and OUTPUT_DIR (default ./estratti)
./extract_p7m.sh [input_dir] [output_dir]

# Batch (python): same args
python3 extract_p7m.py [input_dir] [output_dir]
```

### Web app

```bash
# Docker
docker build -t p7m-apri . && docker run --rm -p 8000:8000 -v p7m-apri-data:/data p7m-apri

# Local dev (dipendenze gestite con Poetry, Python 3.14, venv in ./.venv)
poetry install
poetry run python manage.py migrate && poetry run python manage.py runserver
```

Dependencies live in `pyproject.toml` + `poetry.lock` (single source of truth: the Dockerfile installs with Poetry too, `POETRY_VIRTUALENVS_CREATE=false`). There is no `requirements.txt`.

There are no lint or automated test commands. To smoke-test extraction without a real `.p7m`, generate one with a self-signed cert: `openssl req -x509 -newkey rsa:2048 -keyout k.pem -out c.pem -days 1 -nodes -subj "/CN=TEST"` then `openssl smime -sign -binary -in <file> -signer c.pem -inkey k.pem -outform DER -nodetach -out <file>.p7m`.
