"""AnalysisResult dataclass — all computed metrics for one analysis run."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import numpy as np
import pandas as pd

if TYPE_CHECKING:
    from models.portfolio import Portfolio
    from models.settings import AnalysisSettings


@dataclass
class AssetMetrics:
    """Per-asset analytics, used by Tab 2 (Asset Analysis)."""

    ticker: str
    weight: float
    cagr: float
    annualized_return: float
    volatility: float
    sharpe: float
    sortino: float
    beta: float
    max_drawdown: float
    var_95: float
    var_99: float
    cvar: float
    latest_price: float = float("nan")
    dividend_yield: float = float("nan")
    benchmark_correlation: float = float("nan")
    risk_contribution: float = float("nan")
    return_contribution: float = float("nan")


@dataclass
class OptimizationResult:
    """Weights and metrics produced by one optimizer."""

    method: str                          # "max_sharpe" | "min_variance" | "black_litterman"
    weights: dict[str, float] = field(default_factory=dict)
    expected_return: float = float("nan")
    volatility: float = float("nan")
    sharpe: float = float("nan")
    beta: float = float("nan")
    var_95: float = float("nan")
    max_drawdown: float = float("nan")


@dataclass
class AnalysisResult:
    """Container for all results produced by one full analysis run.

    Filled progressively by the analytics + optimization layers;
    the UI reads from this object only — it never calls analytics directly.
    """

    # ── Inputs ──────────────────────────────────────────────────────────────
    portfolio: Portfolio | None = None
    settings: AnalysisSettings | None = None

    # ── Price / return data ──────────────────────────────────────────────────
    prices: pd.DataFrame = field(default_factory=pd.DataFrame)          # adj close per ticker
    returns: pd.DataFrame = field(default_factory=pd.DataFrame)         # daily returns per ticker
    benchmark_prices: pd.Series = field(default_factory=pd.Series)
    benchmark_returns: pd.Series = field(default_factory=pd.Series)

    # ── Portfolio-level metrics ──────────────────────────────────────────────
    portfolio_return: float = float("nan")       # annualized mean return (daily × 252)
    portfolio_cagr: float = float("nan")
    portfolio_expected_return_capm: float = float("nan")
    portfolio_volatility: float = float("nan")   # annualized
    sharpe_ratio: float = float("nan")
    sortino_ratio: float = float("nan")
    beta: float = float("nan")
    max_drawdown: float = float("nan")
    var_95: float = float("nan")
    var_99: float = float("nan")
    cvar: float = float("nan")

    # ── Diversification ──────────────────────────────────────────────────────
    avg_correlation: float = float("nan")
    diversification_score: float = float("nan")  # 0–1; higher = more diversified

    # ── Per-asset metrics ────────────────────────────────────────────────────
    asset_metrics: dict[str, AssetMetrics] = field(default_factory=dict)

    # ── Optimization results ─────────────────────────────────────────────────
    optimization: dict[str, OptimizationResult] = field(default_factory=dict)

    # ── Chart data series (computed once, read by chart functions) ───────────
    portfolio_value_series: pd.Series = field(default_factory=pd.Series)   # growth from 10k
    benchmark_value_series: pd.Series = field(default_factory=pd.Series)
    drawdown_series: pd.Series = field(default_factory=pd.Series)
    rolling_volatility_series: pd.Series = field(default_factory=pd.Series)
    frontier_risk: list[float] = field(default_factory=list)
    frontier_return: list[float] = field(default_factory=list)

    # ── Error reporting ──────────────────────────────────────────────────────
    failed_tickers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def is_empty(self) -> bool:
        return self.prices.empty
