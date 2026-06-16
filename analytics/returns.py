"""Return analytics — pure functions on pandas Series/DataFrames.

No Qt, no I/O. All formulas follow the domain conventions in CLAUDE.md:
  - Daily returns from Adjusted Close (pct_change)
  - Annualise with 252 trading days
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from utils.constants import TRADING_DAYS_PER_YEAR, GROWTH_START_VALUE


# ── Daily returns ────────────────────────────────────────────────────────────

def daily_returns(prices: pd.Series | pd.DataFrame) -> pd.Series | pd.DataFrame:
    """Percentage daily returns.

    Formula: r_t = (P_t / P_{t-1}) - 1
    First row (NaN) is dropped.
    """
    return prices.pct_change().dropna()


# ── Single-asset return metrics ──────────────────────────────────────────────

def cagr(prices: pd.Series, trading_days: int = TRADING_DAYS_PER_YEAR) -> float:
    """Compound Annual Growth Rate.

    Formula: CAGR = (P_end / P_start)^(trading_days / n_price_days) - 1
    where n_price_days = len(prices) - 1 (number of return observations).
    """
    if len(prices) < 2:
        return float("nan")
    n_days = len(prices) - 1
    years = n_days / trading_days
    if years <= 0:
        return float("nan")
    ratio = prices.iloc[-1] / prices.iloc[0]
    if ratio <= 0:
        return float("nan")
    return float(ratio ** (1.0 / years) - 1.0)


def annualized_return(daily_rets: pd.Series, trading_days: int = TRADING_DAYS_PER_YEAR) -> float:
    """Annualized arithmetic return from daily mean.

    Formula: ann_return = mean(r_daily) × trading_days
    """
    if len(daily_rets) == 0:
        return float("nan")
    return float(daily_rets.mean() * trading_days)


def capm_expected_return(
    beta: float,
    risk_free_rate: float,
    market_return: float,
) -> float:
    """CAPM expected return.

    Formula: E[R] = R_f + β × (E[R_m] - R_f)
    """
    return float(risk_free_rate + beta * (market_return - risk_free_rate))


# ── Portfolio-level return series ────────────────────────────────────────────

def _weights_array(prices_or_returns: pd.DataFrame, weights: dict[str, float]) -> np.ndarray:
    """Weight vector aligned to DataFrame column order."""
    return np.array([weights.get(col, 0.0) for col in prices_or_returns.columns])


def portfolio_daily_returns(
    prices: pd.DataFrame,
    weights: dict[str, float],
) -> pd.Series:
    """Weighted daily portfolio return series.

    Formula: r_p,t = Σ_i w_i × r_i,t
    """
    rets = daily_returns(prices)
    w = _weights_array(rets, weights)
    port_rets = rets @ w
    port_rets.name = "Portfolio"
    return port_rets


def portfolio_value_series(
    prices: pd.DataFrame,
    weights: dict[str, float],
    start_value: float = GROWTH_START_VALUE,
) -> pd.Series:
    """Portfolio value series starting at *start_value* (e.g. €10 000).

    Formula: V_t = start_value × ∏_{s=1}^{t} (1 + r_p,s)
    The starting date row is prepended at *start_value*.
    """
    port_rets = portfolio_daily_returns(prices, weights)
    cum = (1.0 + port_rets).cumprod()
    value = start_value * cum
    # Use the same index type as value to avoid timezone-mismatch ValueError
    # (newer yfinance may return tz-aware DatetimeIndex for some exchanges)
    first_idx = value.index[:0].append(pd.DatetimeIndex([prices.index[0]]))[:1]
    first_row = pd.Series([start_value], index=first_idx, name="Portfolio")
    return pd.concat([first_row, value])


def benchmark_value_series(
    benchmark_prices: pd.Series,
    start_value: float = GROWTH_START_VALUE,
) -> pd.Series:
    """Benchmark value series starting at *start_value*.

    Formula: same compound growth as portfolio_value_series but for a single series.
    """
    rets = benchmark_prices.pct_change().dropna()
    cum = (1.0 + rets).cumprod()
    value = start_value * cum
    name = benchmark_prices.name or "Benchmark"
    first_idx = value.index[:0].append(pd.DatetimeIndex([benchmark_prices.index[0]]))[:1]
    first_row = pd.Series([start_value], index=first_idx, name=name)
    return pd.concat([first_row, value])
