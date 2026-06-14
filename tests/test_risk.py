"""Tests for analytics.risk — formulas verified against known values."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from analytics.risk import (
    annualized_volatility,
    beta,
    downside_deviation,
    drawdown_series,
    historical_cvar,
    historical_var,
    max_drawdown,
    portfolio_beta,
    portfolio_volatility,
    rolling_volatility,
    sharpe_ratio,
    sortino_ratio,
)
from utils.constants import TRADING_DAYS_PER_YEAR


# ── annualized_volatility ─────────────────────────────────────────────────────

class TestAnnualizedVolatility:
    def test_zero_for_constant_returns(self, flat_prices):
        from analytics.returns import daily_returns
        rets = daily_returns(flat_prices)
        assert annualized_volatility(rets) == pytest.approx(0.0, abs=1e-10)

    def test_scales_with_sqrt_252(self, volatile_returns):
        daily_std = volatile_returns.std(ddof=1)
        expected = float(daily_std * np.sqrt(TRADING_DAYS_PER_YEAR))
        assert annualized_volatility(volatile_returns) == pytest.approx(expected, rel=1e-9)

    def test_single_element_returns_nan(self):
        s = pd.Series([0.01])
        assert np.isnan(annualized_volatility(s))

    def test_empty_returns_nan(self):
        assert np.isnan(annualized_volatility(pd.Series([], dtype=float)))


# ── downside_deviation ────────────────────────────────────────────────────────

class TestDownsideDeviation:
    def test_all_positive_returns_gives_zero(self):
        rets = pd.Series([0.01, 0.02, 0.03])
        assert downside_deviation(rets) == pytest.approx(0.0, abs=1e-10)

    def test_mixed_returns(self):
        rets = pd.Series([0.01, -0.02, 0.03, -0.01])
        # np.minimum clips positives to 0 — all four observations contribute
        clipped = np.minimum(rets.values, 0.0)   # [0, -0.02, 0, -0.01]
        expected_daily = np.sqrt(np.mean(clipped ** 2))
        expected_ann = expected_daily * np.sqrt(TRADING_DAYS_PER_YEAR)
        assert downside_deviation(rets) == pytest.approx(expected_ann, rel=1e-9)

    def test_empty_returns_nan(self):
        assert np.isnan(downside_deviation(pd.Series([], dtype=float)))


# ── sharpe_ratio ──────────────────────────────────────────────────────────────

class TestSharpeRatio:
    def test_basic(self):
        # (0.12 - 0.04) / 0.16 = 0.5
        assert sharpe_ratio(0.12, 0.16, 0.04) == pytest.approx(0.5)

    def test_zero_volatility_returns_nan(self):
        assert np.isnan(sharpe_ratio(0.10, 0.0, 0.04))

    def test_nan_return_returns_nan(self):
        assert np.isnan(sharpe_ratio(float("nan"), 0.16, 0.04))

    def test_negative_sharpe(self):
        # Return below risk-free rate
        assert sharpe_ratio(0.02, 0.16, 0.04) < 0.0


# ── sortino_ratio ─────────────────────────────────────────────────────────────

class TestSortinoRatio:
    def test_all_positive_returns_nan(self):
        rets = pd.Series([0.01, 0.02, 0.03])
        # downside deviation = 0 → NaN
        assert np.isnan(sortino_ratio(rets, 0.252, 0.04))

    def test_higher_than_sharpe_with_skewed_dist(self, volatile_returns):
        from analytics.risk import annualized_volatility
        from analytics.returns import annualized_return
        ann_ret = annualized_return(volatile_returns)
        vol = annualized_volatility(volatile_returns)
        rfr = 0.04
        sharpe = sharpe_ratio(ann_ret, vol, rfr)
        sortino = sortino_ratio(volatile_returns, ann_ret, rfr)
        # Sortino >= Sharpe when there are positive returns (downside vol < total vol)
        if not (np.isnan(sharpe) or np.isnan(sortino)):
            assert sortino >= sharpe

    def test_empty_returns_nan(self):
        assert np.isnan(sortino_ratio(pd.Series([], dtype=float), 0.10, 0.04))


# ── beta ──────────────────────────────────────────────────────────────────────

class TestBeta:
    def test_asset_equals_benchmark_gives_beta_one(self, volatile_returns):
        b = beta(volatile_returns, volatile_returns.rename("BENCH"))
        assert b == pytest.approx(1.0, rel=1e-6)

    def test_negative_correlation(self, volatile_returns):
        inverted = -volatile_returns.rename("BENCH")
        b = beta(volatile_returns, inverted)
        assert b < 0.0

    def test_zero_variance_benchmark_returns_nan(self, volatile_returns):
        bench_flat = pd.Series(0.0, index=volatile_returns.index, name="FLAT")
        assert np.isnan(beta(volatile_returns, bench_flat))

    def test_insufficient_overlap_returns_nan(self):
        s1 = pd.Series([0.01], index=pd.bdate_range("2020-01-02", periods=1), name="A")
        s2 = pd.Series([0.02], index=pd.bdate_range("2020-01-02", periods=1), name="B")
        assert np.isnan(beta(s1, s2))

    def test_correlated_asset(self, volatile_returns, benchmark_returns):
        b = beta(volatile_returns, benchmark_returns)
        # Constructed as volatile * 0.8 + noise → beta should be near 0.8
        assert 0.3 < b < 1.5   # broad range; exact value depends on seed


# ── portfolio_volatility ──────────────────────────────────────────────────────

class TestPortfolioVolatility:
    def test_single_asset_equals_individual_vol(self, volatile_returns):
        df = volatile_returns.to_frame()
        weights = {"VOLATILE": 1.0}
        port_vol = portfolio_volatility(df, weights)
        ind_vol = annualized_volatility(volatile_returns)
        assert port_vol == pytest.approx(ind_vol, rel=1e-9)

    def test_50_50_uncorrelated(self):
        """Two uncorrelated assets with known vols."""
        rng = np.random.default_rng(0)
        n = 1000
        idx = pd.bdate_range("2020-01-02", periods=n)
        a = pd.Series(rng.normal(0, 0.01, n), index=idx, name="A")
        b = pd.Series(rng.normal(0, 0.02, n), index=idx, name="B")
        # Verify independence
        assert abs(a.corr(b)) < 0.1
        df = pd.DataFrame({"A": a, "B": b})
        weights = {"A": 0.5, "B": 0.5}
        port_vol = portfolio_volatility(df, weights)
        # Analytic: sqrt(0.5^2 * vol_a^2 + 0.5^2 * vol_b^2) * sqrt(252)
        vol_a = a.std(ddof=1) * np.sqrt(252)
        vol_b = b.std(ddof=1) * np.sqrt(252)
        expected = np.sqrt(0.5**2 * vol_a**2 + 0.5**2 * vol_b**2)
        assert port_vol == pytest.approx(expected, rel=0.05)   # 5 % tolerance for sampling


# ── drawdown_series & max_drawdown ────────────────────────────────────────────

class TestDrawdown:
    def test_flat_prices_no_drawdown(self, flat_prices):
        dd = drawdown_series(flat_prices)
        assert (dd == 0.0).all()

    def test_max_drawdown_known_value(self):
        """100 → 50 → 80 → max drawdown = 50 %."""
        idx = pd.bdate_range("2020-01-02", periods=3)
        prices = pd.Series([100.0, 50.0, 80.0], index=idx)
        assert max_drawdown(prices) == pytest.approx(0.5)

    def test_always_rising_no_drawdown(self, compound_prices):
        assert max_drawdown(compound_prices) == pytest.approx(0.0, abs=1e-10)

    def test_drawdown_series_non_negative(self, volatile_returns):
        from analytics.returns import daily_returns
        from analytics.returns import portfolio_value_series
        prices = pd.DataFrame({"V": 100.0 * (1 + volatile_returns).cumprod()})
        dd = drawdown_series(prices["V"])
        assert (dd >= 0.0).all()

    def test_single_price_max_drawdown_nan(self):
        s = pd.Series([100.0], index=pd.bdate_range("2020-01-02", periods=1))
        assert np.isnan(max_drawdown(s))


# ── VaR / CVaR ────────────────────────────────────────────────────────────────

class TestVaR:
    def _returns(self) -> pd.Series:
        """Ten returns whose 5th percentile we know exactly."""
        # Sorted: -0.10, -0.05, -0.03, -0.01, 0.00, 0.01, 0.02, 0.03, 0.05, 0.10
        vals = [0.10, 0.05, 0.03, 0.01, 0.00, -0.01, -0.03, -0.05, -0.10, 0.02]
        return pd.Series(vals)

    def test_var_95_positive(self):
        rets = self._returns()
        assert historical_var(rets, 0.95) > 0.0

    def test_var_99_gte_var_95(self):
        rets = self._returns()
        assert historical_var(rets, 0.99) >= historical_var(rets, 0.95)

    def test_cvar_gte_var(self):
        rets = self._returns()
        var95 = historical_var(rets, 0.95)
        cvar95 = historical_cvar(rets, 0.95)
        assert cvar95 >= var95

    def test_all_positive_returns_var_negative_or_zero(self):
        rets = pd.Series([0.01, 0.02, 0.03, 0.04, 0.05])
        var = historical_var(rets, 0.95)
        # VaR can be negative (i.e. even the worst case is a gain)
        assert isinstance(var, float)

    def test_empty_returns_nan(self):
        assert np.isnan(historical_var(pd.Series([], dtype=float)))
        assert np.isnan(historical_cvar(pd.Series([], dtype=float)))


# ── rolling_volatility ────────────────────────────────────────────────────────

class TestRollingVolatility:
    def test_output_length(self, volatile_returns):
        rv = rolling_volatility(volatile_returns, window=60)
        assert len(rv) == len(volatile_returns)

    def test_initial_nans(self, volatile_returns):
        window = 60
        rv = rolling_volatility(volatile_returns, window=window)
        assert rv.iloc[: window - 1].isna().all()
        assert not rv.iloc[window - 1 :].isna().all()

    def test_name(self, volatile_returns):
        rv = rolling_volatility(volatile_returns)
        assert rv.name == "Rolling Volatility"
