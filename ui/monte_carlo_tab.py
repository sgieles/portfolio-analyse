"""Tab 5 — Monte Carlo Simulation."""

from __future__ import annotations

import traceback

import numpy as np
from PySide6.QtCore import QObject, QThread, Qt, Signal, Slot
from PySide6.QtWidgets import (
    QFrame, QGroupBox, QHBoxLayout, QLabel,
    QPushButton, QSpinBox, QSplitter, QVBoxLayout, QWidget,
)

from analytics.monte_carlo import MonteCarloResult, run_monte_carlo
from models.results import AnalysisResult
from ui.theme import (
    ACCENT, BG_SECONDARY, BG_TERTIARY, BORDER,
    DANGER, SUCCESS, TEXT_PRIMARY, TEXT_SECONDARY, WARNING,
)
from ui.widgets.chart_canvas import ChartCanvas
from ui.widgets.metric_card import MetricCard
from utils.constants import (
    GROWTH_START_VALUE,
    MONTE_CARLO_DEFAULT_HORIZON_YEARS,
    MONTE_CARLO_DEFAULT_SIMULATIONS,
)
from utils.logging import get_logger

log = get_logger(__name__)


# ── Monte Carlo worker ────────────────────────────────────────────────────────

class MCWorker(QObject):
    """Runs the simulation in a background thread."""

    finished = Signal(object)   # MonteCarloResult
    error    = Signal(str)

    def __init__(self, result: AnalysisResult, n_sims: int, horizon: int) -> None:
        super().__init__()
        self._result  = result
        self._n_sims  = n_sims
        self._horizon = horizon

    @Slot()
    def run(self) -> None:
        try:
            r = self._result
            weights = {t: m.weight for t, m in r.asset_metrics.items()}
            mc = run_monte_carlo(
                daily_returns=r.returns,
                weights=weights,
                n_simulations=self._n_sims,
                horizon_years=self._horizon,
                start_value=GROWTH_START_VALUE,
            )
            self.finished.emit(mc)
        except Exception as exc:
            log.error("Monte Carlo failed:\n%s", traceback.format_exc())
            self.error.emit(str(exc))


# ── Tab ───────────────────────────────────────────────────────────────────────

