"""Parser della Fattura Elettronica (FatturaPA v1.2, formati FPR12/FPA12).

Trasforma l'XML in dataclass semplici e già "leggibili" (codici decodificati,
importi e date formattati all'italiana), pronte per il template PDF.

Scelte di fondo:
- **namespace-agnostico**: l'XML della fattura mescola il namespace del
  tracciato con `xmlns=""` sui figli e con la firma XAdES (`ds:Signature`);
  navighiamo per *nome locale* del tag ignorando i namespace.
- **nessuna eccezione sui campi mancanti**: i tag opzionali diventano stringhe
  vuote o liste vuote, così il template non deve difendersi da `None`.
- una `FatturaElettronica` ha un solo header ma **più `FatturaElettronicaBody`**
  (lotto di fatture): restituiamo quindi una lista di `Documento`.
"""
from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

# ---------------------------------------------------------------------------
# Tabelle di decodifica dei codici del tracciato (le più usate su una fattura
# "cartacea"). Codici non previsti vengono mostrati così come sono.
# ---------------------------------------------------------------------------
TIPO_DOCUMENTO = {
    "TD01": "Fattura",
    "TD02": "Acconto/Anticipo su fattura",
    "TD03": "Acconto/Anticipo su parcella",
    "TD04": "Nota di credito",
    "TD05": "Nota di debito",
    "TD06": "Parcella",
    "TD16": "Integrazione fattura reverse charge interno",
    "TD17": "Integrazione/autofattura acquisto servizi dall'estero",
    "TD18": "Integrazione acquisto beni intracomunitari",
    "TD19": "Integrazione/autofattura acquisto beni ex art.17 c.2",
    "TD20": "Autofattura per regolarizzazione",
    "TD21": "Autofattura per splafonamento",
    "TD22": "Estrazione beni da deposito IVA",
    "TD23": "Estrazione beni da deposito IVA con versamento IVA",
    "TD24": "Fattura differita",
    "TD25": "Fattura differita (art.21 c.4 lett.b)",
    "TD26": "Cessione di beni ammortizzabili",
    "TD27": "Fattura per autoconsumo o cessioni gratuite",
    "TD28": "Acquisti da San Marino con IVA (fattura cartacea)",
}

REGIME_FISCALE = {
    "RF01": "Ordinario",
    "RF02": "Contribuenti minimi",
    "RF04": "Agricoltura e attività connesse e pesca",
    "RF05": "Vendita sali e tabacchi",
    "RF06": "Commercio dei fiammiferi",
    "RF07": "Editoria",
    "RF08": "Gestione servizi telefonia pubblica",
    "RF09": "Rivendita documenti di trasporto pubblico e di sosta",
    "RF10": "Intrattenimenti, giochi e altre attività",
    "RF11": "Agenzie viaggi e turismo",
    "RF12": "Agriturismo",
    "RF13": "Vendite a domicilio",
    "RF14": "Rivendita beni usati, oggetti d'arte, antiquariato",
    "RF15": "Agenzie di vendite all'asta di oggetti d'arte",
    "RF16": "IVA per cassa P.A.",
    "RF17": "IVA per cassa",
    "RF18": "Altro",
    "RF19": "Forfettario",
}

NATURA = {
    "N1": "Escluse ex art.15",
    "N2": "Non soggette",
    "N2.1": "Non soggette ad IVA (artt. da 7 a 7-septies)",
    "N2.2": "Non soggette – altri casi",
    "N3": "Non imponibili",
    "N3.1": "Non imponibili – esportazioni",
    "N3.2": "Non imponibili – cessioni intracomunitarie",
    "N3.3": "Non imponibili – cessioni verso San Marino",
    "N3.4": "Non imponibili – operazioni assimilate alle esportazioni",
    "N3.5": "Non imponibili – a seguito di dichiarazioni d'intento",
    "N3.6": "Non imponibili – altre operazioni",
    "N4": "Esenti",
    "N5": "Regime del margine / IVA non esposta in fattura",
    "N6": "Inversione contabile (reverse charge)",
    "N6.1": "Reverse charge – cessione rottami",
    "N6.2": "Reverse charge – cessione oro e argento",
    "N6.3": "Reverse charge – subappalto settore edile",
    "N6.4": "Reverse charge – cessione fabbricati",
    "N6.5": "Reverse charge – cessione telefoni cellulari",
    "N6.6": "Reverse charge – cessione prodotti elettronici",
    "N6.7": "Reverse charge – prestazioni comparto edile",
    "N6.8": "Reverse charge – operazioni settore energetico",
    "N6.9": "Reverse charge – altri casi",
    "N7": "IVA assolta in altro Stato UE",
}

