"""Tests for analytics.returns — all formulas verified against known values."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from analytics.returns import (
    annualized_return,
    benchmark_value_series,
    capm_expected_return,
    cagr,
    daily_returns,
    portfolio_daily_returns,
    portfolio_value_series,
)
from utils.constants import TRADING_DAYS_PER_YEAR


# ── daily_returns ─────────────────────────────────────────────────────────────

class TestDailyReturns:
    def test_constant_price_gives_zero_returns(self, flat_prices):
        rets = daily_returns(flat_prices)
        assert (rets == 0.0).all()
        assert len(rets) == len(flat_prices) - 1

    def test_first_nan_dropped(self, compound_prices):
        rets = daily_returns(compound_prices)
        assert not rets.isna().any()
        assert len(rets) == len(compound_prices) - 1

    def test_constant_daily_return_value(self, compound_prices):
        rets = daily_returns(compound_prices)
        # compound_prices has 0.1 % daily return → all returns ≈ 0.001
        assert rets.values == pytest.approx(0.001, rel=1e-6)

    def test_dataframe_input(self, two_asset_prices):
        rets = daily_returns(two_asset_prices)
        assert isinstance(rets, pd.DataFrame)
        assert list(rets.columns) == ["A", "B"]


# ── cagr ──────────────────────────────────────────────────────────────────────

class TestCAGR:
    def test_one_year_exact(self):
        """Prices that double in exactly 252 trading days → CAGR = 100 %."""
        idx = pd.bdate_range("2020-01-02", periods=253)
        # 252 steps to go from 100 → 200
        prices = pd.Series(np.linspace(100.0, 200.0, 253), index=idx)
        result = cagr(prices)
        assert result == pytest.approx(1.0, rel=0.01)

    def test_constant_prices_returns_zero(self, flat_prices):
        result = cagr(flat_prices)
        assert result == pytest.approx(0.0, abs=1e-10)

    def test_compound_prices(self, compound_prices):
        # 0.1 % daily for 252 returns → CAGR = 1.001^252 - 1
        expected = 1.001 ** 252 - 1
        assert cagr(compound_prices) == pytest.approx(expected, rel=1e-4)

    def test_single_price_returns_nan(self):
        s = pd.Series([100.0], index=pd.bdate_range("2020-01-02", periods=1))
        assert np.isnan(cagr(s))

    def test_negative_end_price_returns_nan(self):
        """Positive start, negative end → ratio < 0 → can't take power → NaN."""
        idx = pd.bdate_range("2020-01-02", periods=3)
        s = pd.Series([100.0, 50.0, -25.0], index=idx)
        assert np.isnan(cagr(s))


# ── annualized_return ─────────────────────────────────────────────────────────

class TestAnnualizedReturn:
    def test_compound_daily_returns(self, compound_prices):
        rets = daily_returns(compound_prices)
        result = annualized_return(rets)
        # 0.001 × 252 = 0.252
        assert result == pytest.approx(0.001 * TRADING_DAYS_PER_YEAR, rel=1e-6)

    def test_zero_daily_return(self, flat_prices):
        rets = daily_returns(flat_prices)
        assert annualized_return(rets) == pytest.approx(0.0, abs=1e-10)

    def test_empty_series_returns_nan(self):
        assert np.isnan(annualized_return(pd.Series([], dtype=float)))


# ── capm_expected_return ──────────────────────────────────────────────────────

class TestCAPM:
    def test_zero_beta(self):
        # If β = 0, expected return = risk-free rate
        assert capm_expected_return(0.0, 0.04, 0.10) == pytest.approx(0.04)

    def test_beta_one(self):
        # If β = 1, expected return = market return
        assert capm_expected_return(1.0, 0.04, 0.10) == pytest.approx(0.10)

    def test_arbitrary_beta(self):
        # R_f=0.03, Mkt=0.09, β=1.5 → 0.03 + 1.5*(0.09-0.03) = 0.03+0.09 = 0.12
        assert capm_expected_return(1.5, 0.03, 0.09) == pytest.approx(0.12)

    def test_high_beta_amplifies_premium(self):
        # β=2 doubles the market premium
        result = capm_expected_return(2.0, 0.02, 0.08)
        assert result == pytest.approx(0.02 + 2.0 * 0.06)


# ── portfolio_daily_returns ───────────────────────────────────────────────────

class TestPortfolioDailyReturns:
    def test_single_asset_equal_to_individual(self, compound_prices):
        prices_df = compound_prices.to_frame()
        rets_individual = daily_returns(compound_prices)
        rets_portfolio = portfolio_daily_returns(prices_df, {"COMPOUND": 1.0})
        pd.testing.assert_series_equal(
            rets_portfolio.rename("COMPOUND"),
            rets_individual,
            check_names=False,
            atol=1e-12,
        )

    def test_50_50_is_arithmetic_mean(self, two_asset_prices):
        rets = portfolio_daily_returns(two_asset_prices, {"A": 0.5, "B": 0.5})
        rets_a = daily_returns(two_asset_prices["A"])
        rets_b = daily_returns(two_asset_prices["B"])
        expected = 0.5 * rets_a + 0.5 * rets_b
        pd.testing.assert_series_equal(rets, expected.rename("Portfolio"), atol=1e-12)

    def test_named_portfolio(self, two_asset_prices):
        rets = portfolio_daily_returns(two_asset_prices, {"A": 0.6, "B": 0.4})
        assert rets.name == "Portfolio"

    def test_zero_weight_asset_ignored(self, two_asset_prices):
        rets_full = portfolio_daily_returns(two_asset_prices, {"A": 1.0, "B": 0.0})
        rets_a    = daily_returns(two_asset_prices["A"])
        pd.testing.assert_series_equal(rets_full, rets_a.rename("Portfolio"), atol=1e-12)


# ── portfolio_value_series ────────────────────────────────────────────────────

class TestPortfolioValueSeries:
    def test_starts_at_start_value(self, two_asset_prices):
        v = portfolio_value_series(two_asset_prices, {"A": 0.5, "B": 0.5}, start_value=10_000)
        assert v.iloc[0] == pytest.approx(10_000.0)

    def test_length_is_prices_length(self, two_asset_prices):
        v = portfolio_value_series(two_asset_prices, {"A": 0.5, "B": 0.5})
        # prepended start row → len(prices) rows total
        assert len(v) == len(two_asset_prices)

    def test_flat_prices_stays_at_start(self, flat_prices):
        df = flat_prices.to_frame()
        v = portfolio_value_series(df, {"FLAT": 1.0}, start_value=10_000)
        assert v.values == pytest.approx(10_000.0, rel=1e-9)


# ── benchmark_value_series ────────────────────────────────────────────────────

class TestBenchmarkValueSeries:
    def test_starts_at_start_value(self, compound_prices):
        v = benchmark_value_series(compound_prices, start_value=10_000)
        assert v.iloc[0] == pytest.approx(10_000.0)

    def test_flat_stays_flat(self, flat_prices):
        v = benchmark_value_series(flat_prices, start_value=10_000)
        assert v.values == pytest.approx(10_000.0, rel=1e-9)
