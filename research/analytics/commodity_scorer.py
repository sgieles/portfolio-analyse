"""Commodity scoring engine — momentum, trend, seasonality, volatility.

Pure analytics: no I/O, no Dash. Takes pre-fetched price history.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import pandas as pd

_NAN = float("nan")
_TD  = 252  # trading days per year


# ── Result model ───────────────────────────────────────────────────────────────

@dataclass
class CommodityAnalysis:
    ticker: str
    name:   str = ""
    group:  str = ""
    unit:   str = ""

    # Price metrics
    current_price:  float = _NAN
    return_1m:      float = _NAN
    return_3m:      float = _NAN
    return_6m:      float = _NAN
    return_1y:      float = _NAN
    return_3y_ann:  float = _NAN
    volatility_1y:  float = _NAN
    max_drawdown:   float = _NAN

    # Trend
    ma_50:        float = _NAN
    ma_200:       float = _NAN
    above_ma50:   bool  = False
    above_ma200:  bool  = False
    golden_cross: bool  = False   # MA50 > MA200

    # Seasonality: {month_name: avg_return}
    monthly_avg_returns: dict[str, float] = field(default_factory=dict)

    # Sub-scores 0–100
    momentum_score:   float = _NAN
    trend_score:      float = _NAN
    volatility_score: float = _NAN

    # Composite
    composite_score: float = 50.0
    signal: str = "Neutral"   # Bullish / Positive / Neutral / Negative / Bearish

    strengths:  list[str] = field(default_factory=list)
    weaknesses: list[str] = field(default_factory=list)
    score_components: dict[str, float] = field(default_factory=dict)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _ok(v: float) -> bool:
    return isinstance(v, (int, float)) and math.isfinite(float(v))


def _ret(prices: pd.Series, n_days: int) -> float:
    if len(prices) <= n_days:
        return _NAN
    return float(prices.iloc[-1] / prices.iloc[-n_days] - 1)


# ── Scoring functions ──────────────────────────────────────────────────────────

def _score_momentum(r1m: float, r3m: float, r6m: float, r1y: float) -> float:
    parts: list[tuple[float, float]] = []
    for ret, weight, (hi, lo) in [
        (r1m, 0.15, ( 0.03, -0.03)),
        (r3m, 0.25, ( 0.06, -0.06)),
        (r6m, 0.30, ( 0.10, -0.10)),
        (r1y, 0.30, ( 0.15, -0.15)),
    ]:
        if not _ok(ret):
            continue
        if ret >= hi:
            s = 85.0
        elif ret >= 0:
            s = 60.0
        elif ret >= lo:
            s = 40.0
        else:
            s = 20.0
        parts.append((s, weight))
    if not parts:
        return _NAN
    tw = sum(w for _, w in parts)
    return sum(s * w for s, w in parts) / tw


def _score_trend(above_ma50: bool, above_ma200: bool, golden_cross: bool) -> float:
    score = 50.0
    if above_ma200:
        score += 15
    if above_ma50:
        score += 15
    if golden_cross:
        score += 15
    if not above_ma50 and not above_ma200:
        score -= 20
    return max(0.0, min(100.0, score))


def _score_volatility(vol: float) -> float:
    if not _ok(vol):
        return _NAN
    if vol < 0.10:
        return 85.0
    if vol < 0.18:
        return 72.0
    if vol < 0.28:
        return 55.0
    if vol < 0.40:
        return 38.0
    return 22.0


def _monthly_avg(prices: pd.Series) -> dict[str, float]:
    if len(prices) < 50:
        return {}
    monthly = prices.resample("ME").last().pct_change().dropna()
    names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
             "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    result: dict[str, float] = {}
    for i, name in enumerate(names, 1):
        vals = monthly[monthly.index.month == i]
        if not vals.empty:
            result[name] = float(vals.mean())
    return result


def _build_signals(a: CommodityAnalysis) -> tuple[list[str], list[str]]:
    strengths:  list[str] = []
    weaknesses: list[str] = []

    if _ok(a.return_1y):
        if a.return_1y > 0.15:
            strengths.append(f"Strong 12-month momentum: +{a.return_1y*100:.1f}%")
        elif a.return_1y < -0.15:
            weaknesses.append(f"Weak 12-month performance: {a.return_1y*100:.1f}%")

    if a.golden_cross:
        strengths.append("Golden cross (MA50 > MA200) — bullish trend signal")
    elif not a.above_ma50 and not a.above_ma200:
        weaknesses.append("Price below both MA50 and MA200 — bearish trend")
    elif a.above_ma200 and not a.above_ma50:
        weaknesses.append("Price below MA50 — short-term momentum fading")

    if _ok(a.volatility_1y):
        if a.volatility_1y > 0.35:
            weaknesses.append(f"High volatility ({a.volatility_1y*100:.0f}% ann.) — wide price swings")
        elif a.volatility_1y < 0.15:
            strengths.append(f"Relatively low volatility ({a.volatility_1y*100:.0f}% ann.)")

    if _ok(a.max_drawdown) and a.max_drawdown < -0.40:
        weaknesses.append(f"Large historical drawdown ({a.max_drawdown*100:.0f}%)")

    if _ok(a.return_3m) and a.return_3m > 0.10:
        strengths.append(f"Strong 3-month momentum: +{a.return_3m*100:.1f}%")

    return strengths, weaknesses


# ── Main entry point ───────────────────────────────────────────────────────────

def score_commodity(
    ticker: str,
    name: str,
    group: str,
    unit: str,
    price_history: pd.DataFrame,
) -> CommodityAnalysis:
    """Compute CommodityAnalysis from a pre-fetched OHLCV DataFrame."""
    a = CommodityAnalysis(ticker=ticker, name=name, group=group, unit=unit)

    if price_history.empty or "Close" not in price_history.columns:
        return a

    close = price_history["Close"].dropna()
    if len(close) < 22:
        return a

    a.current_price = float(close.iloc[-1])

    # Returns
    a.return_1m = _ret(close, 21)
    a.return_3m = _ret(close, 63)
    a.return_6m = _ret(close, 126)
    a.return_1y = _ret(close, _TD)
    if len(close) >= _TD * 3:
        a.return_3y_ann = float((close.iloc[-1] / close.iloc[-_TD * 3]) ** (1/3) - 1)

    # Volatility (1Y)
    rets    = close.pct_change().dropna()
    rets_1y = rets.iloc[-_TD:] if len(rets) >= _TD else rets
    a.volatility_1y = float(rets_1y.std() * math.sqrt(_TD))

    # Max drawdown (full history)
    cumret       = (1 + rets).cumprod()
    peak         = cumret.cummax()
    a.max_drawdown = float(((cumret - peak) / peak).min())

    # Moving averages
    if len(close) >= 50:
        a.ma_50       = float(close.iloc[-50:].mean())
        a.above_ma50  = float(close.iloc[-1]) > a.ma_50
    if len(close) >= 200:
        a.ma_200      = float(close.iloc[-200:].mean())
        a.above_ma200 = float(close.iloc[-1]) > a.ma_200
    if _ok(a.ma_50) and _ok(a.ma_200):
        a.golden_cross = a.ma_50 > a.ma_200

    # Seasonality
    a.monthly_avg_returns = _monthly_avg(close)

    # Sub-scores
    a.momentum_score   = _score_momentum(a.return_1m, a.return_3m, a.return_6m, a.return_1y)
    a.trend_score      = _score_trend(a.above_ma50, a.above_ma200, a.golden_cross)
    a.volatility_score = _score_volatility(a.volatility_1y)

    # Composite: momentum 40 %, trend 35 %, volatility 25 %
    pairs = [
        (a.momentum_score,   0.40),
        (a.trend_score,      0.35),
        (a.volatility_score, 0.25),
    ]
    valid = [(s, w) for s, w in pairs if _ok(s)]
    if valid:
        tw = sum(w for _, w in valid)
        a.composite_score = max(0.0, min(100.0, sum(s * w for s, w in valid) / tw))

    a.score_components = {
        "Momentum":   a.momentum_score,
        "Trend":      a.trend_score,
        "Volatility": a.volatility_score,
    }

    sc = a.composite_score
    if sc >= 70:
        a.signal = "Bullish"
    elif sc >= 57:
        a.signal = "Positive"
    elif sc >= 43:
        a.signal = "Neutral"
    elif sc >= 30:
        a.signal = "Negative"
    else:
        a.signal = "Bearish"

    a.strengths, a.weaknesses = _build_signals(a)
    return a
