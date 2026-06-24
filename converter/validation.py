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
from dataclasses import dataclass
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


def _cn(cert) -> str:
    try:
        return cert.subject.native.get("common_name", "") or ""
    except Exception:
        return ""


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
            # Recupera via AIA le intermedie mancanti (es. la CA emittente
            # ArubaPEC non inclusa nel .p7m) usando la sessione aiohttp.
            fetcher_backend=AIOHttpFetcherBackend(client),
        )
        status = await async_validate_cms_signature(
            signed_data, validation_context=vc
        )

    return ValidationOutcome(
        available=True,
        intact=bool(getattr(status, "intact", False)),
        valid=bool(getattr(status, "valid", False)),
        trusted=bool(getattr(status, "trusted", False)),
        signer=_cn(status.signing_cert) if status.signing_cert else "",
    )


def validate_signature(p7m_bytes: bytes) -> ValidationOutcome:
    """Esegue la validazione eIDAS. Non solleva mai: in caso di problemi
    restituisce un esito con ``available=False`` e il messaggio in ``error``."""
    try:
        return asyncio.run(_validate(p7m_bytes))
    except Exception as exc:  # rete assente, pyHanko non installato, file rotto…
        return ValidationOutcome(
            False, False, False, False, "", error=str(exc) or exc.__class__.__name__
        )
