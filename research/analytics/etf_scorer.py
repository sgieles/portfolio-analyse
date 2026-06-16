"""ETF scoring engine — pure analytics, no I/O.

Scores an ETF on four dimensions and produces a 0-100 composite.
All inputs are pre-fetched by the caller.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from research.data.etf_fetcher import ETFProfile

_NAN = float("nan")
_TRADING_DAYS = 252


# ── Result model ───────────────────────────────────────────────────────────────

@dataclass
class ETFAnalysis:
    ticker: str
    profile: ETFProfile

    # ── Performance (computed from price history) ─────────────────────────────
    return_1y:      float = _NAN
    return_3y_ann:  float = _NAN    # annualised
    return_5y_ann:  float = _NAN
    volatility_1y:  float = _NAN    # annualised std dev
    sharpe_1y:      float = _NAN    # vs 0 % risk-free (ETF context)
    max_drawdown:   float = _NAN    # negative fraction, e.g. -0.25
    tracking_error: float = _NAN    # annualised, vs SPY

    # ── Concentration ─────────────────────────────────────────────────────────
    top10_weight: float = _NAN      # sum of top-10 holding weights
    hhi_sector:   float = _NAN      # Herfindahl-Hirschman Index of sector weights

    # ── Sub-scores (0-100) ────────────────────────────────────────────────────
    cost_score:           float = _NAN
    diversification_score: float = _NAN
    performance_score:    float = _NAN
    risk_score:           float = _NAN

    # ── Composite ─────────────────────────────────────────────────────────────
    etf_score: float = 50.0
    signal: str = "Neutral"   # "Excellent" / "Good" / "Neutral" / "Weak" / "Poor"

    # ── Explainability ────────────────────────────────────────────────────────
    strengths:  list[str] = field(default_factory=list)
    weaknesses: list[str] = field(default_factory=list)
    score_components: dict[str, float] = field(default_factory=dict)


# ── Scoring helpers ────────────────────────────────────────────────────────────

def _ok(v: float) -> bool:
    return math.isfinite(v)


def _score_expense_ratio(er: float) -> float:
    """Lower expense ratio = higher score.

    < 0.05% → 95   (ultra-cheap passive)
    0.05-0.10% → 88
    0.10-0.20% → 78
    0.20-0.50% → 62
    0.50-1.00% → 42
    > 1.00%   → 20
    """
    if not _ok(er):
        return _NAN
    if er < 0.0005:
        return 95.0
    if er < 0.0010:
        return 88.0
    if er < 0.0020:
        return 78.0
    if er < 0.0050:
        return 62.0
    if er < 0.0100:
        return 42.0
    return 20.0


def _score_diversification(n_holdings: int, top10_weight: float,
                            hhi_sector: float) -> float:
    """Higher holdings count, lower concentration = better.

    Components:
    - Holdings count (40 %): log-scaled, 500+ = 80, 100-500 = 60-80, <10 = 20
    - Top-10 weight (40 %): <20 % = 90, 20-40 % = 70, 40-60 % = 50, >60 % = 25
    - Sector HHI (20 %): <0.10 = 80, 0.10-0.20 = 60, 0.20-0.40 = 40, >0.40 = 20
    """
    parts: list[tuple[float, float]] = []

    if n_holdings > 0:
        # log scale: 1 holding → 0, 500+ → 80
        cnt_score = min(80.0, 80.0 * math.log1p(n_holdings) / math.log1p(500))
        parts.append((cnt_score, 0.40))

    if _ok(top10_weight):
        if top10_weight < 0.20:
            w10_score = 90.0
        elif top10_weight < 0.40:
            w10_score = 70.0
        elif top10_weight < 0.60:
            w10_score = 50.0
        else:
            w10_score = 25.0
        parts.append((w10_score, 0.40))

    if _ok(hhi_sector):
        if hhi_sector < 0.10:
            hhi_score = 80.0
        elif hhi_sector < 0.20:
            hhi_score = 60.0
        elif hhi_sector < 0.40:
            hhi_score = 40.0
        else:
            hhi_score = 20.0
        parts.append((hhi_score, 0.20))

    if not parts:
        return _NAN
    total_w = sum(w for _, w in parts)
    return sum(s * w for s, w in parts) / total_w


def _score_performance(return_1y: float, return_3y_ann: float,
                        sharpe_1y: float) -> float:
    """Risk-adjusted performance score.

    Components:
    - Sharpe 1Y (50 %): >1.0 = 85, 0.5-1.0 = 70, 0-0.5 = 55, <0 = 30
    - 1Y return (30 %): >20 % = 85, 10-20 % = 70, 0-10 % = 55, <0 = 30
    - 3Y ann return (20 %): >12 % = 85, 8-12 % = 70, 0-8 % = 55, <0 = 30
    """
    parts: list[tuple[float, float]] = []

    if _ok(sharpe_1y):
        if sharpe_1y > 1.0:
            s = 85.0
        elif sharpe_1y > 0.5:
            s = 70.0
        elif sharpe_1y > 0:
            s = 55.0
        else:
            s = 30.0
        parts.append((s, 0.50))

    if _ok(return_1y):
        if return_1y > 0.20:
            s = 85.0
        elif return_1y > 0.10:
            s = 70.0
        elif return_1y > 0:
            s = 55.0
        else:
            s = 30.0
        parts.append((s, 0.30))

    if _ok(return_3y_ann):
        if return_3y_ann > 0.12:
            s = 85.0
        elif return_3y_ann > 0.08:
            s = 70.0
        elif return_3y_ann > 0:
            s = 55.0
        else:
            s = 30.0
        parts.append((s, 0.20))

    if not parts:
        return _NAN
    total_w = sum(w for _, w in parts)
    return sum(s * w for s, w in parts) / total_w


def _score_risk(volatility_1y: float, max_drawdown: float,
                tracking_error: float) -> float:
    """Lower volatility and drawdown = better risk score.

    Components:
    - Volatility 1Y (40 %): <10 % = 85, 10-15 % = 75, 15-20 % = 60, >25 % = 35
    - Max drawdown (40 %): >-10 % = 85, -10 to -20 % = 70, -20 to -35 % = 50, < -35 % = 25
    - Tracking error (20 %): only scored for index ETFs; <0.5 % = 85, 0.5-1 % = 70, >2 % = 40
    """
    parts: list[tuple[float, float]] = []

    if _ok(volatility_1y):
        if volatility_1y < 0.10:
            s = 85.0
        elif volatility_1y < 0.15:
            s = 75.0
        elif volatility_1y < 0.20:
            s = 60.0
        elif volatility_1y < 0.25:
            s = 48.0
        else:
            s = 35.0
        parts.append((s, 0.40))

    if _ok(max_drawdown):
        dd = abs(max_drawdown)
        if dd < 0.10:
            s = 85.0
        elif dd < 0.20:
            s = 70.0
        elif dd < 0.35:
            s = 50.0
        else:
            s = 25.0
        parts.append((s, 0.40))

    if _ok(tracking_error):
        if tracking_error < 0.005:
            s = 85.0
        elif tracking_error < 0.010:
            s = 70.0
        elif tracking_error < 0.020:
            s = 55.0
        else:
            s = 40.0
        parts.append((s, 0.20))

    if not parts:
        return _NAN
    total_w = sum(w for _, w in parts)
    return sum(s * w for s, w in parts) / total_w


def _compute_top10_weight(holdings: list[dict]) -> float:
    weights = [h.get("weight", _NAN) for h in holdings[:10]]
    valid   = [w for w in weights if isinstance(w, float) and _ok(w)]
    return sum(valid) if valid else _NAN


def _compute_hhi(sector_weights: dict[str, float]) -> float:
    """Herfindahl-Hirschman Index of sector weights. 0 = perfectly spread."""
    valid = [v for v in sector_weights.values() if _ok(v)]
    if not valid:
        return _NAN
    return sum(w * w for w in valid)


def _price_metrics(prices: pd.DataFrame,
                   benchmark: pd.DataFrame) -> dict[str, float]:
    """Compute return, volatility, Sharpe, drawdown and tracking error."""
    result: dict[str, float] = {}
    if prices.empty or "Close" not in prices.columns:
        return result

    close = prices["Close"].dropna()
    if len(close) < 22:
        return result

    rets = close.pct_change().dropna()

    # 1Y window
    rets_1y = rets.iloc[-_TRADING_DAYS:] if len(rets) >= _TRADING_DAYS else rets
    result["return_1y"]     = float((close.iloc[-1] / close.iloc[-min(_TRADING_DAYS, len(close)-1)]) - 1)
    result["volatility_1y"] = float(rets_1y.std() * math.sqrt(_TRADING_DAYS))
    result["sharpe_1y"]     = (
        float(rets_1y.mean() * _TRADING_DAYS / (rets_1y.std() * math.sqrt(_TRADING_DAYS)))
        if rets_1y.std() > 0 else _NAN
    )

    # 3Y annualised
    if len(close) >= _TRADING_DAYS * 3:
        result["return_3y_ann"] = float(
            (close.iloc[-1] / close.iloc[-_TRADING_DAYS * 3]) ** (1 / 3) - 1
        )

    # 5Y annualised
    if len(close) >= _TRADING_DAYS * 5:
        result["return_5y_ann"] = float(
            (close.iloc[-1] / close.iloc[-_TRADING_DAYS * 5]) ** (1 / 5) - 1
        )

    # Max drawdown (over full history)
    cumulative = (1 + rets).cumprod()
    peak       = cumulative.cummax()
    drawdown   = (cumulative - peak) / peak
    result["max_drawdown"] = float(drawdown.min())

    # Tracking error vs benchmark (1Y)
    if not benchmark.empty and "Close" in benchmark.columns:
        try:
            bclose = benchmark["Close"].dropna()
            brets  = bclose.pct_change().dropna()
            # Align on common dates
            common = rets.index.intersection(brets.index)
            if len(common) >= 22:
                r1 = rets.loc[common].iloc[-_TRADING_DAYS:]
                r2 = brets.loc[common].iloc[-_TRADING_DAYS:]
                diff = r1.values - r2.values[:len(r1)]
                result["tracking_error"] = float(np.std(diff, ddof=1) * math.sqrt(_TRADING_DAYS))
        except Exception:
            pass

    return result


def _build_signals(a: ETFAnalysis) -> tuple[list[str], list[str]]:
    strengths:  list[str] = []
    weaknesses: list[str] = []

    # Cost
    if _ok(a.profile.expense_ratio):
        er_pct = a.profile.expense_ratio * 100
        if er_pct < 0.10:
            strengths.append(f"Extremely low expense ratio ({er_pct:.2f}%) — ideal for buy-and-hold")
        elif er_pct < 0.20:
            strengths.append(f"Low expense ratio ({er_pct:.2f}%) — cost-efficient")
        elif er_pct > 0.80:
            weaknesses.append(f"High expense ratio ({er_pct:.2f}%) erodes long-term returns")

    # Diversification
    if _ok(a.top10_weight):
        if a.top10_weight > 0.60:
            weaknesses.append(
                f"High concentration risk: top-10 holdings represent {a.top10_weight*100:.0f}% of the fund"
            )
        elif a.top10_weight < 0.25:
            strengths.append("Well-diversified: low concentration in top holdings")

    if a.profile.n_holdings > 200:
        strengths.append(f"Broad exposure across {a.profile.n_holdings} holdings")
    elif a.profile.n_holdings > 0 and a.profile.n_holdings < 30:
        weaknesses.append(f"Concentrated portfolio with only {a.profile.n_holdings} holdings")

    # Performance
    if _ok(a.sharpe_1y):
        if a.sharpe_1y > 1.0:
            strengths.append(f"Strong risk-adjusted return: Sharpe ratio of {a.sharpe_1y:.2f}")
        elif a.sharpe_1y < 0:
            weaknesses.append("Negative Sharpe ratio — returns did not compensate for risk")

    # Risk
    if _ok(a.max_drawdown) and a.max_drawdown < -0.35:
        weaknesses.append(
            f"Large historical drawdown ({a.max_drawdown*100:.0f}%) — significant tail risk"
        )

    # Tracking
    if _ok(a.tracking_error) and a.tracking_error < 0.005:
        strengths.append("Tight tracking error vs market — efficient index replication")
    elif _ok(a.tracking_error) and a.tracking_error > 0.02:
        weaknesses.append(
            f"Wide tracking error ({a.tracking_error*100:.1f}%) — fund deviates from benchmark"
        )

    return strengths, weaknesses


# ── Main entry point ───────────────────────────────────────────────────────────

def score_etf(
    ticker: str,
    profile: ETFProfile,
    price_history: pd.DataFrame,
    benchmark_history: pd.DataFrame,
) -> ETFAnalysis:
    """Compute a full ETFAnalysis.

    Args:
        ticker:           Ticker symbol.
        profile:          ETFProfile from etf_fetcher.
        price_history:    Close price DataFrame (2y+ recommended).
        benchmark_history: Benchmark (e.g. SPY) close price for tracking error.
    """
    a = ETFAnalysis(ticker=ticker, profile=profile)

    # ── Price metrics ──────────────────────────────────────────────────────────
    pm = _price_metrics(price_history, benchmark_history)
    a.return_1y     = pm.get("return_1y",     _NAN)
    a.return_3y_ann = pm.get("return_3y_ann", _NAN)
    a.return_5y_ann = pm.get("return_5y_ann", _NAN)
    a.volatility_1y = pm.get("volatility_1y", _NAN)
    a.sharpe_1y     = pm.get("sharpe_1y",     _NAN)
    a.max_drawdown  = pm.get("max_drawdown",  _NAN)
    a.tracking_error = pm.get("tracking_error", _NAN)

    # Fall back to yfinance pre-computed returns if price history too short
    if not _ok(a.return_3y_ann) and _ok(profile.return_3y):
        a.return_3y_ann = profile.return_3y
    if not _ok(a.return_5y_ann) and _ok(profile.return_5y):
        a.return_5y_ann = profile.return_5y

    # ── Concentration metrics ──────────────────────────────────────────────────
    a.top10_weight = _compute_top10_weight(profile.top_holdings)
    a.hhi_sector   = _compute_hhi(profile.sector_weights)

    # ── Sub-scores ─────────────────────────────────────────────────────────────
    a.cost_score           = _score_expense_ratio(profile.expense_ratio)
    a.diversification_score = _score_diversification(
        profile.n_holdings, a.top10_weight, a.hhi_sector
    )
    a.performance_score = _score_performance(a.return_1y, a.return_3y_ann, a.sharpe_1y)
    a.risk_score        = _score_risk(a.volatility_1y, a.max_drawdown, a.tracking_error)

    # ── Composite (weights: cost 25%, diversification 30%, performance 25%, risk 20%) ──
    pairs = [
        (a.cost_score,            0.25),
        (a.diversification_score, 0.30),
        (a.performance_score,     0.25),
        (a.risk_score,            0.20),
    ]
    valid = [(s, w) for s, w in pairs if _ok(s)]
    if valid:
        total_w = sum(w for _, w in valid)
        a.etf_score = sum(s * w for s, w in valid) / total_w
    a.etf_score = max(0.0, min(100.0, a.etf_score))

    a.score_components = {
        "Cost":            a.cost_score,
        "Diversification": a.diversification_score,
        "Performance":     a.performance_score,
        "Risk":            a.risk_score,
    }

    # Signal
    s = a.etf_score
    if s >= 72:
        a.signal = "Excellent"
    elif s >= 60:
        a.signal = "Good"
    elif s >= 45:
        a.signal = "Neutral"
    elif s >= 32:
        a.signal = "Weak"
    else:
        a.signal = "Poor"

    a.strengths, a.weaknesses = _build_signals(a)
    return a
