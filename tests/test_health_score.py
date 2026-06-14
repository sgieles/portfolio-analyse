"""Tests for analytics/health_score.py."""

from __future__ import annotations

import math

import pytest

from analytics.health_score import (
    _score_concentration,
    _score_diversification,
    _score_drawdown,
    _score_sharpe,
    _score_volatility,
    portfolio_health_score,
)


# ── Component: Sharpe ─────────────────────────────────────────────────────────

def test_sharpe_perfect():
    assert _score_sharpe(2.0) == pytest.approx(20.0)


def test_sharpe_above_two_capped():
    assert _score_sharpe(3.0) == pytest.approx(20.0)


def test_sharpe_zero():
    assert _score_sharpe(0.0) == pytest.approx(0.0)


def test_sharpe_negative_is_zero():
    assert _score_sharpe(-1.0) == pytest.approx(0.0)


def test_sharpe_midpoint():
    assert _score_sharpe(1.0) == pytest.approx(10.0)


def test_sharpe_nan_is_zero():
    assert _score_sharpe(float("nan")) == pytest.approx(0.0)


# ── Component: Drawdown ───────────────────────────────────────────────────────

def test_drawdown_below_threshold():
    assert _score_drawdown(0.04) == pytest.approx(20.0)


def test_drawdown_above_worst():
    assert _score_drawdown(0.55) == pytest.approx(0.0)


def test_drawdown_at_worst():
    assert _score_drawdown(0.50) == pytest.approx(0.0)


def test_drawdown_at_best():
    assert _score_drawdown(0.05) == pytest.approx(20.0)


def test_drawdown_midpoint():
    # Linear between 0.05 (20pts) and 0.50 (0pts); midpoint 0.275 → 10pts
    assert _score_drawdown(0.275) == pytest.approx(10.0, abs=1e-9)


def test_drawdown_nan_is_zero():
    assert _score_drawdown(float("nan")) == pytest.approx(0.0)


# ── Component: Volatility ─────────────────────────────────────────────────────

def test_volatility_low():
    assert _score_volatility(0.08) == pytest.approx(20.0)


def test_volatility_high():
    assert _score_volatility(0.45) == pytest.approx(0.0)


def test_volatility_midpoint():
    # Linear between 0.10 (20pts) and 0.40 (0pts); midpoint 0.25 → 10pts
    assert _score_volatility(0.25) == pytest.approx(10.0, abs=1e-9)


def test_volatility_nan_is_zero():
    assert _score_volatility(float("nan")) == pytest.approx(0.0)


# ── Component: Diversification ────────────────────────────────────────────────

def test_div_full():
    assert _score_diversification(1.0) == pytest.approx(20.0)


def test_div_zero():
    assert _score_diversification(0.0) == pytest.approx(0.0)


def test_div_half():
    assert _score_diversification(0.5) == pytest.approx(10.0)


def test_div_nan_is_zero():
    assert _score_diversification(float("nan")) == pytest.approx(0.0)


def test_div_above_one_capped():
    assert _score_diversification(1.5) == pytest.approx(20.0)


# ── Component: Concentration ──────────────────────────────────────────────────

def test_concentration_well_spread():
    # max weight 0.2 (5 equal assets) → perfect
    w = {"A": 0.2, "B": 0.2, "C": 0.2, "D": 0.2, "E": 0.2}
    assert _score_concentration(w) == pytest.approx(20.0)


def test_concentration_single_asset():
    assert _score_concentration({"A": 1.0}) == pytest.approx(0.0)


def test_concentration_high_weight():
    # 80% in one asset → 0 pts
    assert _score_concentration({"A": 0.80, "B": 0.20}) == pytest.approx(0.0)


def test_concentration_midpoint():
    # Linear between 0.20 (20pts) and 0.80 (0pts); midpoint 0.50 → 10pts
    assert _score_concentration({"A": 0.5, "B": 0.5}) == pytest.approx(10.0, abs=1e-9)


def test_concentration_empty_is_zero():
    assert _score_concentration({}) == pytest.approx(0.0)


# ── Full score ────────────────────────────────────────────────────────────────

def test_perfect_portfolio_scores_100():
    score, _ = portfolio_health_score(
        sharpe=2.0,
        max_drawdown=0.04,
        volatility=0.08,
        diversification_score=1.0,
        weights={"A": 0.2, "B": 0.2, "C": 0.2, "D": 0.2, "E": 0.2},
    )
    assert score == pytest.approx(100.0)


def test_terrible_portfolio_scores_zero():
    score, _ = portfolio_health_score(
        sharpe=-1.0,
        max_drawdown=0.80,
        volatility=0.60,
        diversification_score=0.0,
        weights={"A": 1.0},
    )
    assert score == pytest.approx(0.0)


def test_score_between_zero_and_100():
    score, _ = portfolio_health_score(
        sharpe=0.8,
        max_drawdown=0.25,
        volatility=0.18,
        diversification_score=0.55,
        weights={"A": 0.6, "B": 0.4},
    )
    assert 0.0 <= score <= 100.0


def test_returns_five_components():
    _, components = portfolio_health_score(
        sharpe=1.0,
        max_drawdown=0.15,
        volatility=0.20,
        diversification_score=0.5,
        weights={"A": 0.5, "B": 0.5},
    )
    assert set(components.keys()) == {
        "sharpe", "drawdown", "volatility", "diversification", "concentration"
    }


def test_components_sum_to_total():
    score, components = portfolio_health_score(
        sharpe=1.2,
        max_drawdown=0.20,
        volatility=0.15,
        diversification_score=0.65,
        weights={"A": 0.4, "B": 0.35, "C": 0.25},
    )
    # total is rounded to 1 decimal; allow rounding error up to 0.1
    assert abs(sum(components.values()) - score) < 0.1


def test_nan_inputs_do_not_crash():
    score, _ = portfolio_health_score(
        sharpe=float("nan"),
        max_drawdown=float("nan"),
        volatility=float("nan"),
        diversification_score=float("nan"),
        weights={"A": 0.5, "B": 0.5},
    )
    assert score == pytest.approx(10.0)  # only concentration contributes
