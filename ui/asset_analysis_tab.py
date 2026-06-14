"""Tab 2 — Asset Analysis: sortable per-asset metrics table."""

from __future__ import annotations

import math

from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import (
    QAbstractItemView, QGroupBox, QHeaderView, QLabel,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from models.results import AnalysisResult
from ui.theme import DANGER, SUCCESS, TEXT_SECONDARY, WARNING


class _NumericItem(QTableWidgetItem):
    """Table item that sorts numerically instead of lexicographically."""

    def __init__(self, display: str, sort_key: float) -> None:
        super().__init__(display)
        self._sort_key = sort_key

    def __lt__(self, other: QTableWidgetItem) -> bool:
        if isinstance(other, _NumericItem):
            return self._sort_key < other._sort_key
        return super().__lt__(other)


def _pct(v: float, dec: int = 2) -> str:
    return "—" if math.isnan(v) else f"{v * 100:.{dec}f} %"


def _num(v: float, dec: int = 2) -> str:
    return "—" if math.isnan(v) else f"{v:.{dec}f}"


def _price(v: float) -> str:
    return "—" if math.isnan(v) else f"€ {v:,.2f}"


class AssetAnalysisTab(QWidget):
    """Per-asset sortable metrics table. Populated by set_result()."""

    _HEADERS = [
        "Ticker", "Weight", "Latest Price",
        "CAGR", "Return (ann.)", "Volatility",
        "Sharpe", "Sortino", "Beta",
        "Max DD", "VaR 95 %", "VaR 99 %", "CVaR",
        "Risk Contrib.", "Return Contrib.",
    ]

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._result: AnalysisResult | None = None
        self._build_layout()

    def _build_layout(self) -> None:
        vbox = QVBoxLayout(self)
        vbox.setContentsMargins(8, 8, 8, 8)

        gb = QGroupBox("Asset Analysis")
        inner = QVBoxLayout(gb)

        self._status = QLabel("Run an analysis on the Portfolio Dashboard first.")
        self._status.setStyleSheet(f"color: {TEXT_SECONDARY};")
        inner.addWidget(self._status)

        self._table = QTableWidget(0, len(self._HEADERS))
        self._table.setHorizontalHeaderLabels(self._HEADERS)
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self._table.setColumnWidth(0, 80)
        self._table.verticalHeader().hide()
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        self._table.setSortingEnabled(True)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        inner.addWidget(self._table)

        vbox.addWidget(gb)

    @Slot(object)
    def set_result(self, result: AnalysisResult) -> None:
        self._result = result
        self._populate()

    def _populate(self) -> None:
        r = self._result
        if r is None or not r.asset_metrics:
            self._status.setText("No asset data available. Run analysis first.")
            return

        self._status.setText(
            f"Showing {len(r.asset_metrics)} assets · "
            f"Period: {r.portfolio.period if r.portfolio else '?'} · "
            f"Click any column header to sort."
        )

        metrics = list(r.asset_metrics.values())
        self._table.setSortingEnabled(False)
        self._table.setRowCount(len(metrics))

        for row, m in enumerate(metrics):
            def _text_item(text: str) -> QTableWidgetItem:
                item = QTableWidgetItem(text)
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                return item

            def _num_item(display: str, key: float) -> _NumericItem:
                item = _NumericItem(display, key if not math.isnan(key) else -1e18)
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                return item

            self._table.setItem(row, 0,  _text_item(m.ticker))
            self._table.setItem(row, 1,  _num_item(_pct(m.weight), m.weight))
            self._table.setItem(row, 2,  _num_item(_price(m.latest_price), m.latest_price))
            self._table.setItem(row, 3,  _num_item(_pct(m.cagr), m.cagr))
            self._table.setItem(row, 4,  _num_item(_pct(m.annualized_return), m.annualized_return))
            self._table.setItem(row, 5,  _num_item(_pct(m.volatility), m.volatility))
            self._table.setItem(row, 6,  _num_item(_num(m.sharpe), m.sharpe))
            self._table.setItem(row, 7,  _num_item(_num(m.sortino), m.sortino))
            self._table.setItem(row, 8,  _num_item(_num(m.beta), m.beta))
            self._table.setItem(row, 9,  _num_item(_pct(m.max_drawdown), m.max_drawdown))
            self._table.setItem(row, 10, _num_item(_pct(m.var_95), m.var_95))
            self._table.setItem(row, 11, _num_item(_pct(m.var_99), m.var_99))
            self._table.setItem(row, 12, _num_item(_pct(m.cvar), m.cvar))
            self._table.setItem(row, 13, _num_item(_pct(m.risk_contribution), m.risk_contribution))
            self._table.setItem(row, 14, _num_item(_pct(m.return_contribution), m.return_contribution))

            # Colour-code Sharpe
            sharpe_cell = self._table.item(row, 6)
            if not math.isnan(m.sharpe):
                color = SUCCESS if m.sharpe > 1.0 else WARNING if m.sharpe > 0.5 else DANGER
                from PySide6.QtGui import QColor
                sharpe_cell.setForeground(QColor(color))

        self._table.setSortingEnabled(True)
        self._table.sortItems(1, Qt.SortOrder.DescendingOrder)   # sort by weight desc
