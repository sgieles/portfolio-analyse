"""Portfolio optimizers wrapping PyPortfolioOpt.

Three strategies:
  1. Maximum Sharpe Ratio  — highest risk-adjusted return
  2. Minimum Variance      — lowest portfolio volatility
  3. Black-Litterman       — market-equilibrium prior (equal-weighted), no views

All functions are pure: prices + settings in, OptimizationResult out.
No Qt, no I/O.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from pypfopt import EfficientFrontier
from pypfopt import expected_returns as ppo_er
from pypfopt import risk_models as ppo_rm

from analytics.returns import (
    annualized_return,
    capm_expected_return,
    cagr,
    daily_returns,
    portfolio_daily_returns,
    portfolio_value_series,
)
from analytics.risk import (
    historical_var,
    max_drawdown as _max_drawdown,
    portfolio_beta,
    portfolio_volatility,
    sharpe_ratio,
)
from models.results import OptimizationResult
from models.settings import AnalysisSettings, ExpectedReturnMethod
from utils.constants import TRADING_DAYS_PER_YEAR
from utils.logging import get_logger

log = get_logger(__name__)

# Default weight bounds: long-only, fully invested
_DEFAULT_BOUNDS: tuple[float, float] = (0.0, 1.0)


# ── Internal helpers ─────────────────────────────────────────────────────────

def _build_expected_returns(
    prices: pd.DataFrame,
    settings: AnalysisSettings,
    benchmark_prices: pd.Series | None = None,
) -> pd.Series:
    """Compute per-asset expected returns for the chosen method.

    Methods (from AnalysisSettings.expected_return_method):
      HISTORICAL_AVG  — daily mean × 252  (PyPortfolioOpt default)
      CAGR            — compound annual growth rate per asset
      CAPM            — R_f + β × (R_m - R_f); falls back to HISTORICAL_AVG if no benchmark
    """
    method = settings.expected_return_method

    if method == ExpectedReturnMethod.HISTORICAL_AVG:
        return ppo_er.mean_historical_return(prices, frequency=TRADING_DAYS_PER_YEAR)

    if method == ExpectedReturnMethod.CAGR:
        return pd.Series(
            {col: cagr(prices[col]) for col in prices.columns},
            name="Expected Return",
        )

    if method == ExpectedReturnMethod.CAPM:
        if benchmark_prices is None:
            log.warning(
                "CAPM expected-return method requires benchmark_prices; "
                "falling back to HISTORICAL_AVG."
            )
            return ppo_er.mean_historical_return(prices, frequency=TRADING_DAYS_PER_YEAR)
        bench_rets = benchmark_prices.pct_change().dropna()
        mkt_ret = cagr(benchmark_prices)
        mu: dict[str, float] = {}
        for col in prices.columns:
            asset_rets = prices[col].pct_change().dropna()
            aligned = pd.concat([asset_rets, bench_rets], axis=1).dropna()
            if len(aligned) < 2:
                mu[col] = settings.risk_free_rate
                continue
            cov_m = aligned.cov(ddof=1)
            bench_var = float(cov_m.iloc[1, 1])
            b = float(cov_m.iloc[0, 1] / bench_var) if bench_var > 0 else 1.0
            mu[col] = capm_expected_return(b, settings.risk_free_rate, mkt_ret)
        return pd.Series(mu, name="Expected Return")

    # Fallback
    return ppo_er.mean_historical_return(prices, frequency=TRADING_DAYS_PER_YEAR)


def _build_covariance(prices: pd.DataFrame) -> pd.DataFrame:
    """Annualised sample covariance matrix via PyPortfolioOpt."""
    return ppo_rm.sample_cov(prices, frequency=TRADING_DAYS_PER_YEAR)


def _post_optimize(
    weights: dict[str, float],
    prices: pd.DataFrame,
    settings: AnalysisSettings,
    benchmark_rets: pd.Series | None,
    method: str,
) -> OptimizationResult:
    """Compute all performance metrics for a given weight set."""
    rets_df = daily_returns(prices)
    port_rets = portfolio_daily_returns(prices, weights)

    ann_ret = annualized_return(port_rets)
    vol = portfolio_volatility(rets_df, weights)
    sharpe = sharpe_ratio(ann_ret, vol, settings.risk_free_rate)

    b = float("nan")
    if benchmark_rets is not None:
        b = portfolio_beta(port_rets, benchmark_rets)

    var_95 = historical_var(port_rets, 0.95)
    port_prices = portfolio_value_series(prices, weights)
    mdd = _max_drawdown(port_prices)

    return OptimizationResult(
        method=method,
        weights=weights,
        expected_return=ann_ret,
        volatility=vol,
        sharpe=sharpe,
        beta=b,
        var_95=var_95,
        max_drawdown=mdd,
    )


# ── Public optimizers ────────────────────────────────────────────────────────

def max_sharpe(
    prices: pd.DataFrame,
    settings: AnalysisSettings,
    benchmark_prices: pd.Series | None = None,
    weight_bounds: tuple[float, float] = _DEFAULT_BOUNDS,
) -> OptimizationResult:
    """Maximum Sharpe Ratio portfolio.

    Maximises: (E[R] - R_f) / σ_p
    subject to: weights ≥ 0, Σ weights = 1.
    """
    mu = _build_expected_returns(prices, settings, benchmark_prices)
    S = _build_covariance(prices)

    ef = EfficientFrontier(mu, S, weight_bounds=weight_bounds)
    ef.max_sharpe(risk_free_rate=settings.risk_free_rate)
    cleaned = dict(ef.clean_weights())

    bench_rets = benchmark_prices.pct_change().dropna() if benchmark_prices is not None else None
    return _post_optimize(cleaned, prices, settings, bench_rets, "max_sharpe")


def min_variance(
    prices: pd.DataFrame,
    settings: AnalysisSettings,
    benchmark_prices: pd.Series | None = None,
    weight_bounds: tuple[float, float] = _DEFAULT_BOUNDS,
) -> OptimizationResult:
    """Minimum Variance portfolio.

    Minimises: w^T Σ w
    subject to: weights ≥ 0, Σ weights = 1.
    """
    mu = _build_expected_returns(prices, settings, benchmark_prices)
    S = _build_covariance(prices)

    ef = EfficientFrontier(mu, S, weight_bounds=weight_bounds)
    ef.min_volatility()
    cleaned = dict(ef.clean_weights())

    bench_rets = benchmark_prices.pct_change().dropna() if benchmark_prices is not None else None
    return _post_optimize(cleaned, prices, settings, bench_rets, "min_variance")


def black_litterman(
    prices: pd.DataFrame,
    settings: AnalysisSettings,
    benchmark_prices: pd.Series | None = None,
    weight_bounds: tuple[float, float] = _DEFAULT_BOUNDS,
) -> OptimizationResult:
    """Black-Litterman portfolio (equal-weighted market prior, no views).

    Computes the implied equilibrium returns from an equal-weighted market
    portfolio and maximises Sharpe using those as expected returns. This is
    mathematically equivalent to Black-Litterman with no investor views and
    avoids the need to pass explicit view matrices to PyPortfolioOpt.

    Formula: π = δ Σ w_mkt
    where δ = 2.5 (standard risk-aversion) and w_mkt is the equal-weighted
    portfolio. Produces more stable, less concentrated allocations than
    optimising on raw historical returns.
    """
    S_df = _build_covariance(prices)

    n = len(prices.columns)
    w_mkt = np.ones(n) / n
    risk_aversion = 2.5  # standard market risk-aversion parameter

    mu_bl = pd.Series(
        risk_aversion * S_df.values @ w_mkt,
        index=prices.columns,
        name="BL Returns",
    )

    ef = EfficientFrontier(mu_bl, S_df, weight_bounds=weight_bounds)
    ef.max_sharpe(risk_free_rate=settings.risk_free_rate)
    cleaned = dict(ef.clean_weights())

    bench_rets = benchmark_prices.pct_change().dropna() if benchmark_prices is not None else None
    return _post_optimize(cleaned, prices, settings, bench_rets, "black_litterman")
