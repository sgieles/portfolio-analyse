"""Asset universe definitions — S&P 500, Nasdaq 100, STOXX 600 subset, AEX."""

from __future__ import annotations

import logging
from functools import lru_cache

import pandas as pd

_log = logging.getLogger(__name__)

UNIVERSE_NAMES: list[str] = ["AEX", "Nasdaq 100", "S&P 500", "STOXX 600"]

# ── AEX (Amsterdam Exchange) — 25 components ──────────────────────────────────
AEX_TICKERS: list[str] = [
    "ASML.AS", "SHELL.AS", "HEIN.AS", "ING.AS", "PHIA.AS",
    "UNA.AS", "NN.AS", "ABN.AS", "RAND.AS", "AKZA.AS",
    "DSM.AS", "AGN.AS", "WKL.AS", "KPN.AS", "BESI.AS",
    "IMCD.AS", "ADYEN.AS", "AD.AS", "MT.AS", "LIGHT.AS",
    "PRX.AS", "OCI.AS", "TKWY.AS", "UMG.AS", "VPK.AS",
]

# ── Nasdaq 100 — static list (fetched live if Wikipedia is available) ─────────
_NASDAQ100_STATIC: list[str] = [
    "AAPL", "MSFT", "NVDA", "AMZN", "META", "TSLA", "GOOGL", "GOOG",
    "AVGO", "COST", "NFLX", "TMUS", "AMD", "PEP", "LIN", "ADBE",
    "CSCO", "TXN", "QCOM", "AMGN", "ISRG", "INTU", "CMCSA", "BKNG",
    "VRTX", "HON", "AMAT", "ADP", "SBUX", "GILD", "ADI", "PANW",
    "LRCX", "REGN", "MELI", "MU", "KLAC", "CDNS", "SNPS", "MRVL",
    "CSX", "ORLY", "PYPL", "CTAS", "ABNB", "MAR", "PCAR",
    "FTNT", "AZN", "ROP", "CPRT", "WDAY", "IDXX", "DXCM", "KDP",
    "ROST", "ODFL", "FAST", "MCHP", "EA", "EXC", "VRSK",
    "DLTR", "BIIB", "ANSS", "ZS", "PAYX", "KHC", "ON", "CTSH",
    "XEL", "GEHC", "CDW", "CCEP", "MNST", "TEAM", "DDOG",
    "CRWD", "ILMN", "NXPI", "ENPH", "ALGN",
    "MPWR", "CEG", "CHTR", "INTC", "LULU", "TTD", "PDD",
]

# ── STOXX Europe 600 — representative top-50 subset ───────────────────────────
_STOXX600_TOP50: list[str] = [
    "NESN.SW", "NOVN.SW", "ROG.SW",
    "AZN.L", "HSBA.L", "ULVR.L", "BP.L", "RIO.L", "SHEL.L", "GSK.L",
    "LSEG.L", "NXT.L", "BARC.L", "LLOY.L",
    "ASML.AS", "HEIN.AS", "ING.AS", "UNA.AS", "PHIA.AS", "ABN.AS", "AD.AS",
    "MC.PA", "OR.PA", "SAN.PA", "AIR.PA", "BNP.PA", "TTE.PA", "SU.PA",
    "KER.PA", "SGO.PA",
    "SAP.DE", "SIE.DE", "ALV.DE", "BMW.DE", "DTE.DE", "BAS.DE",
    "VOW3.DE", "MUV2.DE", "DBK.DE",
    "ENI.MI", "ENEL.MI", "ISP.MI", "UCG.MI",
    "IBE.MC", "TEF.MC", "SAN.MC",
    "ERIC-B.ST", "VOLV-B.ST", "ABB.ST",
]


@lru_cache(maxsize=1)
def _fetch_sp500_wikipedia() -> list[str]:
    tables = pd.read_html(
        "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies",
        attrs={"id": "constituents"},
    )
    tickers = tables[0]["Symbol"].tolist()
    return [str(t).replace(".", "-") for t in tickers]


@lru_cache(maxsize=1)
def _fetch_nasdaq100_wikipedia() -> list[str]:
    tables = pd.read_html("https://en.wikipedia.org/wiki/Nasdaq-100")
    for t in tables:
        if "Ticker" in t.columns:
            return [str(x) for x in t["Ticker"].tolist()]
    raise ValueError("Ticker column not found in Nasdaq-100 Wikipedia table")


def get_universe(name: str) -> list[str]:
    """Return ticker list for the named universe.

    S&P 500 and Nasdaq 100 are fetched from Wikipedia on first call and then
    cached for the process lifetime.  STOXX 600 and AEX are static.
    """
    if name == "S&P 500":
        try:
            return _fetch_sp500_wikipedia()
        except Exception as exc:
            _log.warning("S&P 500 Wikipedia fetch failed: %s", exc)
            return []
    if name == "Nasdaq 100":
        try:
            return _fetch_nasdaq100_wikipedia()
        except Exception as exc:
            _log.warning("Nasdaq 100 Wikipedia fetch failed: %s; using static list", exc)
            return list(_NASDAQ100_STATIC)
    if name == "STOXX 600":
        return list(_STOXX600_TOP50)
    if name == "AEX":
        return list(AEX_TICKERS)
    raise ValueError(f"Unknown universe: {name!r}")


def universe_size_hint(name: str) -> int:
    """Approximate number of tickers — used to warn user about load time."""
    return {"AEX": 25, "Nasdaq 100": 100, "S&P 500": 503, "STOXX 600": 50}.get(name, 100)
