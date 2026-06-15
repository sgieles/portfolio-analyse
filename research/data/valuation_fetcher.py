"""Fetch valuation inputs: current multiples, year-end prices, market P/E.

This module is the only place in research/ that performs network I/O for
valuation data.  Callers (Streamlit pages) are responsible for caching.
"""

from __future__ import annotations

import logging
import math
from datetime import date

import yfinance as yf

from research.analytics.valuation_engine import ValuationMultiples

_log = logging.getLogger(__name__)


def fetch_current_multiples(ticker: str) -> tuple[ValuationMultiples, float, float]:
    """Return (ValuationMultiples, current_price, shares_outstanding) from yfinance info.

    All values default to nan if unavailable.
    """
    _nan = float("nan")

    def _f(info: dict, *keys) -> float:
        for k in keys:
            v = info.get(k)
            if v is not None:
                try:
                    f = float(v)
                    if math.isfinite(f):
                        return f
                except (TypeError, ValueError):
                    pass
        return _nan

    try:
        info = yf.Ticker(ticker).info or {}
    except Exception as exc:
        _log.warning("yfinance info failed for %s: %s", ticker, exc)
        return ValuationMultiples(), _nan, _nan

    price  = _f(info, "currentPrice", "regularMarketPrice", "previousClose")
    shares = _f(info, "sharesOutstanding", "impliedSharesOutstanding")

    mcap   = _f(info, "marketCap")
    ev     = _f(info, "enterpriseValue")
    rev_ttm = _f(info, "totalRevenue")

    # FCF yield — compute from trailing FCF / market cap if available
    fcf_ttm = _f(info, "freeCashflow")
    fcf_yield = (fcf_ttm / mcap) if (math.isfinite(fcf_ttm) and math.isfinite(mcap) and mcap > 0) else _nan

    multiples = ValuationMultiples(
        pe=_f(info, "trailingPE"),
        forward_pe=_f(info, "forwardPE"),
        ev_ebitda=_f(info, "enterpriseToEbitda"),
        ev_sales=_f(info, "enterpriseToRevenue"),
        ps_ratio=_f(info, "priceToSalesTrailing12Months"),
        pb_ratio=_f(info, "priceToBook"),
        fcf_yield=fcf_yield,
    )
    return multiples, price, shares


def fetch_year_end_prices(ticker: str, years: int = 10) -> dict[int, float]:
    """Return {year: December 31 closing price} for the past *years* years."""
    try:
        hist = yf.download(ticker, period=f"{years + 1}y", auto_adjust=True, progress=False)
        if hist.empty:
            return {}
        close = hist["Close"]
        if hasattr(close, "squeeze"):
            close = close.squeeze()

        result: dict[int, float] = {}
        for yr in range(date.today().year - years, date.today().year + 1):
            # Get last trading day of December in that year
            year_data = close[close.index.year == yr]
            if not year_data.empty:
                result[yr] = float(year_data.iloc[-1])
        return result
    except Exception as exc:
        _log.warning("Year-end price fetch failed for %s: %s", ticker, exc)
        return {}


def fetch_market_pe(benchmark: str = "SPY") -> float:
    """Fetch trailing P/E of the broad market proxy (*benchmark*)."""
    try:
        info = yf.Ticker(benchmark).info or {}
        pe = info.get("trailingPE")
        if pe is not None:
            return float(pe)
    except Exception as exc:
        _log.warning("Market P/E fetch failed: %s", exc)
    return float("nan")
