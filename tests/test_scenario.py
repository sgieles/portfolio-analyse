"""Tests for analytics/scenario.py."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from analytics.scenario import (
    DEFAULT_SCENARIOS,
    ScenarioResult,
    run_scenario_analysis,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture()
def two_asset_returns():
    """250 days of synthetic daily returns for AAPL and MSFT."""
    rng = np.random.default_rng(42)
    n = 250
    dates = pd.bdate_range("2023-01-02", periods=n)
    data = {
        "AAPL": rng.normal(0.001, 0.015, n),
        "MSFT": rng.normal(0.0008, 0.013, n),
    }
    return pd.DataFrame(data, index=dates)


@pytest.fixture()
def bench_returns(two_asset_returns):
    """Benchmark daily returns aligned to the asset returns."""
    rng = np.random.default_rng(99)
    return pd.Series(
        rng.normal(0.0005, 0.012, len(two_asset_returns)),
        index=two_asset_returns.index,
        name="SPY",
    )


@pytest.fixture()
def equal_weights():
    return {"AAPL": 0.5, "MSFT": 0.5}


@pytest.fixture()
def single_asset_returns():
    rng = np.random.default_rng(7)
    n = 200
    dates = pd.bdate_range("2023-01-02", periods=n)
    return pd.DataFrame({"ONLY": rng.normal(0.001, 0.01, n)}, index=dates)


@pytest.fixture()
def single_bench(single_asset_returns):
    rng = np.random.default_rng(77)
    return pd.Series(
        rng.normal(0.0005, 0.01, len(single_asset_returns)),
        index=single_asset_returns.index,
    )


# ── Default scenarios structure ───────────────────────────────────────────────

def test_default_scenarios_has_four_entries():
    assert len(DEFAULT_SCENARIOS) == 4


def test_default_scenarios_covers_bull_and_crash():
    keys = set(DEFAULT_SCENARIOS.keys())
    assert "Bull Market" in keys
    assert "Severe Crash" in keys


def test_default_bull_positive():
    assert DEFAULT_SCENARIOS["Bull Market"] > 0


def test_default_crash_very_negative():
    assert DEFAULT_SCENARIOS["Severe Crash"] < -0.30


# ── run_scenario_analysis: return types ───────────────────────────────────────

def test_returns_list_of_scenario_results(
    two_asset_returns, equal_weights, bench_returns
):
    results = run_scenario_analysis(two_asset_returns, equal_weights, bench_returns)
    assert isinstance(results, list)
    assert all(isinstance(r, ScenarioResult) for r in results)


def test_one_result_per_default_scenario(
    two_asset_returns, equal_weights, bench_returns
):
    results = run_scenario_analysis(two_asset_returns, equal_weights, bench_returns)
    assert len(results) == len(DEFAULT_SCENARIOS)


# ── Directional correctness ───────────────────────────────────────────────────

def test_bull_market_portfolio_return_positive(
    two_asset_returns, equal_weights, bench_returns
):
    results = run_scenario_analysis(two_asset_returns, equal_weights, bench_returns)
    bull = next(r for r in results if r.name == "Bull Market")
    assert bull.portfolio_return > 0


def test_severe_crash_portfolio_return_negative(
    two_asset_returns, equal_weights, bench_returns
):
    results = run_scenario_analysis(two_asset_returns, equal_weights, bench_returns)
    crash = next(r for r in results if r.name == "Severe Crash")
    assert crash.portfolio_return < 0


def test_new_value_higher_in_bull_than_crash(
    two_asset_returns, equal_weights, bench_returns
):
    results = run_scenario_analysis(two_asset_returns, equal_weights, bench_returns)
    bull  = next(r for r in results if r.name == "Bull Market")
    crash = next(r for r in results if r.name == "Severe Crash")
    assert bull.new_value > crash.new_value


# ── new_value uses start_value ─────────────────────────────────────────────────

def test_new_value_derived_from_start_value(
    two_asset_returns, equal_weights, bench_returns
):
    sv = 50_000.0
    results = run_scenario_analysis(
        two_asset_returns, equal_weights, bench_returns, start_value=sv
    )
    bull = next(r for r in results if r.name == "Bull Market")
    # new_value = start_value * (1 + portfolio_return)
    expected = sv * (1 + bull.portfolio_return)
    assert abs(bull.new_value - expected) < 1.0


def test_default_start_value_10000(two_asset_returns, equal_weights, bench_returns):
    results = run_scenario_analysis(two_asset_returns, equal_weights, bench_returns)
    bull = next(r for r in results if r.name == "Bull Market")
    # Should be ~10 000 * (1 + positive_ret)
    assert bull.new_value > 10_000


# ── stressed volatility ───────────────────────────────────────────────────────

def test_stressed_vol_higher_in_crash_than_bull(
    two_asset_returns, equal_weights, bench_returns
):
    results = run_scenario_analysis(two_asset_returns, equal_weights, bench_returns)
    bull  = next(r for r in results if r.name == "Bull Market")
    crash = next(r for r in results if r.name == "Severe Crash")
    # Stress factor increases correlation → higher portfolio vol in crash
    assert crash.stressed_vol >= bull.stressed_vol


def test_stressed_vol_is_positive(two_asset_returns, equal_weights, bench_returns):
    results = run_scenario_analysis(two_asset_returns, equal_weights, bench_returns)
    for r in results:
        assert r.stressed_vol > 0


# ── asset_impacts dict ────────────────────────────────────────────────────────

def test_asset_impacts_has_all_tickers(two_asset_returns, equal_weights, bench_returns):
    results = run_scenario_analysis(two_asset_returns, equal_weights, bench_returns)
    for r in results:
        assert set(r.asset_impacts.keys()) == {"AAPL", "MSFT"}


def test_asset_impacts_weighted_sum_equals_portfolio_return(
    two_asset_returns, equal_weights, bench_returns
):
    # asset_impacts stores beta*market_ret (unweighted); weighted sum = portfolio_return
    results = run_scenario_analysis(two_asset_returns, equal_weights, bench_returns)
    for r in results:
        weighted_total = sum(
            equal_weights.get(t, 0.0) * v for t, v in r.asset_impacts.items()
        )
        assert abs(weighted_total - r.portfolio_return) < 1e-9


# ── single-asset portfolio ────────────────────────────────────────────────────

def test_single_asset_portfolio_runs(single_asset_returns, single_bench):
    results = run_scenario_analysis(
        single_asset_returns, {"ONLY": 1.0}, single_bench
    )
    assert len(results) == 4
    assert all(isinstance(r, ScenarioResult) for r in results)


# ── custom scenarios ──────────────────────────────────────────────────────────

def test_custom_scenarios(two_asset_returns, equal_weights, bench_returns):
    custom = {"Mini Bull": 0.05, "Mini Bear": -0.05}
    results = run_scenario_analysis(
        two_asset_returns, equal_weights, bench_returns, scenarios=custom
    )
    assert len(results) == 2
    names = {r.name for r in results}
    assert names == {"Mini Bull", "Mini Bear"}


def test_custom_bull_positive_custom_bear_negative(
    two_asset_returns, equal_weights, bench_returns
):
    custom = {"Up": 0.10, "Down": -0.10}
    results = run_scenario_analysis(
        two_asset_returns, equal_weights, bench_returns, scenarios=custom
    )
    up   = next(r for r in results if r.name == "Up")
    down = next(r for r in results if r.name == "Down")
    assert up.portfolio_return > 0
    assert down.portfolio_return < 0
