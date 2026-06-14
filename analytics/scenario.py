"""Scenario / stress-test analytics — pure functions, no Qt, no I/O.

Method:
  Portfolio impact = Σ w_i × β_i × r_market  (beta-weighted CAPM shock)
  Stressed volatility is computed from a stressed correlation matrix:
    corr_stressed = corr_base + (1 − corr_base) × stress_factor
  where stress_factor models the well-known correlation surge in downturns.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from utils.constants import GROWTH_START_VALUE, TRADING_DAYS_PER_YEAR

# ── Default scenarios ────────────────────────────────────────────────────────
DEFAULT_SCENARIOS: dict[str, float] = {
    "Bull Market":    0.15,
    "Mild Recession": -0.10,
    "Recession":      -0.20,
    "Severe Crash":   -0.35,
}

# Correlation stress factor per scenario (0 = unchanged, 1 = all corr → 1)
_STRESS_FACTORS: dict[str, float] = {
    "Bull Market":    0.00,
    "Mild Recession": 0.10,
    "Recession":      0.20,
    "Severe Crash":   0.40,
}


@dataclass
class ScenarioResult:
    """Estimated portfolio impact of one stress-test scenario."""

    name: str
    market_return: float          # e.g. −0.20 for Recession
    portfolio_return: float       # beta-weighted estimate
    new_value: float              # start_value × (1 + portfolio_return)
    stressed_vol: float           # annualised vol in stressed conditions
    asset_impacts: dict[str, float] = field(default_factory=dict)  # per-asset est. return


def _stressed_portfolio_vol(
    returns: pd.DataFrame,
    weights: dict[str, float],
    stress_factor: float,
    trading_days: int = TRADING_DAYS_PER_YEAR,
) -> float:
    """Portfolio vol under stressed (higher) correlations.

    Formula:
      corr_stressed = corr_base + (1 − corr_base) × stress_factor
      cov_stressed  = corr_stressed ⊙ outer(σ_i, σ_j)
      σ_p = √(w^T cov_stressed w) × √trading_days
    """
    tickers = [t for t in weights if t in returns.columns]
    if not tickers:
        return float("nan")

    w   = np.array([weights[t] for t in tickers])
    cov = returns[tickers].cov(ddof=1).values          # daily covariance
    vol_diag = np.sqrt(np.diag(cov))                   # per-asset daily σ

    outer_vols = np.outer(vol_diag, vol_diag)
    # Guard against zero volatility
    with np.errstate(invalid="ignore"):
        corr = np.where(outer_vols > 0.0, cov / outer_vols, 0.0)
    corr = np.clip(corr, -1.0, 1.0)

    corr_stressed = corr + (1.0 - corr) * stress_factor
    cov_stressed  = corr_stressed * outer_vols

    port_var = float(w @ cov_stressed @ w)
    if port_var < 0.0:
        port_var = 0.0
    return float(np.sqrt(port_var) * np.sqrt(trading_days))


def run_scenario_analysis(
    daily_returns: pd.DataFrame,
    weights: dict[str, float],
    benchmark_returns: pd.Series,
    scenarios: dict[str, float] | None = None,
    start_value: float = GROWTH_START_VALUE,
) -> list[ScenarioResult]:
    """Run stress tests for each scenario.

    Args:
        daily_returns:     Daily return DataFrame (columns = tickers).
        weights:           Portfolio weights dict.
        benchmark_returns: Daily benchmark returns (same date range).
        scenarios:         Dict {name: market_return}. Defaults to 4 standard scenarios.
        start_value:       Current portfolio value (base for new_value).

    Returns:
        List of ScenarioResult (one per scenario), ordered as in *scenarios*.
    """
    if scenarios is None:
        scenarios = DEFAULT_SCENARIOS

    # Compute per-asset beta vs benchmark
    tickers_ok = [t for t in weights if t in daily_returns.columns]
    betas: dict[str, float] = {}
    bench_var = float(benchmark_returns.var(ddof=1))
    for ticker in tickers_ok:
        aligned = pd.concat(
            [daily_returns[ticker], benchmark_returns], axis=1
        ).dropna()
        if len(aligned) < 2 or bench_var == 0.0:
            betas[ticker] = 1.0
        else:
            cov_ab = aligned.cov(ddof=1).iloc[0, 1]
            betas[ticker] = float(cov_ab / bench_var)

    results: list[ScenarioResult] = []
    for name, market_ret in scenarios.items():
        # Beta-weighted portfolio return
        port_ret = sum(
            weights.get(t, 0.0) * betas.get(t, 1.0) * market_ret
            for t in tickers_ok
        )
        new_val  = start_value * (1.0 + port_ret)
        s_factor = _STRESS_FACTORS.get(name, max(0.0, -market_ret))
        s_vol    = _stressed_portfolio_vol(daily_returns, weights, s_factor)

        asset_impacts = {
            t: betas.get(t, 1.0) * market_ret for t in tickers_ok
        }

        results.append(ScenarioResult(
            name=name,
            market_return=market_ret,
            portfolio_return=port_ret,
            new_value=new_val,
            stressed_vol=s_vol,
            asset_impacts=asset_impacts,
        ))

    return results
