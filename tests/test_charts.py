"""Tests for charts/* — verify that drawing functions run without error
and produce correctly shaped output. Uses matplotlib's non-interactive
Agg backend so no display is required.
"""

from __future__ import annotations

import matplotlib
matplotlib.use("Agg")   # must be set before importing pyplot

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest

from analytics.returns import (
    benchmark_value_series,
    daily_returns,
    portfolio_daily_returns,
    portfolio_value_series,
)
from analytics.risk import drawdown_series, rolling_volatility
from charts.drawdown import draw_drawdown_chart
from charts.frontier import draw_frontier_chart
from charts.growth import draw_growth_chart
from charts.risk_contribution import (
    draw_return_contribution_chart,
    draw_risk_contribution_chart,
)
from charts.rolling_vol import draw_rolling_vol_chart
from charts.correlation import (
    draw_correlation_heatmap,
    draw_covariance_heatmap,
    draw_correlation_clustermap,
)
from models.results import OptimizationResult


# ── Fixtures ──────────────────────────────────────────────────────────────────

def _bday(n: int, start: str = "2020-01-02") -> pd.DatetimeIndex:
    return pd.bdate_range(start, periods=n)


@pytest.fixture
def prices_df() -> pd.DataFrame:
    rng = np.random.default_rng(42)
    n = 400
    idx = _bday(n)
    return pd.DataFrame(
        {
            "AAPL": 100.0 * np.exp(np.cumsum(rng.normal(0.0006, 0.012, n))),
            "MSFT": 100.0 * np.exp(np.cumsum(rng.normal(0.0004, 0.010, n))),
            "SPY":  100.0 * np.exp(np.cumsum(rng.normal(0.0004, 0.008, n))),
        },
        index=idx,
    )


@pytest.fixture
def weights() -> dict[str, float]:
    return {"AAPL": 0.5, "MSFT": 0.3, "SPY": 0.2}


@pytest.fixture
def benchmark_prices(prices_df) -> pd.Series:
    return prices_df["SPY"]


@pytest.fixture
def portfolio_vals(prices_df, weights) -> pd.Series:
    return portfolio_value_series(prices_df, weights)


@pytest.fixture
def benchmark_vals(benchmark_prices) -> pd.Series:
    return benchmark_value_series(benchmark_prices)


@pytest.fixture
def port_rets(prices_df, weights) -> pd.Series:
    return portfolio_daily_returns(prices_df, weights)


@pytest.fixture
def returns_df(prices_df) -> pd.DataFrame:
    return daily_returns(prices_df)


@pytest.fixture
def ax():
    fig, ax = plt.subplots()
    yield ax
    plt.close(fig)


# ── Growth chart ──────────────────────────────────────────────────────────────

class TestGrowthChart:
    def test_draws_without_error(self, ax, portfolio_vals, benchmark_vals):
        draw_growth_chart(ax, portfolio_vals, benchmark_vals)

    def test_produces_two_lines(self, ax, portfolio_vals, benchmark_vals):
        draw_growth_chart(ax, portfolio_vals, benchmark_vals)
        assert len(ax.lines) >= 2

    def test_title_set(self, ax, portfolio_vals, benchmark_vals):
        draw_growth_chart(ax, portfolio_vals, benchmark_vals)
        assert "Growth" in ax.get_title()

    def test_custom_labels(self, ax, portfolio_vals, benchmark_vals):
        draw_growth_chart(
            ax, portfolio_vals, benchmark_vals,
            portfolio_label="My Portfolio",
            benchmark_label="SPY",
        )
        legend_labels = [t.get_text() for t in ax.get_legend().get_texts()]
        assert "My Portfolio" in legend_labels
        assert "SPY" in legend_labels

    def test_empty_portfolio_series_no_crash(self, ax, benchmark_vals):
        empty = pd.Series([], dtype=float, name="Portfolio")
        draw_growth_chart(ax, empty, benchmark_vals)


# ── Frontier chart ────────────────────────────────────────────────────────────

def _make_opt_result(method: str, vol: float, ret: float) -> OptimizationResult:
    return OptimizationResult(
        method=method,
        weights={"A": 0.5, "B": 0.5},
        expected_return=ret,
        volatility=vol,
        sharpe=(ret - 0.04) / vol,
    )


