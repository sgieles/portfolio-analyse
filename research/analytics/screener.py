"""Screener scoring engine — pure functions on yfinance info dicts + price momentum.

No network calls here; this module receives pre-fetched data and returns scores.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field


@dataclass
class ScreenerRow:
    ticker: str
    name: str = ""
    sector: str = ""
    industry: str = ""
    country: str = ""
    market_cap: float = field(default_factory=lambda: float("nan"))
    currency: str = ""
    # composite scores 0–100
    overall_score: float = field(default_factory=lambda: float("nan"))
    fundamental_score: float = field(default_factory=lambda: float("nan"))
    valuation_score: float = field(default_factory=lambda: float("nan"))
    trend_score: float = field(default_factory=lambda: float("nan"))
    insider_score: float = field(default_factory=lambda: float("nan"))  # Phase 20
    # key metrics
    trailing_pe: float = field(default_factory=lambda: float("nan"))
    forward_pe: float = field(default_factory=lambda: float("nan"))
    price_to_book: float = field(default_factory=lambda: float("nan"))
    dividend_yield: float = field(default_factory=lambda: float("nan"))
    revenue_growth: float = field(default_factory=lambda: float("nan"))
    earnings_growth: float = field(default_factory=lambda: float("nan"))
    gross_margin: float = field(default_factory=lambda: float("nan"))
    operating_margin: float = field(default_factory=lambda: float("nan"))
    return_on_equity: float = field(default_factory=lambda: float("nan"))
    debt_to_equity: float = field(default_factory=lambda: float("nan"))
    # 1M / 3M / 6M price momentum
    mom_1m: float = field(default_factory=lambda: float("nan"))
    mom_3m: float = field(default_factory=lambda: float("nan"))
    mom_6m: float = field(default_factory=lambda: float("nan"))
    error: str = ""


def _nan(v: object) -> float:
    """Cast *v* to float, returning nan on None / non-finite."""
    if v is None:
        return float("nan")
    try:
        f = float(v)
        return f if math.isfinite(f) else float("nan")
    except (TypeError, ValueError):
        return float("nan")


def _clamp(v: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, v))


def _fundamental_score(info: dict) -> float:
    """Score 0–100 from revenue/earnings growth, margins, ROE, and D/E.

    Each sub-metric is mapped to [0, 100] with domain knowledge anchors:
      - Revenue growth  0 % → 50, +16 % → 100
      - Earnings growth 0 % → 50, +25 % → 100
      - Gross margin    linear 0–100
      - Op. margin      0 % → 0, 40 % → 100
      - ROE             0 % → 0, 33 % → 100
      - D/E ratio       0x → 100, 4x → 0  (yfinance gives D/E as %)
    """
    scores: list[float] = []

    rev_g = _nan(info.get("revenueGrowth"))
    if not math.isnan(rev_g):
        scores.append(_clamp(50.0 + rev_g * 300.0))

    eps_g = _nan(info.get("earningsGrowth"))
    if not math.isnan(eps_g):
        scores.append(_clamp(50.0 + eps_g * 200.0))

    gm = _nan(info.get("grossMargins"))
    if not math.isnan(gm):
        scores.append(_clamp(gm * 100.0))

    om = _nan(info.get("operatingMargins"))
    if not math.isnan(om):
        scores.append(_clamp(om * 250.0))

    roe = _nan(info.get("returnOnEquity"))
    if not math.isnan(roe):
        scores.append(_clamp(roe * 300.0))

    de_pct = _nan(info.get("debtToEquity"))  # yfinance returns e.g. 150 for 1.5×
    if not math.isnan(de_pct):
        de_ratio = de_pct / 100.0
        scores.append(_clamp(100.0 - de_ratio * 25.0))

    return float(sum(scores) / len(scores)) if scores else float("nan")


def _valuation_score(info: dict) -> float:
    """Score 0–100; cheaper multiples → higher score.

    Anchors:
      - Trailing P/E 10 → 85, 30 → 55, 67 → 0
      - Forward P/E  10 → 82, 25 → 55, 56 → 0
      - Price/Book    1 → 92, 5 → 60, 12.5 → 0
    """
    scores: list[float] = []

    pe = _nan(info.get("trailingPE"))
    if not math.isnan(pe) and pe > 0:
        scores.append(_clamp(100.0 - pe * 1.5))

    fpe = _nan(info.get("forwardPE"))
    if not math.isnan(fpe) and fpe > 0:
        scores.append(_clamp(100.0 - fpe * 1.8))

    pb = _nan(info.get("priceToBook"))
    if not math.isnan(pb) and pb > 0:
        scores.append(_clamp(100.0 - pb * 8.0))

    return float(sum(scores) / len(scores)) if scores else float("nan")


def _trend_score(mom_1m: float, mom_3m: float, mom_6m: float) -> float:
    """Score 0–100 from price momentum; 50 = flat, > 50 = positive.

    Weights: 1M 50%, 3M 30%, 6M 20%.
    A +10% 1-month return maps to 70; -10% maps to 30.
    """
    weighted: list[tuple[float, float]] = []
    for mom, w in [(mom_1m, 0.5), (mom_3m, 0.3), (mom_6m, 0.2)]:
        if not math.isnan(mom):
            weighted.append((_clamp(50.0 + mom * 200.0), w))
    if not weighted:
        return float("nan")
    total_w = sum(w for _, w in weighted)
    return sum(s * w for s, w in weighted) / total_w


def _overall_score(fund: float, val: float, trend: float) -> float:
    """Weighted composite: 40% fundamentals, 35% valuation, 25% trend."""
    parts = [(fund, 0.40), (val, 0.35), (trend, 0.25)]
    valid = [(s, w) for s, w in parts if not math.isnan(s)]
    if not valid:
        return float("nan")
    total_w = sum(w for _, w in valid)
    return sum(s * w for s, w in valid) / total_w


def score_from_info(
    ticker: str,
    info: dict,
    mom_1m: float = float("nan"),
    mom_3m: float = float("nan"),
    mom_6m: float = float("nan"),
) -> ScreenerRow:
    """Compute a ScreenerRow from a pre-fetched yfinance *info* dict.

    The caller is responsible for fetching and caching *info*.  This function
    is pure (no I/O) and safe to call from any layer.
    """
    if not info:
        return ScreenerRow(ticker=ticker, error="no data")

    fund  = _fundamental_score(info)
    val   = _valuation_score(info)
    trend = _trend_score(mom_1m, mom_3m, mom_6m)
    overall = _overall_score(fund, val, trend)

    return ScreenerRow(
        ticker            = ticker,
        name              = str(info.get("longName") or info.get("shortName") or ""),
        sector            = str(info.get("sector") or ""),
        industry          = str(info.get("industry") or ""),
        country           = str(info.get("country") or ""),
        market_cap        = _nan(info.get("marketCap")),
        currency          = str(info.get("currency") or ""),
        overall_score     = overall,
        fundamental_score = fund,
        valuation_score   = val,
        trend_score       = trend,
        trailing_pe       = _nan(info.get("trailingPE")),
        forward_pe        = _nan(info.get("forwardPE")),
        price_to_book     = _nan(info.get("priceToBook")),
        dividend_yield    = _nan(info.get("dividendYield")),
        revenue_growth    = _nan(info.get("revenueGrowth")),
        earnings_growth   = _nan(info.get("earningsGrowth")),
        gross_margin      = _nan(info.get("grossMargins")),
        operating_margin  = _nan(info.get("operatingMargins")),
        return_on_equity  = _nan(info.get("returnOnEquity")),
        debt_to_equity    = _nan(info.get("debtToEquity")),
        mom_1m            = mom_1m,
        mom_3m            = mom_3m,
        mom_6m            = mom_6m,
    )
