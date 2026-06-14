"""Efficient frontier sampling for the chart layer.

Provides risk/return coordinates for the frontier curve, plus the four
marked portfolios (current, Max Sharpe, Min Variance, Black-Litterman).
No Qt, no I/O.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from pypfopt import EfficientFrontier  # noqa: F401 (re-exported via optimizers)

from optimization.optimizers import (
    _build_covariance,
    _build_expected_returns,
    black_litterman,
    max_sharpe,
    min_variance,
)
from analytics.returns import annualized_return, portfolio_daily_returns
from analytics.risk import portfolio_volatility, sharpe_ratio
from models.results import OptimizationResult
from models.settings import AnalysisSettings
from utils.logging import get_logger

log = get_logger(__name__)


@dataclass
class FrontierData:
    """All data needed to draw the efficient-frontier chart."""

    # Frontier curve (list of risk/return coordinates)
    frontier_risks: list[float]
    frontier_returns: list[float]

    # Four marked portfolios
    current: OptimizationResult
    max_sharpe_result: OptimizationResult
    min_variance_result: OptimizationResult
    black_litterman_result: OptimizationResult


def sample_frontier(
    prices: pd.DataFrame,
    settings: AnalysisSettings,
    n_points: int = 60,
) -> tuple[list[float], list[float]]:
    """Sample the mean-variance efficient frontier.

    Returns:
        (risks, returns): two parallel lists of floats for plotting.
        The curve runs from the minimum-variance point to the max-return point.
    """
    mu = _build_expected_returns(prices, settings)
    S = _build_covariance(prices)

    ret_min = float(mu.min())
    ret_max = float(mu.max())

    # Narrow the range slightly to avoid boundary infeasibility
    targets = np.linspace(ret_min * 1.001, ret_max * 0.999, n_points)

    risks: list[float] = []
    returns: list[float] = []

    for target in targets:
        try:
            ef = EfficientFrontier(mu, S, weight_bounds=(0.0, 1.0))
            ef.efficient_return(target_return=float(target))
            perf = ef.portfolio_performance(
                verbose=False,
                risk_free_rate=settings.risk_free_rate,
            )
            risks.append(float(perf[1]))
            returns.append(float(perf[0]))
        except Exception as exc:  # noqa: BLE001
            log.debug("Frontier point skipped (target=%.4f): %s", target, exc)

    return risks, returns


def build_frontier_data(
    prices: pd.DataFrame,
    current_weights: dict[str, float],
    settings: AnalysisSettings,
    benchmark_prices: pd.Series | None = None,
    n_points: int = 60,
) -> FrontierData:
    """Compute all frontier chart data in one call.

    Args:
        prices:          Aligned adjusted-close price DataFrame.
        current_weights: User's current portfolio weights.
        settings:        Analysis settings.
        benchmark_prices: Optional benchmark for beta computation.
        n_points:        Number of points to sample along the frontier.

    Returns:
        FrontierData with the curve and all four marked portfolios.
    """
    # Frontier curve
    f_risks, f_returns = sample_frontier(prices, settings, n_points)

    # Current portfolio point
    rets_df = prices.pct_change().dropna()
    port_rets = portfolio_daily_returns(prices, current_weights)
    ann_ret = annualized_return(port_rets)
    vol = portfolio_volatility(rets_df, current_weights)
    current_result = OptimizationResult(
        method="current",
        weights=current_weights,
        expected_return=ann_ret,
        volatility=vol,
        sharpe=sharpe_ratio(ann_ret, vol, settings.risk_free_rate),
    )

    # Optimized portfolios
    ms = max_sharpe(prices, settings, benchmark_prices)
    mv = min_variance(prices, settings, benchmark_prices)
    bl = black_litterman(prices, settings, benchmark_prices)

    return FrontierData(
        frontier_risks=f_risks,
        frontier_returns=f_returns,
        current=current_result,
        max_sharpe_result=ms,
        min_variance_result=mv,
        black_litterman_result=bl,
    )
