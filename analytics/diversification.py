"""Diversification analytics — pure functions on pandas DataFrames.

No Qt, no I/O.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from analytics.risk import annualized_volatility, portfolio_volatility
from utils.constants import TRADING_DAYS_PER_YEAR


def average_correlation(daily_rets_df: pd.DataFrame) -> float:
    """Average pairwise Pearson correlation across all asset pairs.

    Uses only the upper triangle of the correlation matrix (each pair once).
    Returns 1.0 for a single-asset portfolio (no diversification possible).
    """
    n = daily_rets_df.shape[1]
    if n < 2:
        return 1.0
    corr = daily_rets_df.corr(numeric_only=False)
    upper = corr.values[np.triu_indices(n, k=1)]
    return float(np.nanmean(upper))


def diversification_score(
    daily_rets_df: pd.DataFrame,
    weights: dict[str, float],
    trading_days: int = TRADING_DAYS_PER_YEAR,
) -> float:
    """Portfolio diversification score in [0, 1].

    Based on the Diversification Ratio (DR):
      DR = (w · σ_individual) / σ_portfolio

    Score = 1 - 1/DR   (clipped to [0, 1])

    Interpretation:
      0  → single asset or perfectly correlated assets (no benefit from mixing)
      →1 → assets have near-zero pairwise correlation (maximum diversification)
    """
    n = daily_rets_df.shape[1]
    if n < 2:
        return 0.0

    w = np.array([weights.get(col, 0.0) for col in daily_rets_df.columns])
    individual_vols = np.array([
        annualized_volatility(daily_rets_df[col], trading_days)
        for col in daily_rets_df.columns
    ])

    weighted_avg_vol = float(w @ individual_vols)
    port_vol = portfolio_volatility(daily_rets_df, weights, trading_days)

    if port_vol == 0.0 or np.isnan(port_vol) or np.isnan(weighted_avg_vol):
        return 0.0

    dr = weighted_avg_vol / port_vol
    return float(np.clip(1.0 - 1.0 / dr, 0.0, 1.0))


def risk_contributions(
    daily_rets_df: pd.DataFrame,
    weights: dict[str, float],
) -> dict[str, float]:
    """Marginal risk contribution of each asset as a fraction of total portfolio risk.

    Formula: RC_i = w_i × (Σ w)_i / (w^T Σ w)
    where Σ is the daily covariance matrix.

    Returns fractions summing to 1.0. Useful for the risk-contribution bar chart.
    """
    tickers = list(daily_rets_df.columns)
    w = np.array([weights.get(col, 0.0) for col in tickers])
    cov = daily_rets_df.cov(ddof=1).values

    marginal = cov @ w          # (Σw)_i for each asset i
    total_var = float(w @ marginal)

    if total_var <= 0.0:
        # Degenerate: fall back to weight-proportional contributions
        total_w = float(w.sum())
        return {t: float(w[i] / total_w) if total_w > 0 else 0.0 for i, t in enumerate(tickers)}

    rc = w * marginal / total_var   # each fraction sums to 1
    return {t: float(rc[i]) for i, t in enumerate(tickers)}


def return_contributions(
    ann_returns: dict[str, float],
    weights: dict[str, float],
) -> dict[str, float]:
    """Each asset's absolute contribution to portfolio return.

    Formula: contribution_i = w_i × r_i
    Note: contributions sum to the total portfolio return (weighted average).
    """
    return {
        ticker: float(weights.get(ticker, 0.0) * ret)
        for ticker, ret in ann_returns.items()
    }
