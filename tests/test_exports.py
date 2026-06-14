"""Tests for reports/csv_exporter.py and reports/excel_exporter.py.

PDF export is excluded from the automated suite because it depends on
matplotlib rendering which requires a display.  The CSV and Excel exporters
are pure I/O and can be tested headlessly.
"""

from __future__ import annotations

import csv
from pathlib import Path

import numpy as np
import openpyxl
import pandas as pd
import pytest

from models.asset import Asset
from models.portfolio import Portfolio
from models.results import AnalysisResult, AssetMetrics, OptimizationResult
from reports.csv_exporter import export_portfolio_csv
from reports.excel_exporter import export_portfolio_excel


# ── Shared fixture ────────────────────────────────────────────────────────────

def _make_asset(ticker: str, weight: float) -> AssetMetrics:
    return AssetMetrics(
        ticker=ticker,
        weight=weight,
        cagr=0.12,
        annualized_return=0.11,
        volatility=0.18,
        sharpe=0.75,
        sortino=0.90,
        beta=1.05,
        max_drawdown=0.22,
        var_95=0.015,
        var_99=0.025,
        cvar=0.032,
        latest_price=150.0,
        risk_contribution=weight,
        return_contribution=weight,
    )


def _make_opt(method: str, weights: dict[str, float]) -> OptimizationResult:
    return OptimizationResult(
        method=method,
        weights=weights,
        expected_return=0.10,
        volatility=0.16,
        sharpe=0.80,
        beta=0.95,
        var_95=0.014,
        max_drawdown=0.18,
    )


@pytest.fixture()
def minimal_result() -> AnalysisResult:
    """Minimal but complete AnalysisResult for export tests."""
    rng = np.random.default_rng(0)
    n = 252
    dates = pd.bdate_range("2023-01-02", periods=n)
    prices = pd.DataFrame(
        {"AAPL": np.cumprod(1 + rng.normal(0.0008, 0.012, n)) * 150,
         "MSFT": np.cumprod(1 + rng.normal(0.0006, 0.010, n)) * 300},
        index=dates,
    )
    returns = prices.pct_change().dropna()
    bench_p = pd.Series(
        np.cumprod(1 + rng.normal(0.0005, 0.010, n)) * 440, index=dates
    )
    bench_r = bench_p.pct_change().dropna()

    pf = Portfolio(
        assets=[Asset("AAPL", 0.6), Asset("MSFT", 0.4)],
        benchmark="SPY",
        period="3y",
        name="Test Portfolio",
    )

    current_opt = _make_opt("current",       {"AAPL": 0.6, "MSFT": 0.4})
    ms_opt      = _make_opt("max_sharpe",    {"AAPL": 0.55, "MSFT": 0.45})
    mv_opt      = _make_opt("min_variance",  {"AAPL": 0.45, "MSFT": 0.55})
    bl_opt      = _make_opt("black_litterman", {"AAPL": 0.50, "MSFT": 0.50})

    port_val = pd.Series(
        10_000 * np.cumprod(1 + returns @ np.array([0.6, 0.4])), index=returns.index
    )
    bench_val = pd.Series(
        10_000 * np.cumprod(1 + bench_r.values), index=bench_r.index
    )

    return AnalysisResult(
        portfolio=pf,
        prices=prices,
        returns=returns,
        benchmark_prices=bench_p,
        benchmark_returns=bench_r,
        portfolio_return=0.11,
        portfolio_cagr=0.10,
        portfolio_expected_return_capm=0.09,
        portfolio_volatility=0.18,
        sharpe_ratio=0.72,
        sortino_ratio=0.85,
        beta=1.02,
        max_drawdown=0.22,
        var_95=0.015,
        var_99=0.025,
        cvar=0.032,
        avg_correlation=0.45,
        diversification_score=0.62,
        asset_metrics={
            "AAPL": _make_asset("AAPL", 0.6),
            "MSFT": _make_asset("MSFT", 0.4),
        },
        optimization={
            "current":         current_opt,
            "max_sharpe":      ms_opt,
            "min_variance":    mv_opt,
            "black_litterman": bl_opt,
        },
        portfolio_value_series=port_val,
        benchmark_value_series=bench_val,
    )


# ── CSV exporter tests ────────────────────────────────────────────────────────

