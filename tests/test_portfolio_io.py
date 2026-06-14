"""Tests for services.portfolio_io — JSON save/load round-trips."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from models.asset import Asset
from models.portfolio import Portfolio
from models.settings import AnalysisSettings, ExpectedReturnMethod
from services.portfolio_io import load_portfolio, save_portfolio


def _make_portfolio() -> Portfolio:
    return Portfolio(
        assets=[
            Asset("AAPL", 0.4, "Apple Inc."),
            Asset("MSFT", 0.35, "Microsoft Corp."),
            Asset("SPY",  0.25, "SPDR S&P 500"),
        ],
        benchmark="SPY",
        period="5y",
        name="Tech Heavy",
    )


def _make_settings() -> AnalysisSettings:
    return AnalysisSettings(
        risk_free_rate=0.035,
        market_expected_return=0.09,
        expected_return_method=ExpectedReturnMethod.CAPM,
        monte_carlo_simulations=500,
        monte_carlo_horizon_years=10,
    )


class TestSavePortfolio:
    def test_creates_file(self, tmp_path: Path):
        path = tmp_path / "p.json"
        save_portfolio(_make_portfolio(), _make_settings(), path)
        assert path.exists()

    def test_valid_json(self, tmp_path: Path):
        path = tmp_path / "p.json"
        save_portfolio(_make_portfolio(), _make_settings(), path)
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["version"] == 1
        assert data["name"] == "Tech Heavy"

    def test_assets_serialised(self, tmp_path: Path):
        path = tmp_path / "p.json"
        save_portfolio(_make_portfolio(), _make_settings(), path)
        data = json.loads(path.read_text(encoding="utf-8"))
        assert len(data["assets"]) == 3
        tickers = [a["ticker"] for a in data["assets"]]
        assert "AAPL" in tickers

    def test_settings_serialised(self, tmp_path: Path):
        path = tmp_path / "p.json"
        save_portfolio(_make_portfolio(), _make_settings(), path)
        data = json.loads(path.read_text(encoding="utf-8"))
        s = data["settings"]
        assert s["risk_free_rate"] == pytest.approx(0.035)
        assert s["expected_return_method"] == "capm"
        assert s["monte_carlo_simulations"] == 500

    def test_creates_parent_directories(self, tmp_path: Path):
        path = tmp_path / "nested" / "dir" / "p.json"
        save_portfolio(_make_portfolio(), _make_settings(), path)
        assert path.exists()


class TestLoadPortfolio:
    def _round_trip(self, tmp_path: Path) -> tuple[Portfolio, AnalysisSettings]:
        path = tmp_path / "p.json"
        save_portfolio(_make_portfolio(), _make_settings(), path)
        return load_portfolio(path)

    def test_round_trip_portfolio_name(self, tmp_path: Path):
        p, _ = self._round_trip(tmp_path)
        assert p.name == "Tech Heavy"

    def test_round_trip_assets(self, tmp_path: Path):
        p, _ = self._round_trip(tmp_path)
        assert len(p.assets) == 3
        assert p.tickers == ["AAPL", "MSFT", "SPY"]

    def test_round_trip_weights(self, tmp_path: Path):
        p, _ = self._round_trip(tmp_path)
        assert p.weight_of("AAPL") == pytest.approx(0.4)
        assert p.weight_of("MSFT") == pytest.approx(0.35)

    def test_round_trip_benchmark_and_period(self, tmp_path: Path):
        p, _ = self._round_trip(tmp_path)
        assert p.benchmark == "SPY"
        assert p.period == "5y"

    def test_round_trip_settings(self, tmp_path: Path):
        _, s = self._round_trip(tmp_path)
        assert s.risk_free_rate == pytest.approx(0.035)
        assert s.expected_return_method == ExpectedReturnMethod.CAPM
        assert s.monte_carlo_simulations == 500
        assert s.monte_carlo_horizon_years == 10

    def test_asset_name_preserved(self, tmp_path: Path):
        p, _ = self._round_trip(tmp_path)
        apple = next(a for a in p.assets if a.ticker == "AAPL")
        assert apple.name == "Apple Inc."

    def test_file_not_found_raises(self, tmp_path: Path):
        with pytest.raises(FileNotFoundError):
            load_portfolio(tmp_path / "nonexistent.json")

    def test_wrong_version_raises(self, tmp_path: Path):
        path = tmp_path / "bad.json"
        path.write_text(json.dumps({"version": 99, "assets": []}), encoding="utf-8")
        with pytest.raises(ValueError, match="version"):
            load_portfolio(path)

    def test_malformed_json_raises(self, tmp_path: Path):
        path = tmp_path / "bad.json"
        path.write_text("not json {{{", encoding="utf-8")
        with pytest.raises(Exception):
            load_portfolio(path)

    def test_missing_settings_uses_defaults(self, tmp_path: Path):
        """A file with no 'settings' key should load with default AnalysisSettings."""
        path = tmp_path / "minimal.json"
        data = {
            "version": 1,
            "name": "Minimal",
            "assets": [{"ticker": "SPY", "weight": 1.0, "name": ""}],
            "benchmark": "SPY",
            "period": "1y",
        }
        path.write_text(json.dumps(data), encoding="utf-8")
        p, s = load_portfolio(path)
        assert s.risk_free_rate == pytest.approx(0.04)
        assert s.monte_carlo_simulations == 1_000
