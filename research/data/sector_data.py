"""Sector data fetcher — ETF prices for momentum + screener cache aggregation.

Sector ETF map uses SPDR sector ETFs (US-traded, liquid, 1y+ history).
"""

from __future__ import annotations

import logging
import math
from datetime import date, timedelta

import pandas as pd

_log = logging.getLogger(__name__)

# Sector → representative ETF ticker
SECTOR_ETF_MAP: dict[str, str] = {
    "Technology":             "XLK",
    "Healthcare":             "XLV",
    "Financial Services":     "XLF",
    "Financials":             "XLF",
    "Energy":                 "XLE",
    "Consumer Cyclical":      "XLY",
    "Consumer Discretionary": "XLY",
    "Consumer Defensive":     "XLP",
    "Consumer Staples":       "XLP",
    "Industrials":            "XLI",
    "Basic Materials":        "XLB",
    "Materials":              "XLB",
    "Real Estate":            "XLRE",
    "Utilities":              "XLU",
    "Communication Services": "XLC",
}

_MARKET_ETF = "SPY"
_WORLD_ETF  = "ACWI"   # iShares MSCI ACWI


def fetch_sector_prices(period: str = "1y") -> dict[str, pd.Series]:
    """Return {ticker: adj-close series} for all unique sector ETFs + SPY + ACWI."""
    import yfinance as yf

    all_etfs = list(set(SECTOR_ETF_MAP.values())) + [_MARKET_ETF, _WORLD_ETF]
    try:
        raw = yf.download(all_etfs, period=period, auto_adjust=True,
                          progress=False, group_by="ticker")
        result: dict[str, pd.Series] = {}
        for etf in all_etfs:
            try:
                if len(all_etfs) == 1:
                    col = raw["Close"]
                else:
                    col = raw[etf]["Close"] if etf in raw.columns.get_level_values(0) else None
                if col is not None:
                    col = col.dropna()
                    if not col.empty:
                        result[etf] = col
            except Exception:
                pass
        return result
    except Exception as exc:
        _log.warning("Sector ETF price fetch failed: %s", exc)
        return {}


def momentum(series: pd.Series, months: int) -> float:
    """Return (current / past_N_months_ago) - 1, or NaN."""
    if series.empty or len(series) < 5:
        return float("nan")
    days = int(months * 21)   # ≈ trading days per month
    idx = max(0, len(series) - days)
    past = float(series.iloc[idx])
    curr = float(series.iloc[-1])
    if past <= 0:
        return float("nan")
    return (curr / past) - 1.0


def relative_strength(sector_series: pd.Series, market_series: pd.Series,
                      months: int = 12) -> float:
    """Return sector momentum / market momentum (>1 = outperforming)."""
    s_mom = momentum(sector_series, months)
    m_mom = momentum(market_series, months)
    if math.isnan(s_mom) or math.isnan(m_mom) or m_mom == 0:
        return float("nan")
    # Relative return: sector excess over market
    return s_mom - m_mom


def aggregate_sector_fundamentals(
    universe_rows: list[dict], sector: str
) -> dict[str, float]:
    """Aggregate screener cache rows for *sector* into median KPIs."""
    rows = [r for r in universe_rows if r.get("sector") == sector]
    if not rows:
        return {}

    def _median(key: str) -> float:
        vals = [float(r[key]) for r in rows
                if r.get(key) is not None and not math.isnan(float(r[key]))]
        if not vals:
            return float("nan")
        vals.sort()
        mid = len(vals) // 2
        return vals[mid] if len(vals) % 2 else (vals[mid - 1] + vals[mid]) / 2

    return {
        "n_peers":            len(rows),
        "avg_overall_score":  _median("overall_score"),
        "avg_fund_score":     _median("fundamental_score"),
        "avg_val_score":      _median("valuation_score"),
        "avg_trend_score":    _median("trend_score"),
        "avg_pe":             _median("trailing_pe"),
        "avg_fwd_pe":         _median("forward_pe"),
        "avg_rev_growth":     _median("revenue_growth"),
        "avg_roe":            _median("return_on_equity"),
        "avg_div_yield":      _median("dividend_yield"),
    }
