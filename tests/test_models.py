"""Unit tests for models.Asset, Portfolio, AnalysisSettings, AnalysisResult."""

import pytest

from models.asset import Asset
from models.portfolio import Portfolio
from models.settings import AnalysisSettings, ExpectedReturnMethod
from models.results import AnalysisResult, AssetMetrics, OptimizationResult


# ── Asset ────────────────────────────────────────────────────────────────────

class TestAsset:
    def test_basic_construction(self):
        a = Asset(ticker="aapl", weight=0.5)
        assert a.ticker == "AAPL"        # normalised to upper
        assert a.weight == 0.5
        assert a.name == ""

    def test_with_name(self):
        a = Asset(ticker="SPY", weight=0.3, name="SPDR S&P 500")
        assert a.name == "SPDR S&P 500"

    def test_weight_zero_is_valid(self):
        a = Asset(ticker="MSFT", weight=0.0)
        assert a.weight == 0.0

    def test_weight_one_is_valid(self):
        a = Asset(ticker="MSFT", weight=1.0)
        assert a.weight == 1.0

    def test_weight_above_one_raises(self):
        with pytest.raises(ValueError, match="Weight must be in"):
            Asset(ticker="MSFT", weight=1.01)

    def test_weight_below_zero_raises(self):
        with pytest.raises(ValueError, match="Weight must be in"):
            Asset(ticker="MSFT", weight=-0.01)

    def test_ticker_stripped_and_uppercased(self):
        a = Asset(ticker="  msft  ", weight=0.1)
        assert a.ticker == "MSFT"


# ── Portfolio ─────────────────────────────────────────────────────────────────

class TestPortfolio:
    def _make(self) -> Portfolio:
        return Portfolio(
            assets=[Asset("AAPL", 0.5), Asset("MSFT", 0.3), Asset("SPY", 0.2)],
            benchmark="SPY",
            period="5y",
            name="Test",
        )

    def test_basic_construction(self):
        p = self._make()
        assert p.tickers == ["AAPL", "MSFT", "SPY"]
        assert p.total_weight == pytest.approx(1.0)

    def test_invalid_benchmark_raises(self):
        with pytest.raises(ValueError, match="Benchmark"):
            Portfolio(benchmark="INVALID")

    def test_invalid_period_raises(self):
        with pytest.raises(ValueError, match="Period"):
            Portfolio(period="7y")

    def test_equal_weight(self):
        p = Portfolio(assets=[Asset("A", 0.1), Asset("B", 0.1), Asset("C", 0.1)])
        p.apply_equal_weight()
        for a in p.assets:
            assert a.weight == pytest.approx(1 / 3)

    def test_normalize_weights(self):
        p = Portfolio(assets=[Asset("A", 0.2), Asset("B", 0.4)])
        p.normalize_weights()
        assert p.total_weight == pytest.approx(1.0)
        assert p.assets[0].weight == pytest.approx(1 / 3)
        assert p.assets[1].weight == pytest.approx(2 / 3)

    def test_normalize_all_zero_raises(self):
        p = Portfolio(assets=[Asset("A", 0.0), Asset("B", 0.0)])
        with pytest.raises(ValueError, match="zero"):
            p.normalize_weights()

    def test_weight_of_existing_ticker(self):
        p = self._make()
        assert p.weight_of("MSFT") == pytest.approx(0.3)

    def test_weight_of_missing_ticker_raises(self):
        p = self._make()
        with pytest.raises(KeyError):
            p.weight_of("GOOG")

    def test_weights_property(self):
        p = self._make()
        assert p.weights == [0.5, 0.3, 0.2]

    def test_empty_equal_weight_noop(self):
        p = Portfolio()
        p.apply_equal_weight()   # should not raise
        assert p.assets == []


# ── AnalysisSettings ──────────────────────────────────────────────────────────

class TestAnalysisSettings:
    def test_defaults(self):
        s = AnalysisSettings()
        assert s.risk_free_rate == 0.04
        assert s.market_expected_return == 0.10
        assert s.expected_return_method == ExpectedReturnMethod.HISTORICAL_AVG
        assert s.monte_carlo_simulations == 1_000
        assert s.monte_carlo_horizon_years == 5

    def test_custom_values(self):
        s = AnalysisSettings(risk_free_rate=0.02, monte_carlo_simulations=500)
        assert s.risk_free_rate == 0.02
        assert s.monte_carlo_simulations == 500

    def test_invalid_risk_free_rate_raises(self):
        with pytest.raises(ValueError, match="risk_free_rate"):
            AnalysisSettings(risk_free_rate=1.5)

    def test_invalid_market_return_raises(self):
        with pytest.raises(ValueError, match="market_expected_return"):
            AnalysisSettings(market_expected_return=-0.1)

    def test_zero_simulations_raises(self):
        with pytest.raises(ValueError, match="monte_carlo_simulations"):
            AnalysisSettings(monte_carlo_simulations=0)

    def test_zero_horizon_raises(self):
        with pytest.raises(ValueError, match="monte_carlo_horizon_years"):
            AnalysisSettings(monte_carlo_horizon_years=0)

    def test_string_method_accepted(self):
        s = AnalysisSettings(expected_return_method="cagr")  # type: ignore[arg-type]
        assert s.expected_return_method == ExpectedReturnMethod.CAGR

    def test_invalid_string_method_raises(self):
        with pytest.raises(ValueError):
            AnalysisSettings(expected_return_method="unknown")  # type: ignore[arg-type]


# ── AnalysisResult ─────────────────────────────────────────────────────────────

class TestAnalysisResult:
    def test_empty_by_default(self):
        r = AnalysisResult()
        assert r.is_empty
        assert r.failed_tickers == []
        assert r.warnings == []

    def test_failed_tickers_accumulate(self):
        r = AnalysisResult()
        r.failed_tickers.append("BADTICKER")
        assert "BADTICKER" in r.failed_tickers

    def test_optimization_dict(self):
        r = AnalysisResult()
        r.optimization["max_sharpe"] = OptimizationResult(
            method="max_sharpe", weights={"AAPL": 0.6, "MSFT": 0.4}
        )
        assert r.optimization["max_sharpe"].weights["AAPL"] == 0.6