MODALITA_PAGAMENTO = {
    "MP01": "Contanti",
    "MP02": "Assegno",
    "MP03": "Assegno circolare",
    "MP04": "Contanti presso Tesoreria",
    "MP05": "Bonifico",
    "MP06": "Vaglia cambiario",
    "MP07": "Bollettino bancario",
    "MP08": "Carta di pagamento",
    "MP09": "RID",
    "MP10": "RID utenze",
    "MP11": "RID veloce",
    "MP12": "RIBA",
    "MP13": "MAV",
    "MP14": "Quietanza erario",
    "MP15": "Giroconto su conti di contabilità speciale",
    "MP16": "Domiciliazione bancaria",
    "MP17": "Domiciliazione postale",
    "MP18": "Bollettino di c/c postale",
    "MP19": "SEPA Direct Debit",
    "MP20": "SEPA Direct Debit CORE",
    "MP21": "SEPA Direct Debit B2B",
    "MP22": "Trattenuta su somme già riscosse",
    "MP23": "PagoPA",
}

CONDIZIONI_PAGAMENTO = {
    "TP01": "Pagamento a rate",
    "TP02": "Pagamento completo",
    "TP03": "Anticipo",
}

ESIGIBILITA_IVA = {
    "I": "IVA a esigibilità immediata",
    "D": "IVA a esigibilità differita",
    "S": "Scissione dei pagamenti (split payment)",
}


# ---------------------------------------------------------------------------
# Dataclass del modello "leggibile"
# ---------------------------------------------------------------------------
@dataclass
class Soggetto:
    denominazione: str = ""
    id_paese: str = ""
    id_codice: str = ""          # partita IVA
    codice_fiscale: str = ""
    regime_fiscale: str = ""     # decodificato
    indirizzo: str = ""
    cap: str = ""
    comune: str = ""
    provincia: str = ""
    nazione: str = ""
    telefono: str = ""
    email: str = ""

    @property
    def partita_iva(self) -> str:
        if self.id_codice:
            return f"{self.id_paese}{self.id_codice}" if self.id_paese else self.id_codice
        return ""

    @property
    def indirizzo_completo(self) -> str:
        pezzi = [self.indirizzo]
        loc = " ".join(p for p in (self.cap, self.comune) if p)
        if self.provincia:
            loc = f"{loc} ({self.provincia})" if loc else f"({self.provincia})"
        if loc:
            pezzi.append(loc)
        return " – ".join(p for p in pezzi if p)


@dataclass
class Linea:
    numero: str = ""
    descrizione: str = ""
    quantita: str = ""
    unita_misura: str = ""
    prezzo_unitario: str = ""
    sconto: str = ""
    prezzo_totale: str = ""
    aliquota_iva: str = ""
    natura: str = ""            # decodificata


@dataclass
class Riepilogo:
    aliquota_iva: str = ""
    natura: str = ""            # decodificata
    imponibile: str = ""
    imposta: str = ""
    esigibilita: str = ""       # decodificata
    riferimento_normativo: str = ""


@dataclass
class Pagamento:
    modalita: str = ""          # decodificata
    scadenza: str = ""
    importo: str = ""
    iban: str = ""
    istituto: str = ""


@dataclass
class Documento:
    """Una singola fattura (un `FatturaElettronicaBody`)."""

    tipo_documento: str = ""    # decodificato
    numero: str = ""
    data: str = ""
    divisa: str = "EUR"
    causali: list[str] = field(default_factory=list)
    importo_totale: str = ""
    bollo: str = ""
    condizioni_pagamento: str = ""  # decodificate
    cedente: Soggetto = field(default_factory=Soggetto)
    cessionario: Soggetto = field(default_factory=Soggetto)
    codice_destinatario: str = ""
    linee: list[Linea] = field(default_factory=list)
    riepiloghi: list[Riepilogo] = field(default_factory=list)
    pagamenti: list[Pagamento] = field(default_factory=list)
    totale_imponibile: str = ""  # calcolati dai riepiloghi (valori grezzi)
    totale_imposta: str = ""


# ---------------------------------------------------------------------------
# Helper di navigazione dell'albero (per nome locale, senza namespace)
# ---------------------------------------------------------------------------
def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _find(el, *path):
    """Primo discendente lungo `path` (nomi locali) oppure None."""
    cur = el
    for name in path:
        if cur is None:
            return None
        cur = next((c for c in cur if _local(c.tag) == name), None)
    return cur


def _findall(el, name):
    if el is None:
        return []
    return [c for c in el if _local(c.tag) == name]


