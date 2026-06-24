"""Validazione legale (eIDAS) della firma di un .p7m.

A differenza di ``extractor.py`` — che con OpenSSL verifica solo l'integrità
(la firma corrisponde al contenuto) — qui usiamo pyHanko per stabilire anche la
*fiducia*: il certificato del firmatario risale a una CA presente nelle EU
Trusted List (la lista qualificata pubblicata in ambito eIDAS, che include i
prestatori di servizi fiduciari italiani accreditati AgID).

pyHanko scarica la "list of the lists" (LOTL) europea, ne verifica le firme XML
e la mette in cache su disco (``TRUST_LIST_CACHE_DIR``). Il primo controllo è
quindi lento e richiede rete; i successivi usano la cache. Tenere la cache
aggiornata in background è il compito previsto per il futuro modulo Celery.
"""
import asyncio
from dataclasses import dataclass, field
from datetime import timedelta
from pathlib import Path

from django.conf import settings

# Il registry EUTL è costoso da costruire: lo teniamo per-processo.
_registry = None


@dataclass
class ValidationOutcome:
    available: bool   # True se è stato possibile arrivare a un esito
    intact: bool      # il contenuto non è stato alterato
    valid: bool       # la firma è crittograficamente valida
    trusted: bool     # il certificato risale a una CA nelle EU Trusted List
    signer: str       # CN del firmatario
    error: str = ""   # messaggio in caso di esito non determinabile

    # Dettagli (popolati solo quando available=True)
    signer_org: str = ""
    signer_country: str = ""
    signer_id: str = ""          # serialNumber, di solito il codice fiscale
    signer_valid_from: str = ""
    signer_valid_to: str = ""
    md_algorithm: str = ""
    signature_mechanism: str = ""
    qualified: str = ""          # etichetta sulla qualificazione eIDAS
    qtsp: str = ""               # nome del servizio fiduciario (QTSP)
    validation_time: str = ""
    chain: list = field(default_factory=list)  # catena: lista di dict


def _part(cert, key) -> str:
    try:
        return cert.subject.native.get(key, "") or ""
    except Exception:
        return ""


def _fmt(dt, with_time=False) -> str:
    try:
        return dt.strftime("%d/%m/%Y %H:%M" if with_time else "%d/%m/%Y")
    except Exception:
        return ""


def _build_details(status, outcome: ValidationOutcome) -> None:
    """Popola i campi di dettaglio di ``outcome`` a partire dallo status pyHanko.
    Difensivo: un attributo mancante non compromette il verdetto principale."""
    cert = status.signing_cert
    if cert is not None:
        outcome.signer_org = _part(cert, "organization_name")
        outcome.signer_country = _part(cert, "country_name")
        outcome.signer_id = _part(cert, "serial_number")
        outcome.signer_valid_from = _fmt(cert.not_valid_before)
        outcome.signer_valid_to = _fmt(cert.not_valid_after)

    outcome.md_algorithm = getattr(status, "md_algorithm", "") or ""
    outcome.signature_mechanism = getattr(status, "pkcs7_signature_mechanism", "") or ""
    outcome.validation_time = _fmt(getattr(status, "validation_time", None), with_time=True)

    qr = getattr(status, "qualification_result", None)
    if qr is not None:
        try:
            qs = qr.status
            if getattr(qs, "qualified", False):
                qc_type = getattr(getattr(qs, "qc_type", None), "name", "")
                outcome.qualified = "Qualificata" + (f" ({qc_type})" if qc_type else "")
            else:
                outcome.qualified = "Non qualificata"
            sd = getattr(qr, "service_definition", None)
            if sd is not None:
                outcome.qtsp = getattr(sd.base_info, "service_name", "") or ""
        except Exception:
            pass

    path = getattr(status, "validation_path", None)
    if path is not None:
        try:
            for c in path.iter_certs(include_root=True):
                outcome.chain.append({
                    "subject": c.subject.native.get("common_name", "")
                    or c.subject.native.get("organization_name", ""),
                    "issuer": c.issuer.native.get("common_name", "")
                    or c.issuer.native.get("organization_name", ""),
                    "valid_from": _fmt(c.not_valid_before),
                    "valid_to": _fmt(c.not_valid_after),
                })
        except Exception:
            pass


async def _get_registry(client):
    """Costruisce (una sola volta per processo) il registry dalle EU Trusted List."""
    global _registry
    if _registry is None:
        from pyhanko.sign.validation.qualified.eutl_fetch import (
            FileSystemTLCache,
            lotl_to_registry,
        )

        cache_dir = Path(settings.TRUST_LIST_CACHE_DIR)
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache = FileSystemTLCache(cache_dir, expire_after=timedelta(days=14))
        _registry, _ = await lotl_to_registry(
            lotl_xml=None,
            client=client,
            cache=cache,
            only_territories=settings.TRUST_LIST_TERRITORIES or None,
        )
    return _registry


async def _validate(p7m_bytes: bytes) -> ValidationOutcome:
    import aiohttp
    from asn1crypto import cms
    from pyhanko.sign.validation.generic_cms import async_validate_cms_signature
    from pyhanko.sign.validation.qualified.tsp import TSPTrustManager
    from pyhanko_certvalidator import ValidationContext
    from pyhanko_certvalidator.fetchers.aiohttp_fetchers import (
        AIOHttpFetcherBackend,
    )

    content_info = cms.ContentInfo.load(p7m_bytes)
    if content_info["content_type"].native != "signed_data":
        return ValidationOutcome(
            False, False, False, False, "",
            error="Il file non contiene una struttura CMS SignedData.",
        )

    signed_data = content_info["content"]
    # Un .p7m è enveloping: il contenuto è incapsulato nella firma.
    if signed_data["encap_content_info"]["content"] is None:
        return ValidationOutcome(
            False, False, False, False, "",
            error="Firma detached: il contenuto non è incluso nel .p7m.",
        )

    async with aiohttp.ClientSession() as client:
        registry = await _get_registry(client)
        vc = ValidationContext(
            trust_manager=TSPTrustManager(tsp_registry=registry),
            allow_fetching=True,
            revocation_mode=settings.SIGNATURE_REVOCATION_MODE,
            # Recupera via AIA le intermedie mancanti usando la sessione aiohttp.
            fetcher_backend=AIOHttpFetcherBackend(client),
        )
        status = await async_validate_cms_signature(
            signed_data, validation_context=vc
        )

    outcome = ValidationOutcome(
        available=True,
        intact=bool(getattr(status, "intact", False)),
        valid=bool(getattr(status, "valid", False)),
        trusted=bool(getattr(status, "trusted", False)),
        signer=_part(status.signing_cert, "common_name") if status.signing_cert else "",
    )
    _build_details(status, outcome)
    return outcome


def validate_signature(p7m_bytes: bytes) -> ValidationOutcome:
    """Esegue la validazione eIDAS. Non solleva mai: in caso di problemi
    restituisce un esito con ``available=False`` e il messaggio in ``error``."""
    try:
        return asyncio.run(_validate(p7m_bytes))
    except Exception as exc:  # rete assente, pyHanko non installato, file rotto…
        return ValidationOutcome(
            False, False, False, False, "", error=str(exc) or exc.__class__.__name__
        )
