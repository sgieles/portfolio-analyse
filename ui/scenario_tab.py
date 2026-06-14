"""Tab 4 — Scenario Analysis: beta-weighted stress tests."""

from __future__ import annotations

import math

import matplotlib.ticker as mticker
import numpy as np
from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import (
    QAbstractItemView, QGroupBox, QHBoxLayout, QHeaderView,
    QLabel, QSplitter, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget,
)

from analytics.scenario import run_scenario_analysis
from models.results import AnalysisResult
from ui.theme import ACCENT, DANGER, SUCCESS, TEXT_SECONDARY, WARNING
from ui.widgets.chart_canvas import ChartCanvas


def _pct(v: float, dec: int = 2) -> str:
    return "—" if math.isnan(v) else f"{v * 100:.{dec}f} %"


def _eur(v: float) -> str:
    return "—" if math.isnan(v) else f"€ {v:,.0f}"


class ScenarioTab(QWidget):
    """Stress-test four market scenarios and display impact table + chart."""

    _SCENARIO_COLORS = {
        "Bull Market":    "#4caf50",   # green
        "Mild Recession": "#ff9800",   # orange
        "Recession":      "#f44336",   # red
        "Severe Crash":   "#880e4f",   # dark red
    }

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._result: AnalysisResult | None = None
        self._build_layout()

    def _build_layout(self) -> None:
        vbox = QVBoxLayout(self)
        vbox.setContentsMargins(8, 8, 8, 8)

        self._status = QLabel("Run an analysis on the Portfolio Dashboard first.")
        self._status.setStyleSheet(f"color: {TEXT_SECONDARY};")
        vbox.addWidget(self._status)

        splitter = QSplitter(Qt.Orientation.Vertical)

        # ── Scenario results table ────────────────────────────────────────────
        table_gb = QGroupBox("Scenario Results")
        table_inner = QVBoxLayout(table_gb)

        headers = [
            "Scenario", "Market Return",
            "Portfolio Return", "New Value (from €10 000)",
            "Change vs Baseline", "Stressed Volatility",
        ]
        self._table = QTableWidget(0, len(headers))
        self._table.setHorizontalHeaderLabels(headers)
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._table.verticalHeader().hide()
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        table_inner.addWidget(self._table)
        splitter.addWidget(table_gb)

        # ── Impact chart ──────────────────────────────────────────────────────
        chart_gb = QGroupBox("Portfolio Value under Each Scenario")
        chart_inner = QVBoxLayout(chart_gb)
        self._canvas = ChartCanvas(figsize=(10.0, 3.5))
        self._draw_placeholder()
        chart_inner.addWidget(self._canvas)
        splitter.addWidget(chart_gb)

        splitter.setSizes([240, 280])
        vbox.addWidget(splitter)

    @Slot(object)
    def set_result(self, result: AnalysisResult) -> None:
        self._result = result
        self._compute_and_render()

    def _compute_and_render(self) -> None:
        r = self._result
        if r is None or r.returns.empty:
            self._status.setText("No data available. Run analysis first.")
            return

        self._status.setText(
            f"Stress-testing {len(r.asset_metrics)} assets via beta-weighted CAPM shocks."
        )

        start_val = float(r.portfolio_value_series.iloc[0]) if not r.portfolio_value_series.empty else 10_000.0
        try:
            start_val = float(r.portfolio_value_series.iloc[-1])  # current value
        except Exception:
            pass

        weights = {
            t: m.weight for t, m in r.asset_metrics.items()
        }
        try:
            scenarios = run_scenario_analysis(
                daily_returns=r.returns,
                weights=weights,
                benchmark_returns=r.benchmark_returns,
                start_value=start_val,
            )
        except Exception as exc:
            self._status.setText(f"Scenario computation failed: {exc}")
            return

        self._populate_table(scenarios, start_val)
        self._draw_chart(scenarios, start_val)

    def _populate_table(self, scenarios, start_val: float) -> None:
        self._table.setRowCount(len(scenarios))
        from PySide6.QtGui import QColor

        for row, sc in enumerate(scenarios):
            change = sc.new_value - start_val
            color_str = self._SCENARIO_COLORS.get(sc.name, TEXT_SECONDARY)
            qcolor = QColor(color_str)

            cells = [
                sc.name,
                _pct(sc.market_return),
                _pct(sc.portfolio_return),
                _eur(sc.new_value),
                f"{change:+,.0f} €  ({_pct(sc.portfolio_return)})",
                _pct(sc.stressed_vol),
            ]
            for col, text in enumerate(cells):
                item = QTableWidgetItem(text)
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                if col in (0, 2, 4):   # scenario name + return columns
                    item.setForeground(qcolor)
                self._table.setItem(row, col, item)

    def _draw_chart(self, scenarios, start_val: float) -> None:
        ax = self._canvas.ax
        ax.clear()

        from charts.style import _apply_dark_axes
        names  = [sc.name for sc in scenarios]
        values = [sc.new_value for sc in scenarios]
        colors = [self._SCENARIO_COLORS.get(n, ACCENT) for n in names]

        bars = ax.barh(names, values, color=colors, edgecolor="none", height=0.55)

        # Baseline reference
        ax.axvline(start_val, color=TEXT_SECONDARY, linewidth=1.0, linestyle="--",
                   label=f"Baseline €{start_val:,.0f}")

        for bar, val in zip(bars, values):
            ax.text(
                bar.get_width() + (start_val * 0.005),
                bar.get_y() + bar.get_height() / 2,
                f"€ {val:,.0f}",
                va="center", fontsize=8, color=TEXT_SECONDARY,
            )

        ax.set_xlabel("Portfolio Value (€)", fontsize=9)
        ax.set_title("Portfolio Value under Stress Scenarios", fontsize=10)
        ax.xaxis.set_major_formatter(
            mticker.FuncFormatter(lambda x, _: f"€{x:,.0f}")
        )
        ax.legend(fontsize=8)
        _apply_dark_axes(ax)
        self._canvas.refresh()

    def _draw_placeholder(self) -> None:
        ax = self._canvas.ax
        ax.text(0.5, 0.5, "Run analysis to see scenario impact",
                transform=ax.transAxes, ha="center", va="center",
                color=TEXT_SECONDARY, fontsize=9)
        ax.set_xticks([])
        ax.set_yticks([])
        self._canvas.refresh()