def _text(el, *path) -> str:
    node = _find(el, *path) if path else el
    if node is None or node.text is None:
        return ""
    return node.text.strip()


# ---------------------------------------------------------------------------
# Formattazione italiana di importi e date
# ---------------------------------------------------------------------------
def _num(raw: str, decimali: int = 2) -> str:
    """Formatta un importo all'italiana: 1.234,56. Stringa vuota se non numero."""
    raw = (raw or "").strip()
    if not raw:
        return ""
    try:
        val = Decimal(raw)
    except (InvalidOperation, ValueError):
        return raw
    intero, _, dec = f"{val:.{decimali}f}".partition(".")
    negativo = intero.startswith("-")
    intero = intero.lstrip("-")
    gruppi = []
    while len(intero) > 3:
        gruppi.insert(0, intero[-3:])
        intero = intero[:-3]
    gruppi.insert(0, intero)
    testo = ".".join(gruppi)
    if dec:
        testo = f"{testo},{dec}"
    return f"-{testo}" if negativo else testo


def _qta(raw: str) -> str:
    """Quantità: toglie gli zeri decimali superflui (30.00000000 -> 30)."""
    raw = (raw or "").strip()
    if not raw:
        return ""
    try:
        val = Decimal(raw).normalize()
    except (InvalidOperation, ValueError):
        return raw
    testo = format(val, "f")
    intero, _, dec = testo.partition(".")
    return f"{intero},{dec}" if dec else intero


def _data(raw: str) -> str:
    """Data ISO (2026-01-20 o con orario) -> 20/01/2026."""
    raw = (raw or "").strip()
    if not raw:
        return ""
    for parse in (date.fromisoformat, lambda s: datetime.fromisoformat(s).date()):
        try:
            return parse(raw[:10]).strftime("%d/%m/%Y")
        except ValueError:
            continue
    return raw


def _dec(valori) -> Decimal:
    """Somma i valori numerici grezzi (ignora vuoti/non numerici)."""
    tot = Decimal("0")
    for v in valori:
        v = (v or "").strip()
        if not v:
            continue
        try:
            tot += Decimal(v)
        except (InvalidOperation, ValueError):
            continue
    return tot


def _somma(valori) -> str:
    valori = list(valori)
    if not any((v or "").strip() for v in valori):
        return ""
    return _num(str(_dec(valori)))


# ---------------------------------------------------------------------------
# Costruzione dei soggetti (cedente/cessionario)
# ---------------------------------------------------------------------------
def _soggetto(el) -> Soggetto:
    s = Soggetto()
    if el is None:
        return s
    anag = _find(el, "DatiAnagrafici")
    nome = _text(anag, "Anagrafica", "Denominazione")
    if not nome:
        n = _text(anag, "Anagrafica", "Nome")
        c = _text(anag, "Anagrafica", "Cognome")
        nome = " ".join(p for p in (n, c) if p)
    s.denominazione = nome
    s.id_paese = _text(anag, "IdFiscaleIVA", "IdPaese")
    s.id_codice = _text(anag, "IdFiscaleIVA", "IdCodice")
    s.codice_fiscale = _text(anag, "CodiceFiscale")
    s.regime_fiscale = REGIME_FISCALE.get(
        _text(anag, "RegimeFiscale"), _text(anag, "RegimeFiscale")
    )
    sede = _find(el, "Sede")
    indirizzo = _text(sede, "Indirizzo")
    civico = _text(sede, "NumeroCivico")
    s.indirizzo = f"{indirizzo}, {civico}" if civico else indirizzo
    s.cap = _text(sede, "CAP")
    s.comune = _text(sede, "Comune")
    s.provincia = _text(sede, "Provincia")
    s.nazione = _text(sede, "Nazione")
    contatti = _find(el, "Contatti")
    s.telefono = _text(contatti, "Telefono")
    s.email = _text(contatti, "Email")
    return s


def _linea(el) -> Linea:
    return Linea(
        numero=_text(el, "NumeroLinea"),
        descrizione=_text(el, "Descrizione"),
        quantita=_qta(_text(el, "Quantita")),
        unita_misura=_text(el, "UnitaMisura"),
        prezzo_unitario=_num(_text(el, "PrezzoUnitario")),
        prezzo_totale=_num(_text(el, "PrezzoTotale")),
        aliquota_iva=_num(_text(el, "AliquotaIVA")),
        natura=NATURA.get(_text(el, "Natura"), _text(el, "Natura")),
    )


