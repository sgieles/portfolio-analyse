"""Portfolio Health Score — 0 to 100 composite quality indicator.

Five equally-weighted components (20 pts each):

  Component           Best                Worst
  ────────────────────────────────────────────────
  Sharpe quality      Sharpe ≥ 2.0        Sharpe ≤ 0
  Drawdown risk       Max DD ≤ 5 %        Max DD ≥ 50 %
  Volatility          Ann. vol ≤ 10 %     Ann. vol ≥ 40 %
  Diversification     div_score = 1       div_score = 0
  Concentration       max weight ≤ 20 %   max weight ≥ 80 %

All thresholds use linear interpolation between best and worst values.
NaN inputs score 0 for that component.
"""

from __future__ import annotations

import math

import numpy as np


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def _linear(v: float, v_best: float, v_worst: float, max_pts: float) -> float:
    """Map v linearly from v_best (→ max_pts) to v_worst (→ 0)."""
    if v_best == v_worst:
        return 0.0
    frac = (v - v_worst) / (v_best - v_worst)
    return max_pts * _clamp(frac, 0.0, 1.0)


def _score_sharpe(sharpe: float, pts: float = 20.0) -> float:
    if math.isnan(sharpe):
        return 0.0
    return _linear(sharpe, v_best=2.0, v_worst=0.0, max_pts=pts)


def _score_drawdown(max_drawdown: float, pts: float = 20.0) -> float:
    if math.isnan(max_drawdown):
        return 0.0
    # Lower drawdown is better
    return _linear(max_drawdown, v_best=0.05, v_worst=0.50, max_pts=pts)


def _score_volatility(volatility: float, pts: float = 20.0) -> float:
    if math.isnan(volatility):
        return 0.0
    return _linear(volatility, v_best=0.10, v_worst=0.40, max_pts=pts)


def _score_diversification(div_score: float, pts: float = 20.0) -> float:
    if math.isnan(div_score):
        return 0.0
    return max(0.0, min(pts, div_score * pts))


def _score_concentration(weights: dict[str, float], pts: float = 20.0) -> float:
    if not weights:
        return 0.0
    max_w = max(weights.values())
    return _linear(max_w, v_best=0.20, v_worst=0.80, max_pts=pts)


def portfolio_health_score(
    sharpe: float,
    max_drawdown: float,
    volatility: float,
    diversification_score: float,
    weights: dict[str, float],
) -> tuple[float, dict[str, float]]:
    """Compute the portfolio health score (0–100) and its component breakdown.

    Args:
        sharpe:               Annualised Sharpe ratio.
        max_drawdown:         Peak-to-trough drawdown fraction (positive, e.g. 0.25).
        volatility:           Annualised portfolio volatility fraction (e.g. 0.18).
        diversification_score: Diversification ratio score in [0, 1].
        weights:              Portfolio weights dict (tickers → fractions).

    Returns:
        Tuple of (total_score, component_dict) where total_score is in [0, 100]
        and component_dict has keys:
          "sharpe", "drawdown", "volatility", "diversification", "concentration".
    """
    components = {
        "sharpe":          _score_sharpe(sharpe),
        "drawdown":        _score_drawdown(max_drawdown),
        "volatility":      _score_volatility(volatility),
        "diversification": _score_diversification(diversification_score),
        "concentration":   _score_concentration(weights),
    }
    total = sum(components.values())
    return round(total, 1), components
