"""Commodity data fetcher — yfinance futures tickers (e.g. GC=F, CL=F)."""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass

import pandas as pd
import yfinance as yf

_log = logging.getLogger(__name__)

# ── Universe ───────────────────────────────────────────────────────────────────

COMMODITY_UNIVERSE: dict[str, dict] = {
    "GC=F": {"name": "Gold",         "group": "Precious Metals", "unit": "USD/oz"},
    "SI=F": {"name": "Silver",        "group": "Precious Metals", "unit": "USD/oz"},
    "PL=F": {"name": "Platinum",      "group": "Precious Metals", "unit": "USD/oz"},
    "PA=F": {"name": "Palladium",     "group": "Precious Metals", "unit": "USD/oz"},
    "CL=F": {"name": "WTI Crude Oil", "group": "Energy",          "unit": "USD/bbl"},
    "BZ=F": {"name": "Brent Crude",   "group": "Energy",          "unit": "USD/bbl"},
    "NG=F": {"name": "Natural Gas",   "group": "Energy",          "unit": "USD/MMBtu"},
    "RB=F": {"name": "Gasoline",      "group": "Energy",          "unit": "USD/gal"},
    "HG=F": {"name": "Copper",        "group": "Base Metals",     "unit": "USD/lb"},
    "ZC=F": {"name": "Corn",          "group": "Agriculture",     "unit": "USD/bu"},
    "ZS=F": {"name": "Soybeans",      "group": "Agriculture",     "unit": "USD/bu"},
    "ZW=F": {"name": "Wheat",         "group": "Agriculture",     "unit": "USD/bu"},
    "KC=F": {"name": "Coffee",        "group": "Agriculture",     "unit": "USD/lb"},
    "CT=F": {"name": "Cotton",        "group": "Agriculture",     "unit": "USD/lb"},
    "SB=F": {"name": "Sugar",         "group": "Agriculture",     "unit": "USD/lb"},
}


# ── Data model ─────────────────────────────────────────────────────────────────

@dataclass
class CommodityProfile:
    ticker: str
    name: str = ""
    group: str = ""
    unit: str = ""
    current_price: float = float("nan")
    currency: str = "USD"
    exchange: str = ""


# ── Helpers ───────────────────────────────────────────────────────────────────

def _safe(v) -> float:
    try:
        f = float(v)
        return f if math.isfinite(f) else float("nan")
    except (TypeError, ValueError):
        return float("nan")


# ── Public API ─────────────────────────────────────────────────────────────────

def is_commodity(ticker: str) -> bool:
    """Return True for commodity futures tickers (end with =F)."""
    return str(ticker).upper().endswith("=F")


def fetch_commodity_profile(ticker: str) -> CommodityProfile:
    """Return a CommodityProfile populated from the universe dict + yfinance."""
    t = ticker.upper()
    meta = COMMODITY_UNIVERSE.get(t, {})
    profile = CommodityProfile(
        ticker=t,
        name=meta.get("name", t),
        group=meta.get("group", "Commodity"),
        unit=meta.get("unit", "USD"),
    )
    try:
        info = yf.Ticker(ticker).info or {}
        profile.current_price = _safe(info.get("regularMarketPrice") or info.get("previousClose"))
        profile.currency      = info.get("currency", "USD")
        profile.exchange      = info.get("exchange", "")
        if not profile.name or profile.name == t:
            profile.name = info.get("longName") or info.get("shortName") or t
    except Exception as exc:
        _log.debug("fetch_commodity_profile %s: %s", ticker, exc)
    return profile


def fetch_commodity_history(ticker: str, period: str = "5y") -> pd.DataFrame:
    """Return OHLCV history for a commodity futures ticker."""
    try:
        hist = yf.Ticker(ticker).history(period=period, auto_adjust=True)
        if hist.empty:
            return pd.DataFrame()
        hist.index = hist.index.tz_localize(None) if hist.index.tz else hist.index
        return hist[["Open", "High", "Low", "Close", "Volume"]].dropna(subset=["Close"])
    except Exception as exc:
        _log.warning("fetch_commodity_history %s: %s", ticker, exc)
        return pd.DataFrame()