def _riepilogo(el) -> Riepilogo:
    return Riepilogo(
        aliquota_iva=_num(_text(el, "AliquotaIVA")),
        natura=NATURA.get(_text(el, "Natura"), _text(el, "Natura")),
        imponibile=_num(_text(el, "ImponibileImporto")),
        imposta=_num(_text(el, "Imposta")),
        esigibilita=ESIGIBILITA_IVA.get(
            _text(el, "EsigibilitaIVA"), _text(el, "EsigibilitaIVA")
        ),
        riferimento_normativo=_text(el, "RiferimentoNormativo"),
    )


def _pagamento(el) -> Pagamento:
    return Pagamento(
        modalita=MODALITA_PAGAMENTO.get(
            _text(el, "ModalitaPagamento"), _text(el, "ModalitaPagamento")
        ),
        scadenza=_data(_text(el, "DataScadenzaPagamento")),
        importo=_num(_text(el, "ImportoPagamento")),
        iban=_text(el, "IBAN"),
        istituto=_text(el, "IstitutoFinanziario"),
    )


# ---------------------------------------------------------------------------
# API pubblica
# ---------------------------------------------------------------------------
def is_fattura(raw: bytes | str) -> bool:
    """True se i byte sono una Fattura Elettronica (radice FatturaElettronica).

    Controllo leggero e senza eccezioni: utile per capire, dopo l'estrazione di
    un .p7m, se il contenuto è una fattura da poter visualizzare.
    """
    try:
        root = ET.fromstring(raw)
    except (ET.ParseError, ValueError, TypeError):
        return False
    return _local(root.tag) == "FatturaElettronica"


def parse(raw: bytes) -> list[Documento]:
    """Analizza i byte XML e restituisce l'elenco delle fatture (bodies).

    Solleva `ValueError` se l'XML non è una Fattura Elettronica riconoscibile.
    """
    try:
        root = ET.fromstring(raw)
    except ET.ParseError as exc:
        raise ValueError(f"XML non valido: {exc}") from exc

    if _local(root.tag) != "FatturaElettronica":
        raise ValueError(
            "Il file non è una Fattura Elettronica (FatturaPA): "
            f"radice <{_local(root.tag)}>."
        )

    header = _find(root, "FatturaElettronicaHeader")
    cedente = _soggetto(_find(header, "CedentePrestatore"))
    cessionario = _soggetto(_find(header, "CessionarioCommittente"))
    codice_dest = _text(
        _find(header, "DatiTrasmissione"), "CodiceDestinatario"
    )

    documenti: list[Documento] = []
    for body in _findall(root, "FatturaElettronicaBody"):
        gen = _find(body, "DatiGenerali", "DatiGeneraliDocumento")
        beni = _find(body, "DatiBeniServizi")
        doc = Documento(
            tipo_documento=TIPO_DOCUMENTO.get(
                _text(gen, "TipoDocumento"), _text(gen, "TipoDocumento")
            ),
            numero=_text(gen, "Numero"),
            data=_data(_text(gen, "Data")),
            divisa=_text(gen, "Divisa") or "EUR",
            causali=[c.text.strip() for c in _findall(gen, "Causale") if c.text],
            importo_totale=_num(_text(gen, "ImportoTotaleDocumento")),
            bollo=_num(_text(_find(gen, "DatiBollo"), "ImportoBollo")),
            cedente=cedente,
            cessionario=cessionario,
            codice_destinatario=codice_dest,
            linee=[_linea(l) for l in _findall(beni, "DettaglioLinee")],
        )
        riepiloghi_raw = _findall(beni, "DatiRiepilogo")
        doc.riepiloghi = [_riepilogo(r) for r in riepiloghi_raw]
        imponibili = [_text(r, "ImponibileImporto") for r in riepiloghi_raw]
        imposte = [_text(r, "Imposta") for r in riepiloghi_raw]
        doc.totale_imponibile = _somma(imponibili)
        doc.totale_imposta = _somma(imposte)
        # ImportoTotaleDocumento è opzionale nel tracciato: se manca, il totale
        # documento si ricava da imponibile + imposta + bollo.
        if not _text(gen, "ImportoTotaleDocumento"):
            tot = _dec(imponibili) + _dec(imposte)
            tot += _dec([_text(_find(gen, "DatiBollo"), "ImportoBollo")])
            doc.importo_totale = _num(str(tot))
        for dp in _findall(_find(body, "DatiPagamento"), "DettaglioPagamento"):
            doc.pagamenti.append(_pagamento(dp))
        doc.condizioni_pagamento = CONDIZIONI_PAGAMENTO.get(
            _text(_find(body, "DatiPagamento"), "CondizioniPagamento"), ""
        )
        documenti.append(doc)

    if not documenti:
        raise ValueError("La fattura non contiene alcun corpo documento.")
    return documenti
