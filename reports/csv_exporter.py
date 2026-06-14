"""CSV export — portfolio metrics and asset analysis table."""

from __future__ import annotations

import csv
import math
from datetime import date
from pathlib import Path

from models.results import AnalysisResult


def _pct(v: float, dec: int = 2) -> str:
    return "" if math.isnan(v) else f"{v * 100:.{dec}f} %"


def _num(v: float, dec: int = 2) -> str:
    return "" if math.isnan(v) else f"{v:.{dec}f}"


def _eur(v: float) -> str:
    return "" if math.isnan(v) else f"{v:,.2f}"


def export_portfolio_csv(result: AnalysisResult, path: Path) -> None:
    """Write a multi-section CSV report for the portfolio analysis.

    Sections:
      1. Report metadata
      2. Portfolio-level metrics
      3. Per-asset metrics table
      4. Optimization weights (all three optimizers)

    Args:
        result: Full AnalysisResult from the analysis engine.
        path:   Destination file path (will be created or overwritten).
    """
    portfolio = result.portfolio
    period    = portfolio.period    if portfolio else "?"
    name      = portfolio.name      if portfolio else "Portfolio"
    benchmark = portfolio.benchmark if portfolio else "?"

    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)

        # ── 1. Metadata ──────────────────────────────────────────────────────
        w.writerow(["Portfolio Analysis Report"])
        w.writerow(["Generated", date.today().isoformat()])
        w.writerow(["Portfolio Name", name])
        w.writerow(["Benchmark", benchmark])
        w.writerow(["Period", period])
        w.writerow([])

        # ── 2. Portfolio metrics ─────────────────────────────────────────────
        w.writerow(["PORTFOLIO METRICS"])
        w.writerow(["Metric", "Value"])
        metrics = [
            ("Expected Return (ann.)",  _pct(result.portfolio_return)),
            ("CAGR",                    _pct(result.portfolio_cagr)),
            ("CAPM Expected Return",    _pct(result.portfolio_expected_return_capm)),
            ("Volatility (ann.)",       _pct(result.portfolio_volatility)),
            ("Sharpe Ratio",            _num(result.sharpe_ratio)),
            ("Sortino Ratio",           _num(result.sortino_ratio)),
            ("Beta",                    _num(result.beta)),
            ("Max Drawdown",            _pct(result.max_drawdown)),
            ("VaR 95 %",                _pct(result.var_95)),
            ("VaR 99 %",                _pct(result.var_99)),
            ("CVaR (95 %)",             _pct(result.cvar)),
            ("Avg Correlation",         _num(result.avg_correlation)),
            ("Diversification Score",   _num(result.diversification_score)),
        ]
        for row in metrics:
            w.writerow(row)
        w.writerow([])

        # ── 3. Asset analysis ────────────────────────────────────────────────
        w.writerow(["ASSET ANALYSIS"])
        headers = [
            "Ticker", "Weight", "Latest Price (€)",
            "CAGR", "Return (ann.)", "Volatility",
            "Sharpe", "Sortino", "Beta",
            "Max Drawdown", "VaR 95 %", "VaR 99 %", "CVaR",
            "Risk Contribution", "Return Contribution",
        ]
        w.writerow(headers)
        for m in result.asset_metrics.values():
            w.writerow([
                m.ticker,
                _pct(m.weight),
                _eur(m.latest_price),
                _pct(m.cagr),
                _pct(m.annualized_return),
                _pct(m.volatility),
                _num(m.sharpe),
                _num(m.sortino),
                _num(m.beta),
                _pct(m.max_drawdown),
                _pct(m.var_95),
                _pct(m.var_99),
                _pct(m.cvar),
                _pct(m.risk_contribution),
                _pct(m.return_contribution),
            ])
        w.writerow([])

        # ── 4. Optimization weights ──────────────────────────────────────────
        w.writerow(["OPTIMIZATION RESULTS"])
        opt_keys = ["max_sharpe", "min_variance", "black_litterman"]
        opt_labels = {
            "max_sharpe": "Maximum Sharpe",
            "min_variance": "Minimum Variance",
            "black_litterman": "Black-Litterman",
        }
        # Header: Ticker | Current | Max Sharpe | Min Var | BL
        current = result.optimization.get("current")
        tickers = (
            list(current.weights.keys())
            if current and current.weights
            else list(result.asset_metrics.keys())
        )
        opt_header = ["Ticker", "Current Weight"] + [opt_labels[k] for k in opt_keys]
        w.writerow(opt_header)
        for ticker in tickers:
            row = [ticker, _pct(current.weights.get(ticker, 0.0) if current else 0.0)]
            for key in opt_keys:
                opt = result.optimization.get(key)
                row.append(_pct(opt.weights.get(ticker, 0.0)) if opt and opt.weights else "")
            w.writerow(row)
        w.writerow([])

        # Metric comparison
        w.writerow(["Metric", "Current"] + [opt_labels[k] for k in opt_keys])
        metric_rows = [
            ("Expected Return", lambda o: _pct(o.expected_return)),
            ("Volatility",      lambda o: _pct(o.volatility)),
            ("Sharpe",          lambda o: _num(o.sharpe)),
            ("Beta",            lambda o: _num(o.beta)),
            ("VaR 95 %",        lambda o: _pct(o.var_95)),
            ("Max Drawdown",    lambda o: _pct(o.max_drawdown)),
        ]
        for label, fn in metric_rows:
            row = [label, fn(current) if current else ""]
            for key in opt_keys:
                opt = result.optimization.get(key)
                row.append(fn(opt) if opt else "")
            w.writerow(row)
