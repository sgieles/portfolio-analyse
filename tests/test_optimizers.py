"""Tests for optimization.optimizers and optimization.efficient_frontier.

All tests use synthetic price data — no live network calls.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from models.results import OptimizationResult
from models.settings import AnalysisSettings, ExpectedReturnMethod
from optimization.optimizers import (
    _build_expected_returns,
    black_litterman,
    max_sharpe,
    min_variance,
)
from optimization.efficient_frontier import sample_frontier, build_frontier_data

WEIGHT_TOL = 1e-4   # weights may not sum to exactly 1.0 after clean_weights()


# ── Synthetic data ────────────────────────────────────────────────────────────

def _make_prices(n: int = 600, seed: int = 42) -> pd.DataFrame:
    """Three-asset synthetic price DataFrame with 600 business days."""
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range("2018-01-02", periods=n)
    # Different expected returns and vols so optimizers get a real problem
    a = 100.0 * np.exp(np.cumsum(rng.normal(0.0006, 0.010, n)))
    b = 100.0 * np.exp(np.cumsum(rng.normal(0.0003, 0.006, n)))
    c = 100.0 * np.exp(np.cumsum(rng.normal(0.0009, 0.015, n)))
    return pd.DataFrame({"A": a, "B": b, "C": c}, index=idx)


def _make_benchmark(n: int = 600, seed: int = 7) -> pd.Series:
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range("2018-01-02", periods=n)
    prices = 100.0 * np.exp(np.cumsum(rng.normal(0.0005, 0.010, n)))
    return pd.Series(prices, index=idx, name="BENCH")


@pytest.fixture
def prices() -> pd.DataFrame:
    return _make_prices()


@pytest.fixture
def benchmark() -> pd.Series:
    return _make_benchmark()


@pytest.fixture
def settings() -> AnalysisSettings:
    return AnalysisSettings()


# ── _build_expected_returns ───────────────────────────────────────────────────

class TestBuildExpectedReturns:
    def test_historical_avg_returns_series(self, prices, settings):
        mu = _build_expected_returns(prices, settings)
        assert isinstance(mu, pd.Series)
        assert set(mu.index) == {"A", "B", "C"}

    def test_cagr_method(self, prices):
        s = AnalysisSettings(expected_return_method=ExpectedReturnMethod.CAGR)
        mu = _build_expected_returns(prices, s)
        assert set(mu.index) == {"A", "B", "C"}
        # CAGR depends on the actual price path; just verify output is finite
        assert not mu.isna().all()

    def test_capm_fallback_without_benchmark(self, prices, capsys):
        s = AnalysisSettings(expected_return_method=ExpectedReturnMethod.CAPM)
        mu = _build_expected_returns(prices, s, benchmark_prices=None)
        # Falls back to historical avg — should still return valid Series
        assert isinstance(mu, pd.Series)
        assert not mu.isna().all()

    def test_capm_with_benchmark(self, prices, benchmark):
        s = AnalysisSettings(expected_return_method=ExpectedReturnMethod.CAPM)
        mu = _build_expected_returns(prices, s, benchmark_prices=benchmark)
        assert isinstance(mu, pd.Series)
        assert len(mu) == 3


# ── max_sharpe ────────────────────────────────────────────────────────────────

class TestMaxSharpe:
    def test_returns_optimization_result(self, prices, settings):
        result = max_sharpe(prices, settings)
        assert isinstance(result, OptimizationResult)
        assert result.method == "max_sharpe"

    def test_weights_sum_to_one(self, prices, settings):
        result = max_sharpe(prices, settings)
        assert sum(result.weights.values()) == pytest.approx(1.0, abs=WEIGHT_TOL)

    def test_weights_non_negative(self, prices, settings):
        result = max_sharpe(prices, settings)
        for w in result.weights.values():
            assert w >= -WEIGHT_TOL

    def test_all_tickers_present(self, prices, settings):
        result = max_sharpe(prices, settings)
        assert set(result.weights.keys()) == {"A", "B", "C"}

    def test_metrics_are_finite(self, prices, settings):
        result = max_sharpe(prices, settings)
        assert np.isfinite(result.expected_return)
        assert np.isfinite(result.volatility)
        assert np.isfinite(result.sharpe)

    def test_with_benchmark(self, prices, settings, benchmark):
        result = max_sharpe(prices, settings, benchmark_prices=benchmark)
        assert np.isfinite(result.beta)

    def test_sharpe_positive_for_good_data(self, prices, settings):
        result = max_sharpe(prices, settings)
        # With upward-trending synthetic data, Sharpe should be > 0
        assert result.sharpe > 0.0

    def test_cagr_method(self, prices):
        s = AnalysisSettings(expected_return_method=ExpectedReturnMethod.CAGR)
        result = max_sharpe(prices, s)
        assert sum(result.weights.values()) == pytest.approx(1.0, abs=WEIGHT_TOL)


# ── min_variance ──────────────────────────────────────────────────────────────

class TestMinVariance:
    def test_returns_optimization_result(self, prices, settings):
        result = min_variance(prices, settings)
        assert isinstance(result, OptimizationResult)
        assert result.method == "min_variance"

    def test_weights_sum_to_one(self, prices, settings):
        result = min_variance(prices, settings)
        assert sum(result.weights.values()) == pytest.approx(1.0, abs=WEIGHT_TOL)

    def test_weights_non_negative(self, prices, settings):
        result = min_variance(prices, settings)
        for w in result.weights.values():
            assert w >= -WEIGHT_TOL

    def test_lower_vol_than_equal_weight(self, prices, settings):
        """Min-variance portfolio should have lower volatility than equal-weighted."""
        from analytics.returns import daily_returns
        from analytics.risk import portfolio_volatility

        result = min_variance(prices, settings)
        eq_weights = {"A": 1 / 3, "B": 1 / 3, "C": 1 / 3}
        rets = daily_returns(prices)
        mv_vol = portfolio_volatility(rets, result.weights)
        eq_vol = portfolio_volatility(rets, eq_weights)
        assert mv_vol <= eq_vol + 1e-6   # allow tiny numeric slack

    def test_metrics_are_finite(self, prices, settings):
        result = min_variance(prices, settings)
        assert np.isfinite(result.volatility)


# ── black_litterman ───────────────────────────────────────────────────────────

class TestBlackLitterman:
    def test_returns_optimization_result(self, prices, settings):
        result = black_litterman(prices, settings)
        assert isinstance(result, OptimizationResult)
        assert result.method == "black_litterman"

    def test_weights_sum_to_one(self, prices, settings):
        result = black_litterman(prices, settings)
        assert sum(result.weights.values()) == pytest.approx(1.0, abs=WEIGHT_TOL)

    def test_weights_non_negative(self, prices, settings):
        result = black_litterman(prices, settings)
        for w in result.weights.values():
            assert w >= -WEIGHT_TOL

    def test_metrics_are_finite(self, prices, settings):
        result = black_litterman(prices, settings)
        assert np.isfinite(result.expected_return)
        assert np.isfinite(result.volatility)

    def test_different_weights_from_max_sharpe(self, prices, settings):
        """BL (equilibrium prior) should produce weights different from Max Sharpe."""
        ms = max_sharpe(prices, settings)
        bl = black_litterman(prices, settings)
        # At least one asset should have a different weight
        diffs = [abs(bl.weights[t] - ms.weights[t]) for t in bl.weights]
        assert max(diffs) > 1e-6


# ── sample_frontier ───────────────────────────────────────────────────────────

class TestSampleFrontier:
    def test_returns_two_lists(self, prices, settings):
        risks, returns = sample_frontier(prices, settings, n_points=10)
        assert isinstance(risks, list)
        assert isinstance(returns, list)

    def test_same_length(self, prices, settings):
        risks, returns = sample_frontier(prices, settings, n_points=10)
        assert len(risks) == len(returns)

    def test_non_empty(self, prices, settings):
        risks, returns = sample_frontier(prices, settings, n_points=10)
        assert len(risks) > 0

    def test_risks_positive(self, prices, settings):
        risks, _ = sample_frontier(prices, settings, n_points=10)
        for r in risks:
            assert r > 0.0

    def test_frontier_is_upward_sloping(self, prices, settings):
        """Higher return should correspond to equal or higher risk on the frontier."""
        risks, returns = sample_frontier(prices, settings, n_points=20)
        if len(risks) < 3:
            pytest.skip("Too few frontier points sampled")
        # Sort by return and check risks are non-decreasing (allow small violations)
        pairs = sorted(zip(returns, risks))
        sorted_returns = [p[0] for p in pairs]
        sorted_risks = [p[1] for p in pairs]
        violations = sum(
            sorted_risks[i] > sorted_risks[i + 1] + 0.01
            for i in range(len(sorted_risks) - 1)
        )
        assert violations <= len(risks) // 5   # at most 20 % violations (numerical noise)


# ── build_frontier_data ───────────────────────────────────────────────────────

class TestBuildFrontierData:
    def test_returns_frontier_data(self, prices, settings):
        from optimization.efficient_frontier import FrontierData
        current_weights = {"A": 1 / 3, "B": 1 / 3, "C": 1 / 3}
        fd = build_frontier_data(prices, current_weights, settings, n_points=10)
        assert isinstance(fd, FrontierData)

    def test_all_four_portfolios_present(self, prices, settings):
        current_weights = {"A": 0.5, "B": 0.3, "C": 0.2}
        fd = build_frontier_data(prices, current_weights, settings, n_points=10)
        assert fd.current.method == "current"
        assert fd.max_sharpe_result.method == "max_sharpe"
        assert fd.min_variance_result.method == "min_variance"
        assert fd.black_litterman_result.method == "black_litterman"

    def test_frontier_curve_populated(self, prices, settings):
        current_weights = {"A": 1 / 3, "B": 1 / 3, "C": 1 / 3}
        fd = build_frontier_data(prices, current_weights, settings, n_points=10)
        assert len(fd.frontier_risks) > 0