class TestFrontierChart:
    def test_draws_without_error(self, ax):
        risks   = [0.10, 0.12, 0.15, 0.18, 0.22]
        returns = [0.06, 0.08, 0.10, 0.12, 0.14]
        draw_frontier_chart(
            ax,
            risks, returns,
            current=_make_opt_result("current", 0.14, 0.09),
            max_sharpe_result=_make_opt_result("max_sharpe", 0.13, 0.10),
            min_variance_result=_make_opt_result("min_variance", 0.10, 0.06),
            black_litterman_result=_make_opt_result("black_litterman", 0.12, 0.08),
        )

    def test_frontier_line_plotted(self, ax):
        risks   = [0.10, 0.15, 0.20]
        returns = [0.06, 0.09, 0.12]
        draw_frontier_chart(
            ax, risks, returns,
            current=_make_opt_result("current", 0.14, 0.09),
            max_sharpe_result=_make_opt_result("max_sharpe", 0.13, 0.10),
            min_variance_result=_make_opt_result("min_variance", 0.10, 0.06),
            black_litterman_result=_make_opt_result("black_litterman", 0.12, 0.08),
        )
        assert len(ax.lines) >= 1

    def test_empty_frontier_no_crash(self, ax):
        draw_frontier_chart(
            ax, [], [],
            current=_make_opt_result("current", 0.14, 0.09),
            max_sharpe_result=_make_opt_result("max_sharpe", 0.13, 0.10),
            min_variance_result=_make_opt_result("min_variance", 0.10, 0.06),
            black_litterman_result=_make_opt_result("black_litterman", 0.12, 0.08),
        )

    def test_nan_portfolio_skipped(self, ax):
        nan_result = _make_opt_result("current", float("nan"), float("nan"))
        draw_frontier_chart(
            ax, [0.10, 0.15], [0.06, 0.09],
            current=nan_result,
            max_sharpe_result=_make_opt_result("max_sharpe", 0.13, 0.10),
            min_variance_result=_make_opt_result("min_variance", 0.10, 0.06),
            black_litterman_result=_make_opt_result("black_litterman", 0.12, 0.08),
        )


# ── Drawdown chart ────────────────────────────────────────────────────────────

class TestDrawdownChart:
    def test_draws_without_error(self, ax, portfolio_vals):
        dd = drawdown_series(portfolio_vals)
        draw_drawdown_chart(ax, dd)

    def test_produces_filled_area(self, ax, portfolio_vals):
        dd = drawdown_series(portfolio_vals)
        draw_drawdown_chart(ax, dd)
        assert len(ax.collections) >= 1   # fill_between produces a PolyCollection

    def test_title_set(self, ax, portfolio_vals):
        dd = drawdown_series(portfolio_vals)
        draw_drawdown_chart(ax, dd)
        assert "Drawdown" in ax.get_title()

    def test_flat_series_no_crash(self, ax):
        idx = pd.bdate_range("2020-01-02", periods=50)
        flat = pd.Series(100.0, index=idx)
        dd = drawdown_series(flat)
        draw_drawdown_chart(ax, dd)


# ── Rolling vol chart ─────────────────────────────────────────────────────────

class TestRollingVolChart:
    def test_draws_without_error(self, ax, port_rets):
        rv = rolling_volatility(port_rets, window=60)
        draw_rolling_vol_chart(ax, rv)

    def test_title_set(self, ax, port_rets):
        rv = rolling_volatility(port_rets)
        draw_rolling_vol_chart(ax, rv)
        assert "Volatility" in ax.get_title()

    def test_all_nan_shows_message(self, ax):
        rv = pd.Series([float("nan")] * 50)
        draw_rolling_vol_chart(ax, rv)
        # Should not raise; fallback text is shown


# ── Risk contribution chart ───────────────────────────────────────────────────

class TestRiskContributionChart:
    _rc = {"AAPL": 0.45, "MSFT": 0.35, "SPY": 0.20}
    _ret = {"AAPL": 0.04, "MSFT": 0.025, "SPY": -0.005}

    def test_risk_draws_without_error(self, ax):
        draw_risk_contribution_chart(ax, self._rc)

    def test_return_draws_without_error(self, ax):
        draw_return_contribution_chart(ax, self._ret)

    def test_risk_produces_bars(self, ax):
        draw_risk_contribution_chart(ax, self._rc)
        assert len(ax.patches) == len(self._rc)

    def test_return_produces_bars(self, ax):
        draw_return_contribution_chart(ax, self._ret)
        assert len(ax.patches) == len(self._ret)

    def test_single_asset_no_crash(self, ax):
        draw_risk_contribution_chart(ax, {"AAPL": 1.0})

    def test_negative_return_no_crash(self, ax):
        draw_return_contribution_chart(ax, {"A": -0.05, "B": 0.08})


# ── Correlation charts ────────────────────────────────────────────────────────

class TestCorrelationCharts:
    def test_correlation_heatmap_no_error(self, ax, returns_df):
        draw_correlation_heatmap(ax, returns_df, annot=False)

    def test_covariance_heatmap_no_error(self, ax, returns_df):
        draw_covariance_heatmap(ax, returns_df, annot=False)

    def test_clustermap_returns_figure(self, returns_df):
        fig = draw_correlation_clustermap(returns_df, figsize=(5, 4))
        import matplotlib.figure
        assert isinstance(fig, matplotlib.figure.Figure)
        plt.close(fig)

    def test_correlation_title_set(self, ax, returns_df):
        draw_correlation_heatmap(ax, returns_df, annot=False)
        assert "Correlation" in ax.get_title()

    def test_single_asset_no_crash(self, ax):
        idx = _bday(100)
        one_asset = pd.DataFrame({"AAPL": np.random.default_rng(1).normal(0, 0.01, 100)}, index=idx)
        draw_correlation_heatmap(ax, one_asset, annot=False)
