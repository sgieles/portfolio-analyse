"""Monte Carlo simulation engine — pure functions, no Qt, no I/O.

Method: parametric GBM using historical mean and covariance of daily returns.
  - Correlated shocks via Cholesky decomposition of the covariance matrix.
  - Fully vectorised: generates all paths in a single NumPy call.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from utils.constants import GROWTH_START_VALUE, TRADING_DAYS_PER_YEAR


@dataclass
class MonteCarloResult:
    """Output of one Monte Carlo simulation run."""

    n_simulations: int
    horizon_years: int
    start_value: float

    # Percentile paths over time — shape (horizon_days,) each
    median_path: np.ndarray
    pct_5_path:  np.ndarray
    pct_95_path: np.ndarray

    # A sample of individual paths for the spaghetti plot — shape (n_sample, horizon_days)
    sample_paths: np.ndarray

    # Ending-value distribution — shape (n_simulations,)
    ending_values: np.ndarray

    # Summary statistics (from ending values)
    median: float
    mean: float
    pct_5: float
    pct_95: float
    prob_loss: float    # fraction of paths ending below start_value


def run_monte_carlo(
    daily_returns: pd.DataFrame,
    weights: dict[str, float],
    n_simulations: int = 1000,
    horizon_years: int = 5,
    start_value: float = GROWTH_START_VALUE,
    n_sample_paths: int = 200,
    seed: int | None = None,
) -> MonteCarloResult:
    """Simulate *n_simulations* portfolio paths over *horizon_years*.

    Args:
        daily_returns:  Daily return DataFrame (rows = dates, columns = tickers).
        weights:        Portfolio weights dict (must sum ≈ 1).
        n_simulations:  Number of Monte Carlo paths.
        horizon_years:  Simulation horizon in years (252 days/year).
        start_value:    Starting portfolio value.
        n_sample_paths: Number of individual paths stored for the spaghetti plot.
        seed:           Optional RNG seed for reproducibility.

    Returns:
        MonteCarloResult with paths and summary statistics.
    """
    tickers = [t for t in weights if t in daily_returns.columns]
    if not tickers:
        raise ValueError("No tickers with price data found in weights.")

    w = np.array([weights[t] for t in tickers], dtype=np.float64)
    rets = daily_returns[tickers].dropna()

    mu  = rets.mean().values                         # daily mean per asset
    cov = rets.cov(ddof=1).values                    # daily covariance matrix

    # Regularise to ensure positive-definiteness
    cov_reg = cov + np.eye(len(tickers)) * 1e-10

    try:
        L = np.linalg.cholesky(cov_reg)
    except np.linalg.LinAlgError:
        # Fallback: diagonal (uncorrelated) covariance
        L = np.diag(np.sqrt(np.diag(cov_reg)))

    horizon_days = int(horizon_years * TRADING_DAYS_PER_YEAR)
    rng = np.random.default_rng(seed)

    # Shape (n_simulations, horizon_days, n_assets)
    z = rng.standard_normal((n_simulations, horizon_days, len(tickers)))

    # Correlated daily returns: r_t = μ + L z_t
    asset_daily_rets = mu + z @ L.T                 # (N, H, A)

    # Portfolio daily returns
    port_daily_rets = asset_daily_rets @ w           # (N, H)

    # Compound growth paths
    growth  = np.cumprod(1.0 + port_daily_rets, axis=1)   # (N, H)
    paths   = start_value * growth                          # (N, H)

    ending_values = paths[:, -1]                            # (N,)

    # Percentile paths at every time step
    median_path = np.median(paths, axis=0)
    pct_5_path  = np.percentile(paths, 5,  axis=0)
    pct_95_path = np.percentile(paths, 95, axis=0)

    # Sample paths for the spaghetti plot
    n_sample = min(n_sample_paths, n_simulations)
    sample_paths = paths[:n_sample]

    return MonteCarloResult(
        n_simulations=n_simulations,
        horizon_years=horizon_years,
        start_value=start_value,
        median_path=median_path,
        pct_5_path=pct_5_path,
        pct_95_path=pct_95_path,
        sample_paths=sample_paths,
        ending_values=ending_values,
        median=float(np.median(ending_values)),
        mean=float(np.mean(ending_values)),
        pct_5=float(np.percentile(ending_values, 5)),
        pct_95=float(np.percentile(ending_values, 95)),
        prob_loss=float(np.mean(ending_values < start_value)),
    )
