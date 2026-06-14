"""Tab 1 — Portfolio Dashboard: the primary workspace.

Layout:
  Left panel  (fixed ~320 px)  — Section A: Portfolio Builder
  Right panel (scrollable)     — Section B: Metrics
                                 Section C: Optimization
                                 Section D: Visualizations
"""

from __future__ import annotations

import traceback
from pathlib import Path

import numpy as np
import pandas as pd
from PySide6.QtCore import (
    Qt, QThread, QObject, QTimer, Signal, Slot,
)
from PySide6.QtWidgets import (
    QAbstractItemView, QComboBox, QFileDialog, QFrame,
    QGridLayout, QGroupBox, QHBoxLayout, QHeaderView,
    QLabel, QLineEdit, QMessageBox, QPushButton,
    QScrollArea, QSizePolicy, QSplitter,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from analytics.diversification import (
    average_correlation, diversification_score,
    return_contributions, risk_contributions,
)
from analytics.health_score import portfolio_health_score
from analytics.returns import (
    annualized_return, benchmark_value_series,
    capm_expected_return, cagr,
    portfolio_daily_returns, portfolio_value_series,
)
from analytics.risk import (
    annualized_volatility, beta as compute_beta,
    drawdown_series, historical_cvar, historical_var,
    max_drawdown, portfolio_beta, portfolio_volatility,
    rolling_volatility, sharpe_ratio, sortino_ratio,
)
from charts.drawdown import draw_drawdown_chart
from charts.frontier import draw_frontier_chart
from charts.growth import draw_growth_chart
from charts.risk_contribution import (
    draw_return_contribution_chart, draw_risk_contribution_chart,
)
from charts.rolling_vol import draw_rolling_vol_chart
from models.asset import Asset
from models.portfolio import Portfolio
from models.results import AnalysisResult, AssetMetrics, OptimizationResult
from models.settings import AnalysisSettings
from optimization.efficient_frontier import build_frontier_data
from optimization.optimizers import black_litterman, max_sharpe, min_variance
from services.data_service import DataService
from services.portfolio_io import load_portfolio, save_portfolio
from ui.theme import (
    ACCENT, BG_PRIMARY, BG_SECONDARY, BG_TERTIARY,
    BORDER, DANGER, SUCCESS, TEXT_PRIMARY, TEXT_SECONDARY, WARNING,
)
from ui.widgets.chart_canvas import ChartCanvas
from ui.widgets.metric_card import MetricCard
from utils.constants import (
    ANALYSIS_PERIODS, BENCHMARKS,
    DEFAULT_BENCHMARK, DEFAULT_PERIOD,
)
from utils.logging import get_logger
from utils.validators import validate_ticker

log = get_logger(__name__)


# ── Analysis worker ────────────────────────────────────────────────────────────

class AnalysisWorker(QObject):
    """Runs a full portfolio analysis in a background QThread."""

    finished = Signal(object)   # emits AnalysisResult
    error    = Signal(str)
    progress = Signal(str)

    def __init__(self, portfolio: Portfolio, settings: AnalysisSettings) -> None:
        super().__init__()
        self._portfolio = portfolio
        self._settings  = settings

    @Slot()
    def run(self) -> None:
        try:
            result = self._compute()
            self.finished.emit(result)
        except Exception as exc:
            log.error("Analysis failed:\n%s", traceback.format_exc())
            self.error.emit(str(exc))

    def _compute(self) -> AnalysisResult:  # noqa: C901 (acceptable complexity for orchestration)
        portfolio = self._portfolio
        settings  = self._settings

        # ── 1. Fetch prices ──────────────────────────────────────────────────
        self.progress.emit("Fetching price data…")
        svc   = DataService()
        fetch = svc.fetch_prices(portfolio.tickers, portfolio.period)
        prices: pd.DataFrame = fetch.prices.copy()

        bench_prices: pd.Series = svc.fetch_single(portfolio.benchmark, portfolio.period)
        bench_prices = bench_prices.reindex(prices.index).ffill().dropna()

        # ── 2. Resolve weights (drop failed tickers, renormalise) ────────────
        available  = set(prices.columns)
        weights: dict[str, float] = {
            t: portfolio.weight_of(t)
            for t in portfolio.tickers if t in available
        }
        w_total = sum(weights.values())
        if w_total == 0:
            raise ValueError("All tickers failed — no data available.")
        if abs(w_total - 1.0) > 1e-4:
            weights = {t: w / w_total for t, w in weights.items()}

        tickers_ok = list(weights.keys())
        prices = prices[tickers_ok]

        # ── 3. Returns and alignment ─────────────────────────────────────────
        self.progress.emit("Computing returns and risk metrics…")
        rets: pd.DataFrame = prices.pct_change().dropna()
        bench_rets_raw: pd.Series = bench_prices.pct_change().dropna()

        common = rets.index.intersection(bench_rets_raw.index)
        rets_a       = rets.loc[common]
        bench_rets_a = bench_rets_raw.loc[common]

        port_rets = portfolio_daily_returns(prices, weights).loc[common]

        # ── 4. Portfolio-level metrics ───────────────────────────────────────
        ann_ret   = annualized_return(port_rets)
        port_val  = portfolio_value_series(prices, weights)
        port_cagr = cagr(port_val)
        port_vol  = portfolio_volatility(rets_a, weights)
        p_sharpe  = sharpe_ratio(ann_ret, port_vol, settings.risk_free_rate)
        p_sortino = sortino_ratio(port_rets, ann_ret, settings.risk_free_rate)
        p_beta    = portfolio_beta(port_rets, bench_rets_a)
        capm_ret  = capm_expected_return(
            p_beta, settings.risk_free_rate, settings.market_expected_return,
        )
        mdd    = max_drawdown(port_val)
        var95  = historical_var(port_rets, 0.95)
        var99  = historical_var(port_rets, 0.99)
        cvar   = historical_cvar(port_rets, 0.95)
        avg_c  = average_correlation(rets_a)
        div_sc = diversification_score(rets_a, weights)

        current_opt = OptimizationResult(
            method="current",
            weights=weights,
            expected_return=ann_ret,
            volatility=port_vol,
            sharpe=p_sharpe,
            beta=p_beta,
            var_95=var95,
            max_drawdown=mdd,
        )

        # ── 5. Per-asset metrics ─────────────────────────────────────────────
        risk_c = risk_contributions(rets_a, weights)
        ann_rets_per_ticker = {t: annualized_return(rets_a[t]) for t in tickers_ok}
        ret_c  = return_contributions(ann_rets_per_ticker, weights)

        asset_metrics: dict[str, AssetMetrics] = {}
        for ticker in tickers_ok:
            a_rets = rets_a[ticker]
            a_ann  = ann_rets_per_ticker[ticker]
            a_vol  = annualized_volatility(a_rets)
            asset_metrics[ticker] = AssetMetrics(
                ticker=ticker,
                weight=weights[ticker],
                cagr=cagr(prices[ticker]),
                annualized_return=a_ann,
                volatility=a_vol,
                sharpe=sharpe_ratio(a_ann, a_vol, settings.risk_free_rate),
                sortino=sortino_ratio(a_rets, a_ann, settings.risk_free_rate),
                beta=compute_beta(a_rets, bench_rets_a),
                max_drawdown=max_drawdown(prices[ticker]),
                var_95=historical_var(a_rets, 0.95),
                var_99=historical_var(a_rets, 0.99),
                cvar=historical_cvar(a_rets, 0.95),
                latest_price=float(prices[ticker].iloc[-1]),
                risk_contribution=risk_c.get(ticker, float("nan")),
                return_contribution=ret_c.get(ticker, float("nan")),
            )

        # ── 6. Optimizers ────────────────────────────────────────────────────
        self.progress.emit("Running portfolio optimization…")
        opt_results: dict[str, OptimizationResult] = {"current": current_opt}
        for key, fn in [
            ("max_sharpe",       max_sharpe),
            ("min_variance",     min_variance),
            ("black_litterman",  black_litterman),
        ]:
            try:
                opt_results[key] = fn(prices, settings, bench_prices)
            except Exception as exc:
                log.warning("Optimizer '%s' failed: %s", key, exc)
                opt_results[key] = OptimizationResult(method=key)

        # ── 7. Frontier ──────────────────────────────────────────────────────
        self.progress.emit("Sampling efficient frontier…")
        frontier_risks:   list[float] = []
        frontier_returns: list[float] = []
        try:
            fd = build_frontier_data(prices, weights, settings, bench_prices, n_points=50)
            frontier_risks   = fd.frontier_risks
            frontier_returns = fd.frontier_returns
        except Exception as exc:
            log.warning("Frontier sampling failed: %s", exc)

        # ── 8. Chart data series ─────────────────────────────────────────────
        bench_vals = benchmark_value_series(bench_prices)
        dd_series  = drawdown_series(port_val)
        roll_vol   = rolling_volatility(port_rets, window=252)

        # ── 9. Assemble ──────────────────────────────────────────────────────
        return AnalysisResult(
            portfolio=portfolio,
            settings=settings,
            prices=prices,
            returns=rets_a,
            benchmark_prices=bench_prices,
            benchmark_returns=bench_rets_a,
            portfolio_return=ann_ret,
            portfolio_cagr=port_cagr,
            portfolio_expected_return_capm=capm_ret,
            portfolio_volatility=port_vol,
            sharpe_ratio=p_sharpe,
            sortino_ratio=p_sortino,
            beta=p_beta,
            max_drawdown=mdd,
            var_95=var95,
            var_99=var99,
            cvar=cvar,
            avg_correlation=avg_c,
            diversification_score=div_sc,
            asset_metrics=asset_metrics,
            optimization=opt_results,
            portfolio_value_series=port_val,
            benchmark_value_series=bench_vals,
            drawdown_series=dd_series,
            rolling_volatility_series=roll_vol,
            frontier_risk=frontier_risks,
            frontier_return=frontier_returns,
            failed_tickers=fetch.failed_tickers,
            warnings=fetch.warnings,
        )


# ── Helper constants ───────────────────────────────────────────────────────────

_OPT_LABELS = {
    "max_sharpe":      "Max Sharpe",
    "min_variance":    "Min Variance",
    "black_litterman": "Black-Litterman",
}


def _fmt_pct(v: float, decimals: int = 2) -> str:
    return "—" if np.isnan(v) else f"{v * 100:.{decimals}f} %"


def _fmt_num(v: float, decimals: int = 2) -> str:
    return "—" if np.isnan(v) else f"{v:.{decimals}f}"


def _color_return(v: float) -> str | None:
    if np.isnan(v):
        return None
    return SUCCESS if v >= 0 else DANGER


def _color_risk(v: float, threshold: float = 0.20) -> str | None:
    if np.isnan(v):
        return None
    return WARNING if v > threshold else SUCCESS


# ── DashboardTab ───────────────────────────────────────────────────────────────

class DashboardTab(QWidget):
    """Primary workspace: portfolio construction, metrics, optimization, charts."""

    status_message  = Signal(str)
    analysis_ready  = Signal(object)   # emits AnalysisResult after a full analysis

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        # State
        self._portfolio: Portfolio = Portfolio()
        self._settings:  AnalysisSettings = AnalysisSettings()
        self._result:    AnalysisResult | None = None

        # Cached price data for quick weight-change recompute
        self._last_prices:       pd.DataFrame | None = None
        self._last_bench_prices: pd.Series    | None = None

        # Thread management
        self._thread: QThread | None = None
        self._worker: AnalysisWorker | None = None

        # Flag to suppress itemChanged signal during programmatic table updates
        self._updating_table: bool = False

        # Currently selected optimizer for Section C display
        self._current_opt_key: str = "max_sharpe"

        # Debounce timer for quick refresh on weight changes
        self._refresh_timer = QTimer(self)
        self._refresh_timer.setSingleShot(True)
        self._refresh_timer.timeout.connect(self._quick_refresh)

        self._build_layout()
        self._set_analyze_enabled(True)

    # ── Layout construction ────────────────────────────────────────────────────

    def _build_layout(self) -> None:
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.addWidget(self._build_left_panel())
        splitter.addWidget(self._build_right_panel())
        splitter.setSizes([310, 1090])
        splitter.setHandleWidth(4)
        root.addWidget(splitter)

    def _build_left_panel(self) -> QWidget:
        """Section A — Portfolio Builder."""
        panel = QWidget()
        panel.setMinimumWidth(280)
        panel.setMaximumWidth(400)
        panel.setStyleSheet(f"background-color: {BG_PRIMARY};")
        vbox = QVBoxLayout(panel)
        vbox.setContentsMargins(8, 8, 4, 8)
        vbox.setSpacing(6)

        gb = QGroupBox("Portfolio Builder")
        inner = QVBoxLayout(gb)
        inner.setSpacing(6)

        # ── Ticker input ─────────────────────────────────────────────────────
        row_add = QHBoxLayout()
        self._ticker_input = QLineEdit()
        self._ticker_input.setPlaceholderText("Ticker (e.g. AAPL)")
        self._ticker_input.setMaxLength(12)
        self._ticker_input.returnPressed.connect(self._on_add_ticker)
        self._btn_add = QPushButton("Add")
        self._btn_add.clicked.connect(self._on_add_ticker)
        row_add.addWidget(self._ticker_input, 1)
        row_add.addWidget(self._btn_add)
        inner.addLayout(row_add)

        # ── Weight table ─────────────────────────────────────────────────────
        self._weight_table = QTableWidget(0, 3)
        self._weight_table.setHorizontalHeaderLabels(["Ticker", "Name", "Weight %"])
        self._weight_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self._weight_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self._weight_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self._weight_table.verticalHeader().hide()
        self._weight_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._weight_table.setAlternatingRowColors(True)
        self._weight_table.setMinimumHeight(160)
        self._weight_table.cellChanged.connect(self._on_weight_changed)
        inner.addWidget(self._weight_table)

        # ── Total label ──────────────────────────────────────────────────────
        self._total_label = QLabel("Total: 0.00 %")
        self._total_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        self._total_label.setStyleSheet(f"font-size: 11px; color: {TEXT_SECONDARY};")
        inner.addWidget(self._total_label)

        # ── Action buttons ───────────────────────────────────────────────────
        btn_remove = QPushButton("Remove Selected")
        btn_remove.setProperty("secondary", "true")
        btn_remove.clicked.connect(self._on_remove_ticker)
        inner.addWidget(btn_remove)

        row_w = QHBoxLayout()
        btn_eq = QPushButton("Equal Weight")
        btn_eq.setProperty("secondary", "true")
        btn_eq.clicked.connect(self._on_equal_weight)
        btn_norm = QPushButton("Normalize")
        btn_norm.setProperty("secondary", "true")
        btn_norm.clicked.connect(self._on_normalize)
        row_w.addWidget(btn_eq)
        row_w.addWidget(btn_norm)
        inner.addLayout(row_w)

        row_io = QHBoxLayout()
        btn_save = QPushButton("Save")
        btn_save.setProperty("secondary", "true")
        btn_save.clicked.connect(self._on_save_portfolio)
        btn_load = QPushButton("Load")
        btn_load.setProperty("secondary", "true")
        btn_load.clicked.connect(self._on_load_portfolio)
        row_io.addWidget(btn_save)
        row_io.addWidget(btn_load)
        inner.addLayout(row_io)

        # ── Benchmark / period ───────────────────────────────────────────────
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"color: {BORDER};")
        inner.addWidget(sep)

        grid = QGridLayout()
        grid.setColumnStretch(1, 1)
        grid.addWidget(QLabel("Benchmark:"), 0, 0)
        self._benchmark_combo = QComboBox()
        self._benchmark_combo.addItems(BENCHMARKS)
        self._benchmark_combo.setCurrentText(DEFAULT_BENCHMARK)
        grid.addWidget(self._benchmark_combo, 0, 1)

        grid.addWidget(QLabel("Period:"), 1, 0)
        self._period_combo = QComboBox()
        self._period_combo.addItems(ANALYSIS_PERIODS)
        self._period_combo.setCurrentText(DEFAULT_PERIOD)
        grid.addWidget(self._period_combo, 1, 1)
        inner.addLayout(grid)

        # ── Analyze button ───────────────────────────────────────────────────
        self._btn_analyze = QPushButton("Analyze Portfolio")
        self._btn_analyze.setMinimumHeight(34)
        self._btn_analyze.clicked.connect(self._on_analyze)
        inner.addWidget(self._btn_analyze)

        vbox.addWidget(gb)
        vbox.addStretch()
        return panel

    def _build_right_panel(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        vbox = QVBoxLayout(container)
        vbox.setContentsMargins(6, 6, 6, 6)
        vbox.setSpacing(8)
        vbox.addWidget(self._build_metrics_section())
        vbox.addWidget(self._build_optimization_section())
        vbox.addWidget(self._build_charts_section())
        vbox.addStretch()

        scroll.setWidget(container)
        return scroll

    # ── Section B: Metrics ─────────────────────────────────────────────────────

    def _build_metrics_section(self) -> QGroupBox:
        gb = QGroupBox("Portfolio Metrics")
        hbox = QHBoxLayout(gb)
        hbox.setSpacing(8)

        # Return group
        ret_frame, self._cards_return = self._make_card_group("Return", [
            ("Expected Return (ann.)", "card_exp_ret"),
            ("CAGR",                   "card_cagr"),
            ("CAPM Expected Return",   "card_capm"),
        ])

        # Risk group
        risk_frame, self._cards_risk = self._make_card_group("Risk", [
            ("Volatility (ann.)", "card_vol"),
            ("Sharpe Ratio",      "card_sharpe"),
            ("Beta",              "card_beta"),
        ])

        # Diversification group
        div_frame, self._cards_div = self._make_card_group("Diversification", [
            ("# Assets",          "card_n"),
            ("Avg Correlation",   "card_corr"),
            ("Div. Score (0–1)",  "card_div"),
            ("Health Score",      "card_health"),
        ])

        hbox.addWidget(ret_frame, 1)
        hbox.addWidget(risk_frame, 2)
        hbox.addWidget(div_frame, 1)
        return gb

    def _make_card_group(
        self,
        title: str,
        items: list[tuple[str, str]],
    ) -> tuple[QFrame, dict[str, MetricCard]]:
        frame = QFrame()
        frame.setStyleSheet(
            f"QFrame {{ background: {BG_TERTIARY}; border-radius: 6px;"
            f"border: 1px solid {BORDER}; }}"
        )
        vbox = QVBoxLayout(frame)
        vbox.setContentsMargins(6, 4, 6, 6)
        vbox.setSpacing(4)

        lbl = QLabel(title.upper())
        lbl.setStyleSheet(
            f"font-size: 10px; font-weight: bold; color: {ACCENT};"
            f" background: transparent; border: none;"
        )
        vbox.addWidget(lbl)

        cards: dict[str, MetricCard] = {}
        for label, key in items:
            card = MetricCard(label, frame)
            vbox.addWidget(card)
            cards[key] = card

        vbox.addStretch()
        return frame, cards

    def _all_cards(self) -> dict[str, MetricCard]:
        return {**self._cards_return, **self._cards_risk, **self._cards_div}

    # ── Section C: Optimization ────────────────────────────────────────────────

    def _build_optimization_section(self) -> QGroupBox:
        gb = QGroupBox("Portfolio Optimization")
        vbox = QVBoxLayout(gb)
        vbox.setSpacing(6)

        # Optimizer selector buttons
        btn_row = QHBoxLayout()
        self._opt_buttons: dict[str, QPushButton] = {}
        for key, label in _OPT_LABELS.items():
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked, k=key: self._select_optimizer(k))
            self._opt_buttons[key] = btn
            btn_row.addWidget(btn)
        btn_row.addStretch()
        vbox.addLayout(btn_row)
        self._opt_buttons["max_sharpe"].setChecked(True)

        # Comparison tables side by side
        table_splitter = QSplitter(Qt.Orientation.Horizontal)

        # Weight comparison table
        self._opt_weight_table = QTableWidget(0, 3)
        self._opt_weight_table.setHorizontalHeaderLabels(["Ticker", "Current", "Optimized"])
        self._opt_weight_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self._opt_weight_table.verticalHeader().hide()
        self._opt_weight_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._opt_weight_table.setMinimumHeight(160)

        # Metric comparison table
        self._opt_metric_table = QTableWidget(0, 3)
        self._opt_metric_table.setHorizontalHeaderLabels(["Metric", "Current", "Optimized"])
        self._opt_metric_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self._opt_metric_table.verticalHeader().hide()
        self._opt_metric_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._opt_metric_table.setMinimumHeight(160)

        table_splitter.addWidget(self._opt_weight_table)
        table_splitter.addWidget(self._opt_metric_table)
        vbox.addWidget(table_splitter)

        # Action buttons
        action_row = QHBoxLayout()
        btn_preview = QPushButton("Preview Results")
        btn_preview.setProperty("secondary", "true")
        btn_preview.clicked.connect(self._on_preview_optimized)
        btn_apply = QPushButton("Apply Optimized Weights")
        btn_apply.clicked.connect(self._on_apply_optimized)
        action_row.addWidget(btn_preview)
        action_row.addWidget(btn_apply)
        action_row.addStretch()
        vbox.addLayout(action_row)

        return gb

    # ── Section D: Charts ──────────────────────────────────────────────────────

    def _build_charts_section(self) -> QGroupBox:
        gb = QGroupBox("Visualizations")
        grid = QGridLayout(gb)
        grid.setSpacing(8)

        # Row 0: Growth (col 0) + Frontier (col 1)
        self._canvas_growth   = ChartCanvas(figsize=(8.0, 5.0))
        self._canvas_frontier = ChartCanvas(figsize=(5.5, 5.0))
        self._canvas_growth.setMinimumHeight(400)
        self._canvas_frontier.setMinimumHeight(400)
        grid.addWidget(self._canvas_growth,   0, 0)
        grid.addWidget(self._canvas_frontier, 0, 1)

        # Row 1: Drawdown (col 0) + Rolling Vol (col 1)
        self._canvas_drawdown = ChartCanvas(figsize=(5.5, 4.5))
        self._canvas_roll_vol = ChartCanvas(figsize=(5.5, 4.5))
        self._canvas_drawdown.setMinimumHeight(340)
        self._canvas_roll_vol.setMinimumHeight(340)
        grid.addWidget(self._canvas_drawdown, 1, 0)
        grid.addWidget(self._canvas_roll_vol, 1, 1)

        # Row 2: Risk contribution — 2 sub-plots in one canvas
        self._canvas_risk_contrib = ChartCanvas(nrows=1, ncols=2, figsize=(11.0, 4.0))
        self._canvas_risk_contrib.setMinimumHeight(320)
        grid.addWidget(self._canvas_risk_contrib, 2, 0, 1, 2)

        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)

        self._draw_all_placeholders()
        return gb

    # ── Section A slots ────────────────────────────────────────────────────────

    def _on_add_ticker(self) -> None:
        raw = self._ticker_input.text().strip().upper()
        if not raw:
            return
        try:
            validate_ticker(raw)
        except ValueError as exc:
            QMessageBox.warning(self, "Invalid ticker", str(exc))
            return

        if raw in self._portfolio.tickers:
            QMessageBox.information(self, "Already added", f"{raw} is already in the portfolio.")
            return

        n = len(self._portfolio.assets) + 1
        asset = Asset(ticker=raw, weight=round(1.0 / n, 6))
        self._portfolio.assets.append(asset)
        self._ticker_input.clear()
        self._update_weight_table_from_portfolio()
        self._schedule_quick_refresh()

    def _on_remove_ticker(self) -> None:
        rows = {idx.row() for idx in self._weight_table.selectedIndexes()}
        if not rows:
            return
        tickers_to_remove = set()
        for r in rows:
            item = self._weight_table.item(r, 0)
            if item:
                tickers_to_remove.add(item.text())
        self._portfolio.assets = [
            a for a in self._portfolio.assets if a.ticker not in tickers_to_remove
        ]
        self._update_weight_table_from_portfolio()
        self._schedule_quick_refresh()

    @Slot(int, int)
    def _on_weight_changed(self, row: int, col: int) -> None:
        if self._updating_table or col != 2:
            return
        item = self._weight_table.item(row, col)
        if item is None:
            return
        try:
            val = float(item.text().strip().rstrip("%")) / 100.0
            val = max(0.0, min(1.0, val))
        except ValueError:
            return

        ticker_item = self._weight_table.item(row, 0)
        if ticker_item is None:
            return
        ticker = ticker_item.text()
        for asset in self._portfolio.assets:
            if asset.ticker == ticker:
                asset.weight = val
                break

        self._update_total_label()
        self._schedule_quick_refresh()

    def _on_equal_weight(self) -> None:
        if not self._portfolio.assets:
            return
        self._portfolio.apply_equal_weight()
        self._update_weight_table_from_portfolio()
        self._schedule_quick_refresh()

    def _on_normalize(self) -> None:
        if not self._portfolio.assets:
            return
        try:
            self._portfolio.normalize_weights()
        except ValueError as exc:
            QMessageBox.warning(self, "Cannot normalize", str(exc))
            return
        self._update_weight_table_from_portfolio()
        self._schedule_quick_refresh()

    def _on_save_portfolio(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Portfolio", str(Path.home()), "JSON files (*.json)"
        )
        if not path:
            return
        try:
            self._sync_portfolio_from_ui()
            save_portfolio(self._portfolio, self._settings, Path(path))
            self.status_message.emit(f"Portfolio saved to {path}")
        except Exception as exc:
            QMessageBox.critical(self, "Save failed", str(exc))

    def _on_load_portfolio(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Load Portfolio", str(Path.home()), "JSON files (*.json)"
        )
        if not path:
            return
        try:
            portfolio, settings = load_portfolio(Path(path))
            self._portfolio = portfolio
            self._settings  = settings
            self._benchmark_combo.setCurrentText(portfolio.benchmark)
            self._period_combo.setCurrentText(portfolio.period)
            self._update_weight_table_from_portfolio()
            self.status_message.emit(f"Portfolio loaded from {path}")
        except Exception as exc:
            QMessageBox.critical(self, "Load failed", str(exc))

    def _on_analyze(self) -> None:
        if not self._portfolio.assets:
            QMessageBox.information(self, "Empty portfolio", "Add at least one ticker first.")
            return
        if self._thread and self._thread.isRunning():
            return  # already running

        self._sync_portfolio_from_ui()
        self._run_full_analysis(self._portfolio, self._settings)

    # ── Analysis management ────────────────────────────────────────────────────

    def _sync_portfolio_from_ui(self) -> None:
        """Update portfolio benchmark/period from UI controls."""
        try:
            self._portfolio.benchmark = self._benchmark_combo.currentText()
        except ValueError:
            pass
        try:
            self._portfolio.period = self._period_combo.currentText()
        except ValueError:
            pass

    def _run_full_analysis(
        self, portfolio: Portfolio, settings: AnalysisSettings
    ) -> None:
        self._set_analyze_enabled(False)
        self.status_message.emit("Starting analysis…")

        self._thread = QThread()
        self._worker = AnalysisWorker(portfolio, settings)
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_analysis_complete)
        self._worker.finished.connect(self._thread.quit)
        self._worker.error.connect(self._on_analysis_error)
        self._worker.error.connect(self._thread.quit)
        self._worker.progress.connect(self.status_message)
        self._thread.finished.connect(lambda: self._set_analyze_enabled(True))

        self._thread.start()

    @Slot(object)
    def _on_analysis_complete(self, result: AnalysisResult) -> None:
        self._result = result
        self._last_prices       = result.prices.copy()
        self._last_bench_prices = result.benchmark_prices.copy()

        # Sync portfolio object weights to whatever the worker resolved
        resolved = result.optimization.get("current")
        if resolved and resolved.weights:
            for asset in self._portfolio.assets:
                if asset.ticker in resolved.weights:
                    asset.weight = resolved.weights[asset.ticker]
            self._update_weight_table_from_portfolio()

        self._update_metric_cards(result)
        self._select_optimizer(self._current_opt_key)
        self._redraw_charts()
        self.analysis_ready.emit(result)   # propagate to other tabs

        warnings = result.warnings + (
            [f"Failed tickers: {', '.join(result.failed_tickers)}"]
            if result.failed_tickers else []
        )
        msg = "Analysis complete."
        if warnings:
            msg += f"  ⚠ {warnings[0]}"
        self.status_message.emit(msg)

    @Slot(str)
    def _on_analysis_error(self, msg: str) -> None:
        self.status_message.emit(f"Analysis failed: {msg}")
        QMessageBox.critical(self, "Analysis failed", msg)

    def _schedule_quick_refresh(self) -> None:
        self._refresh_timer.start(400)

    @Slot()
    def _quick_refresh(self) -> None:
        """Recompute analytics from cached prices — no network call."""
        if self._last_prices is None or self._last_prices.empty:
            return
        if not self._portfolio.assets:
            return

        prices = self._last_prices
        bench_prices = self._last_bench_prices

        weights: dict[str, float] = {
            a.ticker: a.weight
            for a in self._portfolio.assets
            if a.ticker in prices.columns
        }
        if not weights:
            return
        w_total = sum(weights.values())
        if w_total <= 0:
            return
        if abs(w_total - 1.0) > 1e-6:
            weights = {t: w / w_total for t, w in weights.items()}

        tickers_ok = [t for t in self._portfolio.tickers if t in prices.columns]
        prices     = prices[tickers_ok]

        rets = prices.pct_change().dropna()
        bench_rets_raw = bench_prices.pct_change().dropna()
        common = rets.index.intersection(bench_rets_raw.index)
        rets_a = rets.loc[common]
        bench_rets_a = bench_rets_raw.loc[common]

        port_rets = portfolio_daily_returns(prices, weights).loc[common]
        ann_ret   = annualized_return(port_rets)
        port_val  = portfolio_value_series(prices, weights)
        port_cagr = cagr(port_val)
        port_vol  = portfolio_volatility(rets_a, weights)
        p_sharpe  = sharpe_ratio(ann_ret, port_vol, self._settings.risk_free_rate)
        p_sortino = sortino_ratio(port_rets, ann_ret, self._settings.risk_free_rate)
        p_beta    = portfolio_beta(port_rets, bench_rets_a)
        capm_ret  = capm_expected_return(
            p_beta, self._settings.risk_free_rate, self._settings.market_expected_return,
        )
        mdd   = max_drawdown(port_val)
        var95 = historical_var(port_rets, 0.95)
        var99 = historical_var(port_rets, 0.99)
        cvar  = historical_cvar(port_rets, 0.95)
        avg_c = average_correlation(rets_a)
        div_s = diversification_score(rets_a, weights)

        current_opt = OptimizationResult(
            method="current",
            weights=weights,
            expected_return=ann_ret,
            volatility=port_vol,
            sharpe=p_sharpe,
            beta=p_beta,
            var_95=var95,
            max_drawdown=mdd,
        )

        risk_c = risk_contributions(rets_a, weights)
        ann_rets_per = {t: annualized_return(rets_a[t]) for t in tickers_ok}
        ret_c = return_contributions(ann_rets_per, weights)

        asset_metrics: dict[str, AssetMetrics] = {}
        for ticker in tickers_ok:
            a_rets = rets_a[ticker]
            a_ann  = ann_rets_per[ticker]
            a_vol  = annualized_volatility(a_rets)
            asset_metrics[ticker] = AssetMetrics(
                ticker=ticker,
                weight=weights[ticker],
                cagr=cagr(prices[ticker]),
                annualized_return=a_ann,
                volatility=a_vol,
                sharpe=sharpe_ratio(a_ann, a_vol, self._settings.risk_free_rate),
                sortino=sortino_ratio(a_rets, a_ann, self._settings.risk_free_rate),
                beta=compute_beta(a_rets, bench_rets_a),
                max_drawdown=max_drawdown(prices[ticker]),
                var_95=historical_var(a_rets, 0.95),
                var_99=historical_var(a_rets, 0.99),
                cvar=historical_cvar(a_rets, 0.95),
                latest_price=float(prices[ticker].iloc[-1]),
                risk_contribution=risk_c.get(ticker, float("nan")),
                return_contribution=ret_c.get(ticker, float("nan")),
            )

        prev_result = self._result
        self._result = AnalysisResult(
            portfolio=self._portfolio,
            settings=self._settings,
            prices=prices,
            returns=rets_a,
            benchmark_prices=bench_prices,
            benchmark_returns=bench_rets_a,
            portfolio_return=ann_ret,
            portfolio_cagr=port_cagr,
            portfolio_expected_return_capm=capm_ret,
            portfolio_volatility=port_vol,
            sharpe_ratio=p_sharpe,
            sortino_ratio=p_sortino,
            beta=p_beta,
            max_drawdown=mdd,
            var_95=var95,
            var_99=var99,
            cvar=cvar,
            avg_correlation=avg_c,
            diversification_score=div_s,
            asset_metrics=asset_metrics,
            optimization={
                "current": current_opt,
                **(prev_result.optimization if prev_result else {}),
            },
            portfolio_value_series=port_val,
            benchmark_value_series=benchmark_value_series(bench_prices),
            drawdown_series=drawdown_series(port_val),
            rolling_volatility_series=rolling_volatility(port_rets, window=252),
            frontier_risk=prev_result.frontier_risk if prev_result else [],
            frontier_return=prev_result.frontier_return if prev_result else [],
        )

        self._update_metric_cards(self._result)
        self._redraw_charts()

    # ── Section B: metric card updates ────────────────────────────────────────

    def _update_metric_cards(self, result: AnalysisResult) -> None:
        cards = self._all_cards()

        # Return group
        cards["card_exp_ret"].set_value(
            _fmt_pct(result.portfolio_return),
            _color_return(result.portfolio_return),
        )
        cards["card_cagr"].set_value(
            _fmt_pct(result.portfolio_cagr),
            _color_return(result.portfolio_cagr),
        )
        cards["card_capm"].set_value(
            _fmt_pct(result.portfolio_expected_return_capm),
            _color_return(result.portfolio_expected_return_capm),
        )

        # Risk group
        cards["card_vol"].set_value(
            _fmt_pct(result.portfolio_volatility),
            _color_risk(result.portfolio_volatility),
        )
        cards["card_sharpe"].set_value(
            _fmt_num(result.sharpe_ratio),
            SUCCESS if result.sharpe_ratio > 1.0 else
            WARNING if result.sharpe_ratio > 0.5 else DANGER,
        )
        cards["card_beta"].set_value(
            _fmt_num(result.beta),
            SUCCESS if 0.8 <= result.beta <= 1.2 else WARNING,
        )

        # Diversification group
        n = len(result.portfolio.assets) if result.portfolio else 0
        cards["card_n"].set_value(str(n))
        cards["card_corr"].set_value(
            _fmt_num(result.avg_correlation),
            SUCCESS if result.avg_correlation < 0.5 else
            WARNING if result.avg_correlation < 0.75 else DANGER,
        )
        cards["card_div"].set_value(
            _fmt_num(result.diversification_score),
            SUCCESS if result.diversification_score > 0.3 else
            WARNING if result.diversification_score > 0.1 else DANGER,
        )
        weights_dict = {
            t: m.weight for t, m in result.asset_metrics.items()
        }
        hs, _ = portfolio_health_score(
            sharpe=result.sharpe_ratio,
            max_drawdown=result.max_drawdown,
            volatility=result.portfolio_volatility,
            diversification_score=result.diversification_score,
            weights=weights_dict,
        )
        cards["card_health"].set_value(
            f"{hs:.0f} / 100",
            SUCCESS if hs >= 60 else WARNING if hs >= 35 else DANGER,
        )

    # ── Section C: optimizer selection & tables ────────────────────────────────

    def _select_optimizer(self, key: str) -> None:
        self._current_opt_key = key
        for k, btn in self._opt_buttons.items():
            btn.setChecked(k == key)
            btn.setStyleSheet(
                f"QPushButton {{ background-color: {ACCENT}; }}"
                if k == key else ""
            )
        self._update_optimization_tables()

    def _update_optimization_tables(self) -> None:
        if self._result is None:
            return

        opt = self._result.optimization.get(self._current_opt_key)
        current = self._result.optimization.get("current")
        if opt is None or current is None:
            return

        # Weight comparison
        tickers = (
            list(current.weights.keys()) or
            list(self._result.prices.columns)
        )
        self._opt_weight_table.blockSignals(True)
        self._opt_weight_table.setRowCount(len(tickers))
        for r, ticker in enumerate(tickers):
            cw = current.weights.get(ticker, 0.0)
            ow = opt.weights.get(ticker, 0.0)
            self._opt_weight_table.setItem(r, 0, QTableWidgetItem(ticker))
            self._opt_weight_table.setItem(r, 1, QTableWidgetItem(f"{cw * 100:.2f} %"))
            cell = QTableWidgetItem(f"{ow * 100:.2f} %")
            # Colour significant changes
            diff = ow - cw
            if abs(diff) > 0.05:
                cell.setForeground(
                    __import__("PySide6.QtGui", fromlist=["QColor"]).QColor(
                        SUCCESS if diff > 0 else DANGER
                    )
                )
            self._opt_weight_table.setItem(r, 2, cell)
        self._opt_weight_table.blockSignals(False)

        # Metric comparison
        metrics = [
            ("Return",     _fmt_pct(current.expected_return), _fmt_pct(opt.expected_return)),
            ("Volatility", _fmt_pct(current.volatility),      _fmt_pct(opt.volatility)),
            ("Sharpe",     _fmt_num(current.sharpe),          _fmt_num(opt.sharpe)),
            ("Beta",       _fmt_num(current.beta),            _fmt_num(opt.beta)),
            ("VaR 95 %",   _fmt_pct(current.var_95),          _fmt_pct(opt.var_95)),
            ("Max DD",     _fmt_pct(current.max_drawdown),    _fmt_pct(opt.max_drawdown)),
        ]
        self._opt_metric_table.setRowCount(len(metrics))
        for r, (name, c_val, o_val) in enumerate(metrics):
            self._opt_metric_table.setItem(r, 0, QTableWidgetItem(name))
            self._opt_metric_table.setItem(r, 1, QTableWidgetItem(c_val))
            self._opt_metric_table.setItem(r, 2, QTableWidgetItem(o_val))

    def _on_preview_optimized(self) -> None:
        if self._result is None:
            self.status_message.emit("Run an analysis first.")
            return
        opt = self._result.optimization.get(self._current_opt_key)
        if opt is None or not opt.weights:
            self.status_message.emit(f"{_OPT_LABELS[self._current_opt_key]} optimization not available.")
            return

        lines = [f"<b>{_OPT_LABELS[self._current_opt_key]} — Optimized Portfolio</b><br>"]
        for ticker, w in sorted(opt.weights.items(), key=lambda x: -x[1]):
            lines.append(f"{ticker}: {w * 100:.2f} %<br>")
        lines.append(f"<br>Return: {_fmt_pct(opt.expected_return)}<br>")
        lines.append(f"Volatility: {_fmt_pct(opt.volatility)}<br>")
        lines.append(f"Sharpe: {_fmt_num(opt.sharpe)}<br>")

        box = QMessageBox(self)
        box.setWindowTitle("Optimization Preview")
        box.setTextFormat(Qt.TextFormat.RichText)
        box.setText("".join(lines))
        box.exec()

    def _on_apply_optimized(self) -> None:
        if self._result is None:
            self.status_message.emit("Run an analysis first.")
            return
        opt = self._result.optimization.get(self._current_opt_key)
        if opt is None or not opt.weights:
            self.status_message.emit("No optimization result to apply.")
            return

        for asset in self._portfolio.assets:
            if asset.ticker in opt.weights:
                asset.weight = opt.weights[asset.ticker]

        self._update_weight_table_from_portfolio()
        self.status_message.emit(
            f"Applied {_OPT_LABELS[self._current_opt_key]} weights."
        )
        self._schedule_quick_refresh()

    # ── Section D: chart drawing ───────────────────────────────────────────────

    def _redraw_charts(self) -> None:
        if self._result is None:
            return
        r = self._result
        bench_label = self._portfolio.benchmark if self._portfolio else "Benchmark"
        port_label  = self._portfolio.name      if self._portfolio else "Portfolio"

        # Growth
        c = self._canvas_growth
        c.ax.clear()
        try:
            draw_growth_chart(
                c.ax, r.portfolio_value_series, r.benchmark_value_series,
                portfolio_label=port_label, benchmark_label=bench_label,
            )
        except Exception as exc:
            self._draw_error(c.ax, str(exc))
        c.refresh()

        # Frontier
        c = self._canvas_frontier
        c.ax.clear()
        try:
            draw_frontier_chart(
                c.ax,
                r.frontier_risk, r.frontier_return,
                current=r.optimization.get("current"),
                max_sharpe_result=r.optimization.get("max_sharpe"),
                min_variance_result=r.optimization.get("min_variance"),
                black_litterman_result=r.optimization.get("black_litterman"),
            )
        except Exception as exc:
            self._draw_error(c.ax, str(exc))
        c.refresh()

        # Drawdown
        c = self._canvas_drawdown
        c.ax.clear()
        try:
            draw_drawdown_chart(c.ax, r.drawdown_series)
        except Exception as exc:
            self._draw_error(c.ax, str(exc))
        c.refresh()

        # Rolling vol
        c = self._canvas_roll_vol
        c.ax.clear()
        try:
            draw_rolling_vol_chart(c.ax, r.rolling_volatility_series)
        except Exception as exc:
            self._draw_error(c.ax, str(exc))
        c.refresh()

        # Risk + Return contribution
        c = self._canvas_risk_contrib
        ax_risk, ax_ret = c.axes[0], c.axes[1]
        ax_risk.clear()
        ax_ret.clear()
        try:
            rc = {t: m.risk_contribution for t, m in r.asset_metrics.items()
                  if not np.isnan(m.risk_contribution)}
            if rc:
                draw_risk_contribution_chart(ax_risk, rc)
        except Exception as exc:
            self._draw_error(ax_risk, str(exc))
        try:
            ret_c = {t: m.return_contribution for t, m in r.asset_metrics.items()
                     if not np.isnan(m.return_contribution)}
            if ret_c:
                draw_return_contribution_chart(ax_ret, ret_c)
        except Exception as exc:
            self._draw_error(ax_ret, str(exc))
        c.refresh()

    def _draw_all_placeholders(self) -> None:
        for canvas in (
            self._canvas_growth, self._canvas_frontier,
            self._canvas_drawdown, self._canvas_roll_vol,
        ):
            self._draw_placeholder(canvas.ax, "Run analysis to populate chart")
            canvas.refresh()

        for ax in self._canvas_risk_contrib.axes:
            self._draw_placeholder(ax, "Run analysis")
        self._canvas_risk_contrib.refresh()

    def _draw_placeholder(self, ax, msg: str) -> None:
        ax.clear()
        ax.text(
            0.5, 0.5, msg,
            transform=ax.transAxes,
            ha="center", va="center",
            color=TEXT_SECONDARY, fontsize=9,
        )
        ax.set_facecolor(BG_PRIMARY)
        ax.set_xticks([])
        ax.set_yticks([])

    def _draw_error(self, ax, msg: str) -> None:
        ax.text(
            0.5, 0.5, f"Chart error:\n{msg}",
            transform=ax.transAxes,
            ha="center", va="center",
            color=DANGER, fontsize=8,
        )

    # ── Weight table helpers ───────────────────────────────────────────────────

    def _update_weight_table_from_portfolio(self) -> None:
        self._updating_table = True
        try:
            assets = self._portfolio.assets
            self._weight_table.setRowCount(len(assets))
            for r, asset in enumerate(assets):
                ticker_item = QTableWidgetItem(asset.ticker)
                ticker_item.setFlags(ticker_item.flags() & ~Qt.ItemFlag.ItemIsEditable)

                # Asset name (filled after analysis if available)
                name = ""
                if self._result and asset.ticker in self._result.asset_metrics:
                    name = asset.ticker  # placeholder; full name lookup skipped
                name_item = QTableWidgetItem(name)
                name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)

                weight_item = QTableWidgetItem(f"{asset.weight * 100:.4f}")

                self._weight_table.setItem(r, 0, ticker_item)
                self._weight_table.setItem(r, 1, name_item)
                self._weight_table.setItem(r, 2, weight_item)
        finally:
            self._updating_table = False
        self._update_total_label()

    def _update_total_label(self) -> None:
        total = sum(a.weight for a in self._portfolio.assets)
        pct   = total * 100.0
        if abs(pct - 100.0) < 0.5:
            color = SUCCESS
            suffix = ""
        elif pct > 100.5:
            color = DANGER
            suffix = " (exceeds 100 %)"
        else:
            color = WARNING
            suffix = " (< 100 %)"
        self._total_label.setText(f"Total: {pct:.2f} %{suffix}")
        self._total_label.setStyleSheet(f"font-size: 11px; color: {color};")

    def _set_analyze_enabled(self, enabled: bool) -> None:
        self._btn_analyze.setEnabled(enabled)
        self._btn_analyze.setText(
            "Analyze Portfolio" if enabled else "Analyzing…"
        )