class TestCsvExporter:
    def test_creates_file(self, minimal_result, tmp_path):
        p = tmp_path / "report.csv"
        export_portfolio_csv(minimal_result, p)
        assert p.exists()

    def test_file_not_empty(self, minimal_result, tmp_path):
        p = tmp_path / "report.csv"
        export_portfolio_csv(minimal_result, p)
        assert p.stat().st_size > 100

    def test_contains_portfolio_name(self, minimal_result, tmp_path):
        p = tmp_path / "report.csv"
        export_portfolio_csv(minimal_result, p)
        content = p.read_text(encoding="utf-8")
        assert "Test Portfolio" in content

    def test_contains_both_tickers(self, minimal_result, tmp_path):
        p = tmp_path / "report.csv"
        export_portfolio_csv(minimal_result, p)
        content = p.read_text(encoding="utf-8")
        assert "AAPL" in content
        assert "MSFT" in content

    def test_contains_benchmark(self, minimal_result, tmp_path):
        p = tmp_path / "report.csv"
        export_portfolio_csv(minimal_result, p)
        content = p.read_text(encoding="utf-8")
        assert "SPY" in content

    def test_contains_period(self, minimal_result, tmp_path):
        p = tmp_path / "report.csv"
        export_portfolio_csv(minimal_result, p)
        content = p.read_text(encoding="utf-8")
        assert "3y" in content

    def test_contains_sharpe_value(self, minimal_result, tmp_path):
        p = tmp_path / "report.csv"
        export_portfolio_csv(minimal_result, p)
        content = p.read_text(encoding="utf-8")
        assert "Sharpe" in content

    def test_contains_optimization_section(self, minimal_result, tmp_path):
        p = tmp_path / "report.csv"
        export_portfolio_csv(minimal_result, p)
        content = p.read_text(encoding="utf-8")
        assert "OPTIMIZATION" in content

    def test_valid_csv_parses(self, minimal_result, tmp_path):
        p = tmp_path / "report.csv"
        export_portfolio_csv(minimal_result, p)
        with p.open(encoding="utf-8") as f:
            rows = list(csv.reader(f))
        assert len(rows) > 10

    def test_overwrite_existing_file(self, minimal_result, tmp_path):
        p = tmp_path / "report.csv"
        p.write_text("old content")
        export_portfolio_csv(minimal_result, p)
        content = p.read_text(encoding="utf-8")
        assert "Test Portfolio" in content
        assert "old content" not in content

    def test_no_portfolio_object_does_not_crash(self, tmp_path):
        result = AnalysisResult()
        result.asset_metrics = {}
        result.optimization = {}
        p = tmp_path / "report.csv"
        export_portfolio_csv(result, p)
        assert p.exists()


# ── Excel exporter tests ──────────────────────────────────────────────────────

class TestExcelExporter:
    def test_creates_file(self, minimal_result, tmp_path):
        p = tmp_path / "report.xlsx"
        export_portfolio_excel(minimal_result, p)
        assert p.exists()

    def test_file_not_empty(self, minimal_result, tmp_path):
        p = tmp_path / "report.xlsx"
        export_portfolio_excel(minimal_result, p)
        assert p.stat().st_size > 2_000

    def test_four_sheets(self, minimal_result, tmp_path):
        p = tmp_path / "report.xlsx"
        export_portfolio_excel(minimal_result, p)
        wb = openpyxl.load_workbook(str(p))
        assert len(wb.sheetnames) == 4

    def test_sheet_names(self, minimal_result, tmp_path):
        p = tmp_path / "report.xlsx"
        export_portfolio_excel(minimal_result, p)
        wb = openpyxl.load_workbook(str(p))
        assert "Summary" in wb.sheetnames
        assert "Assets" in wb.sheetnames
        assert "Optimization" in wb.sheetnames
        assert "Scenarios" in wb.sheetnames

    def test_summary_contains_portfolio_name(self, minimal_result, tmp_path):
        p = tmp_path / "report.xlsx"
        export_portfolio_excel(minimal_result, p)
        wb = openpyxl.load_workbook(str(p))
        ws = wb["Summary"]
        values = [str(c.value or "") for row in ws.iter_rows() for c in row]
        combined = " ".join(values)
        assert "Test Portfolio" in combined

    def test_assets_sheet_has_both_tickers(self, minimal_result, tmp_path):
        p = tmp_path / "report.xlsx"
        export_portfolio_excel(minimal_result, p)
        wb = openpyxl.load_workbook(str(p))
        ws = wb["Assets"]
        values = [str(c.value or "") for row in ws.iter_rows() for c in row]
        combined = " ".join(values)
        assert "AAPL" in combined
        assert "MSFT" in combined

    def test_assets_sheet_row_count(self, minimal_result, tmp_path):
        """Header + 2 asset rows = at least 3 rows."""
        p = tmp_path / "report.xlsx"
        export_portfolio_excel(minimal_result, p)
        wb = openpyxl.load_workbook(str(p))
        ws = wb["Assets"]
        non_empty = [r for r in ws.iter_rows(values_only=True) if any(c for c in r)]
        assert len(non_empty) >= 3

    def test_optimization_sheet_has_max_sharpe(self, minimal_result, tmp_path):
        p = tmp_path / "report.xlsx"
        export_portfolio_excel(minimal_result, p)
        wb = openpyxl.load_workbook(str(p))
        ws = wb["Optimization"]
        values = [str(c.value or "") for row in ws.iter_rows() for c in row]
        combined = " ".join(values)
        assert "Maximum Sharpe" in combined or "MAX" in combined.upper()

    def test_scenarios_sheet_exists_and_not_empty(self, minimal_result, tmp_path):
        p = tmp_path / "report.xlsx"
        export_portfolio_excel(minimal_result, p)
        wb = openpyxl.load_workbook(str(p))
        ws = wb["Scenarios"]
        rows = list(ws.iter_rows(values_only=True))
        non_empty = [r for r in rows if any(c for c in r)]
        assert len(non_empty) >= 1

    def test_no_portfolio_object_does_not_crash(self, tmp_path):
        result = AnalysisResult()
        result.asset_metrics = {}
        result.optimization = {}
        p = tmp_path / "report.xlsx"
        export_portfolio_excel(result, p)
        assert p.exists()
