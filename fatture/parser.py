"""Compatibilità: il parser vive ora nella libreria autonoma `fatturapa`.

Il codice è stato estratto in `packages/fatturapa/` così da poter essere riusato
da altri progetti senza tirarsi dietro Django, WeasyPrint e pyHanko. Questo
modulo resta come punto d'importazione storico (`from fatture.parser import …`).
"""
from fatturapa.parser import *  # noqa: F401,F403
from fatturapa.parser import (  # noqa: F401  (nomi usati esplicitamente in giro)
    Documento,
    Linea,
    Pagamento,
    Riepilogo,
    Soggetto,
    is_fattura,
    parse,
)
