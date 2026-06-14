"""Tests for analytics/monte_carlo.py."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from analytics.monte_carlo import MonteCarloResult, run_monte_carlo


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture()
def two_asset_returns():
    """250 days of synthetic daily returns for two assets."""
    rng = np.random.default_rng(0)
    n = 250
    dates = pd.bdate_range("2023-01-02", periods=n)
    return pd.DataFrame(
        {
            "A": rng.normal(0.0008, 0.012, n),
            "B": rng.normal(0.0006, 0.010, n),
        },
        index=dates,
    )


@pytest.fixture()
def equal_weights():
    return {"A": 0.5, "B": 0.5}


@pytest.fixture()
def single_asset_returns():
    rng = np.random.default_rng(1)
    n = 200
    dates = pd.bdate_range("2023-01-02", periods=n)
    return pd.DataFrame({"X": rng.normal(0.001, 0.01, n)}, index=dates)


# ── Return type ───────────────────────────────────────────────────────────────

def test_returns_montecarlo_result(two_asset_returns, equal_weights):
    result = run_monte_carlo(
        two_asset_returns, equal_weights, n_simulations=100, horizon_years=2, seed=1
    )
    assert isinstance(result, MonteCarloResult)


# ── Simulation dimensions ─────────────────────────────────────────────────────

def test_n_simulations_stored(two_asset_returns, equal_weights):
    result = run_monte_carlo(
        two_asset_returns, equal_weights, n_simulations=200, horizon_years=1, seed=2
    )
    assert result.n_simulations == 200


def test_horizon_stored(two_asset_returns, equal_weights):
    result = run_monte_carlo(
        two_asset_returns, equal_weights, n_simulations=100, horizon_years=3, seed=3
    )
    assert result.horizon_years == 3


def test_ending_values_shape(two_asset_returns, equal_weights):
    n_sims = 150
    result = run_monte_carlo(
        two_asset_returns, equal_weights, n_simulations=n_sims, horizon_years=1, seed=4
    )
    assert result.ending_values.shape == (n_sims,)


def test_median_path_length(two_asset_returns, equal_weights):
    result = run_monte_carlo(
        two_asset_returns, equal_weights, n_simulations=100, horizon_years=2, seed=5
    )
    expected_days = 2 * 252
    assert result.median_path.shape == (expected_days,)


def test_sample_paths_capped_at_200(two_asset_returns, equal_weights):
    result = run_monte_carlo(
        two_asset_returns, equal_weights, n_simulations=500, horizon_years=1, seed=6
    )
    assert result.sample_paths.shape[0] <= 200


def test_sample_paths_fewer_than_nsims_stored(two_asset_returns, equal_weights):
    result = run_monte_carlo(
        two_asset_returns, equal_weights, n_simulations=50, horizon_years=1,
        n_sample_paths=50, seed=7,
    )
    assert result.sample_paths.shape[0] == 50


# ── Statistical properties ────────────────────────────────────────────────────

def test_pct5_less_than_pct95(two_asset_returns, equal_weights):
    result = run_monte_carlo(
        two_asset_returns, equal_weights, n_simulations=500, horizon_years=3, seed=8
    )
    assert result.pct_5 < result.pct_95


def test_median_between_pct5_and_pct95(two_asset_returns, equal_weights):
    result = run_monte_carlo(
        two_asset_returns, equal_weights, n_simulations=500, horizon_years=3, seed=9
    )
    assert result.pct_5 <= result.median <= result.pct_95


def test_prob_loss_in_range(two_asset_returns, equal_weights):
    result = run_monte_carlo(
        two_asset_returns, equal_weights, n_simulations=300, horizon_years=2, seed=10
    )
    assert 0.0 <= result.prob_loss <= 1.0


def test_mean_near_median_symmetric_rets(two_asset_returns, equal_weights):
    """For moderate horizons with typical drift the mean and median should be close."""
    result = run_monte_carlo(
        two_asset_returns, equal_weights, n_simulations=1000, horizon_years=1, seed=11
    )
    # Median and mean should be within 50% of each other
    ratio = abs(result.mean - result.median) / max(abs(result.median), 1e-6)
    assert ratio < 0.50


# ── start_value ───────────────────────────────────────────────────────────────

def test_start_value_stored(two_asset_returns, equal_weights):
    sv = 25_000.0
    result = run_monte_carlo(
        two_asset_returns, equal_weights, n_simulations=100, horizon_years=1,
        start_value=sv, seed=12,
    )
    assert result.start_value == sv


def test_ending_values_scale_with_start(two_asset_returns, equal_weights):
    r1 = run_monte_carlo(
        two_asset_returns, equal_weights, n_simulations=200, horizon_years=2,
        start_value=10_000, seed=13,
    )
    r2 = run_monte_carlo(
        two_asset_returns, equal_weights, n_simulations=200, horizon_years=2,
        start_value=20_000, seed=13,
    )
    ratio = r2.ending_values / r1.ending_values
    assert np.allclose(ratio, 2.0, rtol=1e-10)


# ── Reproducibility ───────────────────────────────────────────────────────────

def test_same_seed_gives_same_result(two_asset_returns, equal_weights):
    kwargs = dict(n_simulations=200, horizon_years=2, seed=42)
    r1 = run_monte_carlo(two_asset_returns, equal_weights, **kwargs)
    r2 = run_monte_carlo(two_asset_returns, equal_weights, **kwargs)
    assert np.allclose(r1.ending_values, r2.ending_values)


def test_different_seeds_differ(two_asset_returns, equal_weights):
    r1 = run_monte_carlo(
        two_asset_returns, equal_weights, n_simulations=200, horizon_years=2, seed=1
    )
    r2 = run_monte_carlo(
        two_asset_returns, equal_weights, n_simulations=200, horizon_years=2, seed=2
    )
    assert not np.allclose(r1.ending_values, r2.ending_values)


# ── Single-asset portfolio ────────────────────────────────────────────────────

def test_single_asset_runs(single_asset_returns):
    result = run_monte_carlo(
        single_asset_returns, {"X": 1.0}, n_simulations=100, horizon_years=2, seed=5
    )
    assert isinstance(result, MonteCarloResult)
    assert result.ending_values.shape == (100,)


# ── Near-singular covariance fallback ────────────────────────────────────────

def test_identical_assets_no_error():
    """Perfectly correlated assets make cov near-singular; should not crash."""
    rng = np.random.default_rng(0)
    n = 200
    dates = pd.bdate_range("2023-01-02", periods=n)
    rets = rng.normal(0.001, 0.01, n)
    df = pd.DataFrame({"A": rets, "B": rets}, index=dates)
    result = run_monte_carlo(df, {"A": 0.5, "B": 0.5}, n_simulations=50, horizon_years=1, seed=0)
    assert isinstance(result, MonteCarloResult)
    assert np.all(np.isfinite(result.ending_values))
