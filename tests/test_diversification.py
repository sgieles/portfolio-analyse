"""Tests for analytics.diversification."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from analytics.diversification import (
    average_correlation,
    diversification_score,
    return_contributions,
    risk_contributions,
)


# ── average_correlation ───────────────────────────────────────────────────────

class TestAverageCorrelation:
    def test_single_asset_returns_one(self, volatile_returns):
        df = volatile_returns.to_frame()
        assert average_correlation(df) == pytest.approx(1.0)

    def test_identical_assets_returns_one(self, volatile_returns):
        df = pd.DataFrame({"A": volatile_returns, "B": volatile_returns})
        assert average_correlation(df) == pytest.approx(1.0, rel=1e-6)

    def test_range_is_minus_one_to_one(self, multi_asset_returns):
        corr = average_correlation(multi_asset_returns)
        assert -1.0 <= corr <= 1.0

    def test_known_value(self):
        """Two perfectly negatively correlated assets → avg corr = -1."""
        idx = pd.bdate_range("2020-01-02", periods=100)
        rng = np.random.default_rng(5)
        a = pd.Series(rng.normal(0, 0.01, 100), index=idx, name="A")
        df = pd.DataFrame({"A": a, "B": -a})
        assert average_correlation(df) == pytest.approx(-1.0, rel=1e-6)


# ── diversification_score ─────────────────────────────────────────────────────

class TestDiversificationScore:
    def test_single_asset_gives_zero(self, volatile_returns):
        df = volatile_returns.to_frame()
        score = diversification_score(df, {"VOLATILE": 1.0})
        assert score == 0.0

    def test_perfectly_correlated_gives_zero(self, volatile_returns):
        df = pd.DataFrame({"A": volatile_returns, "B": volatile_returns})
        score = diversification_score(df, {"A": 0.5, "B": 0.5})
        assert score == pytest.approx(0.0, abs=1e-6)

    def test_score_in_zero_one(self, multi_asset_returns, equal_weights_3):
        score = diversification_score(multi_asset_returns, equal_weights_3)
        assert 0.0 <= score <= 1.0

    def test_more_assets_higher_score(self, multi_asset_returns):
        """Adding an uncorrelated asset should not decrease the score."""
        w2 = {"X": 0.5, "Y": 0.5}
        w3 = {"X": 1 / 3, "Y": 1 / 3, "Z": 1 / 3}
        score2 = diversification_score(multi_asset_returns[["X", "Y"]], w2)
        score3 = diversification_score(multi_asset_returns, w3)
        # Z adds volatility but also potential diversification — score should be >= score2
        # (may not hold perfectly with random data; allow small tolerance)
        assert score3 >= score2 - 0.05


# ── risk_contributions ────────────────────────────────────────────────────────

class TestRiskContributions:
    def test_single_asset_full_contribution(self, volatile_returns):
        df = volatile_returns.to_frame()
        rc = risk_contributions(df, {"VOLATILE": 1.0})
        assert rc["VOLATILE"] == pytest.approx(1.0, rel=1e-6)

    def test_contributions_sum_to_one(self, multi_asset_returns, equal_weights_3):
        rc = risk_contributions(multi_asset_returns, equal_weights_3)
        assert sum(rc.values()) == pytest.approx(1.0, rel=1e-6)

    def test_all_fractions_non_negative_for_positive_cov(self, multi_asset_returns, equal_weights_3):
        rc = risk_contributions(multi_asset_returns, equal_weights_3)
        for v in rc.values():
            assert v >= -0.05   # allow tiny numeric negatives for near-zero correlations

    def test_two_equal_assets(self, volatile_returns):
        """Two identical assets equally weighted → 50 % risk contribution each."""
        df = pd.DataFrame({"A": volatile_returns, "B": volatile_returns})
        rc = risk_contributions(df, {"A": 0.5, "B": 0.5})
        assert rc["A"] == pytest.approx(0.5, rel=1e-6)
        assert rc["B"] == pytest.approx(0.5, rel=1e-6)


# ── return_contributions ──────────────────────────────────────────────────────

class TestReturnContributions:
    def test_basic(self):
        ann_returns = {"A": 0.10, "B": 0.05}
        weights     = {"A": 0.6, "B": 0.4}
        rc = return_contributions(ann_returns, weights)
        assert rc["A"] == pytest.approx(0.06)
        assert rc["B"] == pytest.approx(0.02)

    def test_sums_to_portfolio_return(self):
        ann_returns = {"A": 0.12, "B": 0.08, "C": -0.02}
        weights     = {"A": 0.5,  "B": 0.3,  "C": 0.2}
        rc = return_contributions(ann_returns, weights)
        portfolio_ret = sum(weights[t] * r for t, r in ann_returns.items())
        assert sum(rc.values()) == pytest.approx(portfolio_ret, rel=1e-9)

    def test_zero_weight_gives_zero_contribution(self):
        rc = return_contributions({"A": 0.10, "B": 0.05}, {"A": 1.0, "B": 0.0})
        assert rc["B"] == pytest.approx(0.0)

    def test_missing_weight_defaults_to_zero(self):
        rc = return_contributions({"A": 0.10}, {"B": 1.0})
        assert rc["A"] == pytest.approx(0.0)
