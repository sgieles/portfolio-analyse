"""ETF data fetcher — pulls profile, holdings and exposures from yfinance.

All I/O lives here; callers in analytics/ and ui/ receive plain dataclasses.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field

import pandas as pd
import yfinance as yf

_log = logging.getLogger(__name__)


# ── Data model ────────────────────────────────────────────────────────────────

@dataclass
class ETFProfile:
    """All descriptive and static data for one ETF."""
    ticker: str
    name: str = ""
    category: str = ""        # Morningstar category
    fund_family: str = ""
    expense_ratio: float = float("nan")   # annual TER, e.g. 0.0003 = 0.03 %
    aum: float = float("nan")             # total net assets in USD
    nav: float = float("nan")             # net asset value per share
    dividend_yield: float = float("nan")
    inception_date: str = ""
    description: str = ""
    # Morningstar ratings
    morningstar_risk: int = 0    # 1 (low) – 5 (high)
    morningstar_rating: int = 0  # 1 – 5 stars
    # Pre-computed returns from yfinance info
    beta_3y: float = float("nan")
    return_ytd: float = float("nan")
    return_3y: float = float("nan")
    return_5y: float = float("nan")
    # Holdings & allocation (populated by fetch_etf_profile)
    n_holdings: int = 0
    top_holdings: list[dict] = field(default_factory=list)   # {symbol, name, weight}
    sector_weights: dict[str, float] = field(default_factory=dict)
    country_weights: dict[str, float] = field(default_factory=dict)
    asset_allocation: dict[str, float] = field(default_factory=dict)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _safe_float(v) -> float:
    try:
        f = float(v)
        return f if math.isfinite(f) else float("nan")
    except (TypeError, ValueError):
        return float("nan")


def _parse_holdings(funds_data) -> list[dict]:
    """Extract top holdings from yfinance FundsData object."""
    try:
        df = funds_data.top_holdings
        if df is None or df.empty:
            return []
        # Normalise column names (yfinance version-dependent)
        cols = {c.lower().replace(" ", "_"): c for c in df.columns}
        symbol_col  = cols.get("symbol", cols.get("ticker", None))
        name_col    = next((cols[k] for k in cols if "name" in k or "holding" in k
                            and "percent" not in k), None)
        weight_col  = next((cols[k] for k in cols
                            if "percent" in k or "weight" in k), None)

        results = []
        for _, row in df.head(15).iterrows():
            sym = str(row[symbol_col]).strip() if symbol_col else "—"
            nm  = str(row[name_col]).strip()   if name_col  else sym
            wt  = _safe_float(row[weight_col]) if weight_col else float("nan")
            if sym and sym != "nan":
                results.append({"symbol": sym, "name": nm, "weight": wt})
        return results
    except Exception as exc:
        _log.debug("Could not parse holdings: %s", exc)
        return []


def _parse_sectors(funds_data) -> dict[str, float]:
    """Extract sector weightings from yfinance FundsData."""
    try:
        sw = funds_data.sector_weightings
        if not sw:
            return {}
        # yfinance sometimes returns a list of dicts or a plain dict
        if isinstance(sw, list):
            result: dict[str, float] = {}
            for item in sw:
                if isinstance(item, dict):
                    result.update({k: _safe_float(v) for k, v in item.items()})
            return result
        return {k: _safe_float(v) for k, v in sw.items()}
    except Exception:
        return {}


def _parse_countries(funds_data) -> dict[str, float]:
    """Extract country/geographic weights from yfinance FundsData equity_holdings."""
    try:
        eh = getattr(funds_data, "equity_holdings", None)
        if eh is None or (hasattr(eh, "empty") and eh.empty):
            return {}
        # equity_holdings sometimes has a 'Country' breakdown dict
        if isinstance(eh, dict):
            return {k: _safe_float(v) for k, v in eh.items() if "%" not in str(k)}
        return {}
    except Exception:
        return {}


def _parse_asset_allocation(funds_data) -> dict[str, float]:
    """Extract asset allocation (stocks/bonds/cash) from yfinance FundsData."""
    try:
        aa = getattr(funds_data, "asset_allocation", None)
        if not aa:
            return {}
        if isinstance(aa, dict):
            return {k: _safe_float(v) for k, v in aa.items()}
        return {}
    except Exception:
        return {}


# ── Public API ─────────────────────────────────────────────────────────────────

def fetch_etf_profile(ticker: str) -> ETFProfile:
    """Return a fully populated ETFProfile for *ticker*.

    Data comes from two yfinance sources:
    - ``Ticker.info`` for metadata and pre-computed returns
    - ``Ticker.funds_data`` for holdings, sector and geographic weights
    """
    profile = ETFProfile(ticker=ticker)
    try:
        t = yf.Ticker(ticker)
        info = t.info or {}

        profile.name          = info.get("longName") or info.get("shortName") or ticker
        profile.category      = info.get("category") or ""
        profile.fund_family   = info.get("fundFamily") or ""
        profile.expense_ratio = _safe_float(info.get("expenseRatio"))
        profile.aum           = _safe_float(info.get("totalNetAssets"))
        profile.nav           = _safe_float(info.get("navPrice") or info.get("previousClose"))
        profile.dividend_yield = _safe_float(info.get("yield") or info.get("dividendYield"))
        profile.description   = info.get("longBusinessSummary") or ""
        profile.morningstar_risk   = int(info.get("morningStarRiskRating")   or 0)
        profile.morningstar_rating = int(info.get("morningStarOverallRating") or 0)
        profile.beta_3y       = _safe_float(info.get("beta3Year"))
        profile.return_ytd    = _safe_float(info.get("ytdReturn"))
        profile.return_3y     = _safe_float(info.get("threeYearAverageReturn"))
        profile.return_5y     = _safe_float(info.get("fiveYearAverageReturn"))
        profile.n_holdings    = int(info.get("totalHoldings") or 0)

        # Holdings, sectors, geography — via funds_data
        try:
            fd = t.funds_data
            if fd is not None:
                profile.top_holdings    = _parse_holdings(fd)
                profile.sector_weights  = _parse_sectors(fd)
                profile.country_weights = _parse_countries(fd)
                profile.asset_allocation = _parse_asset_allocation(fd)
                if not profile.n_holdings and profile.top_holdings:
                    profile.n_holdings = len(profile.top_holdings)
        except Exception as exc:
            _log.debug("funds_data unavailable for %s: %s", ticker, exc)

    except Exception as exc:
        _log.warning("fetch_etf_profile failed for %s: %s", ticker, exc)

    return profile


def fetch_etf_price_history(ticker: str, period: str = "5y") -> pd.DataFrame:
    """Return adjusted close price history as a DataFrame."""
    try:
        t = yf.Ticker(ticker)
        hist = t.history(period=period, auto_adjust=True)
        return hist[["Close"]].dropna() if "Close" in hist.columns else pd.DataFrame()
    except Exception:
        return pd.DataFrame()


def is_etf(info: dict) -> bool:
    """Return True when yfinance info indicates an ETF or mutual fund."""
    qt = str(info.get("quoteType", "")).upper()
    lt = str(info.get("legalType",  "")).upper()
    return "ETF" in qt or "ETF" in lt or "MUTUALFUND" in qt or "FUND" in lt
