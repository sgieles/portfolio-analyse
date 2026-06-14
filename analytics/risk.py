"""Risk analytics — pure functions on pandas Series/DataFrames.

No Qt, no I/O. Conventions (from CLAUDE.md):
  - Volatility = daily std × √252
  - Sharpe     = (ann_return - R_f) / ann_vol
  - Sortino    = (ann_return - R_f) / ann_downside_dev
  - Beta       = Cov(asset, benchmark) / Var(benchmark)   on daily returns
  - VaR        = historical, returned as a *positive* loss magnitude
  - CVaR       = mean of losses beyond the VaR threshold
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from utils.constants import TRADING_DAYS_PER_YEAR


# ── Volatility ───────────────────────────────────────────────────────────────

def annualized_volatility(
    daily_rets: pd.Series,
    trading_days: int = TRADING_DAYS_PER_YEAR,
) -> float:
    """Annualized standard deviation of returns.

    Formula: σ_ann = σ_daily × √(trading_days)
    """
    if len(daily_rets) < 2:
        return float("nan")
    return float(daily_rets.std(ddof=1) * np.sqrt(trading_days))


def rolling_volatility(
    daily_rets: pd.Series,
    window: int = TRADING_DAYS_PER_YEAR,
    trading_days: int = TRADING_DAYS_PER_YEAR,
) -> pd.Series:
    """Rolling annualized volatility (default: 252-day / 12-month window).

    Formula: rolling_σ_ann_t = std(r_{t-window+1..t}) × √(trading_days)
    """
    rolled = daily_rets.rolling(window).std(ddof=1) * np.sqrt(trading_days)
    rolled.name = "Rolling Volatility"
    return rolled


def portfolio_volatility(
    daily_rets_df: pd.DataFrame,
    weights: dict[str, float],
    trading_days: int = TRADING_DAYS_PER_YEAR,
) -> float:
    """Annualized portfolio volatility via the full covariance matrix.

    Formula: σ_p = √(w^T Σ w) × √(trading_days)
    where Σ is the daily covariance matrix of individual asset returns.
    """
    w = np.array([weights.get(col, 0.0) for col in daily_rets_df.columns])
    cov = daily_rets_df.cov(ddof=1).values
    port_var = float(w @ cov @ w)
    if port_var < 0.0:
        return float("nan")
    return float(np.sqrt(port_var) * np.sqrt(trading_days))


# ── Downside deviation ───────────────────────────────────────────────────────

def downside_deviation(
    daily_rets: pd.Series,
    trading_days: int = TRADING_DAYS_PER_YEAR,
) -> float:
    """Annualized downside deviation (Sortino denominator).

    Target return = 0 (daily). Only returns below 0 contribute.
    Formula: DD_ann = √(mean(min(r_t, 0)²)) × √(trading_days)
    """
    if len(daily_rets) == 0:
        return float("nan")
    below_zero = np.minimum(daily_rets.values, 0.0)
    dd_daily = np.sqrt(np.mean(below_zero ** 2))
    return float(dd_daily * np.sqrt(trading_days))


# ── Sharpe / Sortino ─────────────────────────────────────────────────────────

def sharpe_ratio(
    ann_return: float,
    volatility: float,
    risk_free_rate: float,
) -> float:
    """Sharpe ratio.

    Formula: S = (ann_return - R_f) / σ_ann
    Returns NaN when volatility is zero or NaN.
    """
    if volatility == 0.0 or np.isnan(volatility) or np.isnan(ann_return):
        return float("nan")
    return float((ann_return - risk_free_rate) / volatility)


def sortino_ratio(
    daily_rets: pd.Series,
    ann_return: float,
    risk_free_rate: float,
    trading_days: int = TRADING_DAYS_PER_YEAR,
) -> float:
    """Sortino ratio.

    Formula: Sortino = (ann_return - R_f) / DD_ann
    where DD_ann is the annualized downside deviation vs. a 0% daily target.
    """
    dd = downside_deviation(daily_rets, trading_days)
    if dd == 0.0 or np.isnan(dd) or np.isnan(ann_return):
        return float("nan")
    return float((ann_return - risk_free_rate) / dd)


# ── Beta ─────────────────────────────────────────────────────────────────────

def beta(asset_rets: pd.Series, benchmark_rets: pd.Series) -> float:
    """Beta of an asset relative to a benchmark.

    Formula: β = Cov(r_asset, r_benchmark) / Var(r_benchmark)
    Uses only the overlapping date range.
    """
    aligned = pd.concat([asset_rets, benchmark_rets], axis=1).dropna()
    if len(aligned) < 2:
        return float("nan")
    cov_matrix = aligned.cov(ddof=1)
    bench_col = aligned.columns[-1]
    asset_col = aligned.columns[0]
    bench_var = cov_matrix.loc[bench_col, bench_col]
    if bench_var == 0.0:
        return float("nan")
    return float(cov_matrix.loc[asset_col, bench_col] / bench_var)


def portfolio_beta(
    portfolio_daily_rets: pd.Series,
    benchmark_rets: pd.Series,
) -> float:
    """Beta of the portfolio return series vs. the benchmark.

    Same formula as asset beta: Cov(r_p, r_bench) / Var(r_bench).
    """
    return beta(portfolio_daily_rets, benchmark_rets)


# ── Drawdown ─────────────────────────────────────────────────────────────────

def drawdown_series(prices: pd.Series) -> pd.Series:
    """Full peak-to-current drawdown time series (values in [0, 1]).

    Formula: DD_t = (peak_t - P_t) / peak_t   where peak_t = max(P_{0..t})
    """
    cummax = prices.cummax()
    dd = (cummax - prices) / cummax
    dd.name = "Drawdown"
    return dd


def max_drawdown(prices: pd.Series) -> float:
    """Maximum peak-to-trough drawdown.

    Returns a *positive* fraction (e.g. 0.35 means a 35 % drawdown).
    Formula: MDD = max(DD_t) over the full price series.
    """
    if len(prices) < 2:
        return float("nan")
    return float(drawdown_series(prices).max())


# ── VaR / CVaR (historical) ───────────────────────────────────────────────────

def historical_var(daily_rets: pd.Series, confidence: float = 0.95) -> float:
    """Historical Value at Risk at *confidence* level (positive = loss).

    Formula: VaR = -quantile(r, 1 - confidence)
    E.g. VaR_95 = 2 % means the daily loss will not exceed 2 % on 95 % of days.
    """
    if len(daily_rets) == 0:
        return float("nan")
    return float(-np.percentile(daily_rets.values, (1.0 - confidence) * 100.0))


def historical_cvar(daily_rets: pd.Series, confidence: float = 0.95) -> float:
    """Historical Conditional VaR (Expected Shortfall) at *confidence* level.

    Mean of losses that exceed the VaR threshold (positive = loss magnitude).
    Formula: CVaR = -mean(r | r < -VaR)
    """
    if len(daily_rets) == 0:
        return float("nan")
    var = historical_var(daily_rets, confidence)
    tail = daily_rets[daily_rets < -var]
    if len(tail) == 0:
        return var  # degenerate: no observations in the tail
    return float(-tail.mean())