class MonteCarloTab(QWidget):
    """Monte Carlo simulation tab with configurable parameters."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._analysis_result: AnalysisResult | None = None
        self._mc_result: MonteCarloResult | None = None
        self._thread: QThread | None = None
        self._worker: MCWorker | None = None
        self._build_layout()

    def _build_layout(self) -> None:
        vbox = QVBoxLayout(self)
        vbox.setContentsMargins(8, 8, 8, 8)
        vbox.setSpacing(8)

        # ── Controls ──────────────────────────────────────────────────────────
        ctrl_gb = QGroupBox("Simulation Parameters")
        ctrl_row = QHBoxLayout(ctrl_gb)
        ctrl_row.setSpacing(16)

        ctrl_row.addWidget(QLabel("Simulations:"))
        self._spin_sims = QSpinBox()
        self._spin_sims.setRange(100, 10_000)
        self._spin_sims.setSingleStep(100)
        self._spin_sims.setValue(MONTE_CARLO_DEFAULT_SIMULATIONS)
        ctrl_row.addWidget(self._spin_sims)

        ctrl_row.addWidget(QLabel("Horizon (years):"))
        self._spin_horizon = QSpinBox()
        self._spin_horizon.setRange(1, 30)
        self._spin_horizon.setValue(MONTE_CARLO_DEFAULT_HORIZON_YEARS)
        ctrl_row.addWidget(self._spin_horizon)

        self._btn_run = QPushButton("Run Monte Carlo")
        self._btn_run.clicked.connect(self._on_run)
        ctrl_row.addWidget(self._btn_run)
        ctrl_row.addStretch()

        self._status = QLabel("Run an analysis on the Portfolio Dashboard first.")
        self._status.setStyleSheet(f"color: {TEXT_SECONDARY};")
        ctrl_row.addWidget(self._status)

        vbox.addWidget(ctrl_gb)

        # ── Statistics cards ──────────────────────────────────────────────────
        stats_gb = QGroupBox("Simulation Results")
        stats_row = QHBoxLayout(stats_gb)
        stats_row.setSpacing(6)
        self._card_median = MetricCard("Median ending value")
        self._card_mean   = MetricCard("Mean ending value")
        self._card_p5     = MetricCard("5th percentile")
        self._card_p95    = MetricCard("95th percentile")
        self._card_ploss  = MetricCard("Probability of loss")
        for card in (self._card_median, self._card_mean,
                     self._card_p5, self._card_p95, self._card_ploss):
            stats_row.addWidget(card)
        stats_row.addStretch()
        vbox.addWidget(stats_gb)

        # ── Charts ────────────────────────────────────────────────────────────
        chart_row = QHBoxLayout()

        paths_gb = QGroupBox("Simulation Paths")
        paths_inner = QVBoxLayout(paths_gb)
        self._canvas_paths = ChartCanvas(figsize=(7.5, 4.0))
        self._placeholder(self._canvas_paths.ax, "Paths chart")
        self._canvas_paths.refresh()
        paths_inner.addWidget(self._canvas_paths)

        dist_gb = QGroupBox("Ending-Value Distribution")
        dist_inner = QVBoxLayout(dist_gb)
        self._canvas_dist = ChartCanvas(figsize=(5.0, 4.0))
        self._placeholder(self._canvas_dist.ax, "Distribution chart")
        self._canvas_dist.refresh()
        dist_inner.addWidget(self._canvas_dist)

        chart_row.addWidget(paths_gb, 3)
        chart_row.addWidget(dist_gb, 2)
        vbox.addLayout(chart_row, stretch=1)

    # ── Slots ──────────────────────────────────────────────────────────────────

    @Slot(object)
    def set_result(self, result: AnalysisResult) -> None:
        self._analysis_result = result
        self._status.setText(
            f"Ready · {len(result.asset_metrics)} assets · "
            f"Click Run Monte Carlo to simulate."
        )

    def _on_run(self) -> None:
        if self._analysis_result is None:
            self._status.setText("Run a portfolio analysis first.")
            return
        if self._thread and self._thread.isRunning():
            return

        n_sims  = self._spin_sims.value()
        horizon = self._spin_horizon.value()

        self._btn_run.setEnabled(False)
        self._btn_run.setText("Simulating…")
        self._status.setText(
            f"Running {n_sims:,} simulations over {horizon} years…"
        )

        self._thread = QThread()
        self._worker = MCWorker(self._analysis_result, n_sims, horizon)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_mc_done)
        self._worker.finished.connect(self._thread.quit)
        self._worker.error.connect(self._on_mc_error)
        self._worker.error.connect(self._thread.quit)
        self._thread.finished.connect(self._reset_btn)
        self._thread.start()

    @Slot(object)
    def _on_mc_done(self, mc: MonteCarloResult) -> None:
        self._mc_result = mc
        self._update_cards(mc)
        self._draw_paths(mc)
        self._draw_distribution(mc)
        self._status.setText(
            f"Done · {mc.n_simulations:,} paths · {mc.horizon_years} yr horizon"
        )

    @Slot(str)
    def _on_mc_error(self, msg: str) -> None:
        self._status.setText(f"Error: {msg}")

    def _reset_btn(self) -> None:
        self._btn_run.setEnabled(True)
        self._btn_run.setText("Run Monte Carlo")

    # ── UI update ──────────────────────────────────────────────────────────────

    def _update_cards(self, mc: MonteCarloResult) -> None:
        def _eur(v: float) -> str:
            return f"€ {v:,.0f}"

        sv = mc.start_value
        self._card_median.set_value(
            _eur(mc.median),
            SUCCESS if mc.median >= sv else DANGER,
        )
        self._card_mean.set_value(
            _eur(mc.mean),
            SUCCESS if mc.mean >= sv else DANGER,
        )
        self._card_p5.set_value(
            _eur(mc.pct_5),
            SUCCESS if mc.pct_5 >= sv else DANGER,
        )
        self._card_p95.set_value(
            _eur(mc.pct_95),
            SUCCESS if mc.pct_95 >= sv else DANGER,
        )
        self._card_ploss.set_value(
            f"{mc.prob_loss * 100:.1f} %",
            DANGER if mc.prob_loss > 0.3 else WARNING if mc.prob_loss > 0.1 else SUCCESS,
        )

    def _draw_paths(self, mc: MonteCarloResult) -> None:
        from charts.style import _apply_dark_axes
        import matplotlib.ticker as mticker

        ax = self._canvas_paths.ax
        ax.clear()

        horizon_days = mc.median_path.shape[0]
        x = np.linspace(0, mc.horizon_years, horizon_days)   # time in years

        # Thin sample paths
        n_show = min(mc.sample_paths.shape[0], 100)
        for i in range(n_show):
            ax.plot(x, mc.sample_paths[i], color=TEXT_SECONDARY,
                    linewidth=0.3, alpha=0.25, zorder=1)

        # Confidence band
        ax.fill_between(
            x, mc.pct_5_path, mc.pct_95_path,
            color=ACCENT, alpha=0.15, label="5th–95th pct", zorder=2,
        )

        # Median path
        ax.plot(x, mc.median_path, color=ACCENT, linewidth=1.8,
                label="Median", zorder=3)

        # Breakeven line
        ax.axhline(mc.start_value, color=SUCCESS, linewidth=1.0,
                   linestyle="--", label=f"Breakeven €{mc.start_value:,.0f}", zorder=2)

        ax.set_xlabel("Time (years)", fontsize=9)
        ax.set_ylabel("Portfolio Value (€)", fontsize=9)
        ax.set_title(
            f"Monte Carlo Paths ({mc.n_simulations:,} simulations, {mc.horizon_years} yr)",
            fontsize=10,
        )
        ax.yaxis.set_major_formatter(
            mticker.FuncFormatter(lambda v, _: f"€{v:,.0f}")
        )
        ax.legend(fontsize=8)
        _apply_dark_axes(ax)
        self._canvas_paths.refresh()

    def _draw_distribution(self, mc: MonteCarloResult) -> None:
        from charts.style import _apply_dark_axes
        import matplotlib.ticker as mticker

        ax = self._canvas_dist.ax
        ax.clear()

        ev = mc.ending_values
        ax.hist(ev, bins=50, color=ACCENT, alpha=0.7, edgecolor="none")

        # Vertical markers
        ax.axvline(mc.start_value, color=SUCCESS, linewidth=1.2,
                   linestyle="--", label=f"Breakeven")
        ax.axvline(mc.median, color=TEXT_PRIMARY, linewidth=1.2,
                   linestyle="-", label=f"Median €{mc.median:,.0f}")
        ax.axvline(mc.pct_5, color=DANGER, linewidth=1.0,
                   linestyle=":", label=f"5th pct €{mc.pct_5:,.0f}")
        ax.axvline(mc.pct_95, color=SUCCESS, linewidth=1.0,
                   linestyle=":", label=f"95th pct €{mc.pct_95:,.0f}")

        ax.set_xlabel("Ending Value (€)", fontsize=9)
        ax.set_ylabel("Frequency", fontsize=9)
        ax.set_title("Distribution of Ending Values", fontsize=10)
        ax.xaxis.set_major_formatter(
            mticker.FuncFormatter(lambda v, _: f"€{v:,.0f}")
        )
        ax.legend(fontsize=7)
        _apply_dark_axes(ax)
        self._canvas_dist.refresh()

    def _placeholder(self, ax, label: str) -> None:
        ax.text(0.5, 0.5, label,
                transform=ax.transAxes, ha="center", va="center",
                color=TEXT_SECONDARY, fontsize=9)
        ax.set_xticks([])
        ax.set_yticks([])
