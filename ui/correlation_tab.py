"""Tab 3 — Correlation Analysis: heatmaps + hierarchical clustering."""

from __future__ import annotations

import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import (
    QFrame, QGroupBox, QHBoxLayout, QLabel,
    QScrollArea, QSizePolicy, QVBoxLayout, QWidget,
)

from charts.correlation import (
    draw_correlation_clustermap,
    draw_correlation_heatmap,
    draw_covariance_heatmap,
)
from models.results import AnalysisResult
from ui.theme import TEXT_SECONDARY
from ui.widgets.chart_canvas import ChartCanvas


class CorrelationTab(QWidget):
    """Three correlation views: Pearson heatmap, covariance heatmap, clustermap."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._cluster_canvas: FigureCanvasQTAgg | None = None
        self._build_layout()

    def _build_layout(self) -> None:
        vbox = QVBoxLayout(self)
        vbox.setContentsMargins(8, 8, 8, 8)

        self._status = QLabel("Run an analysis on the Portfolio Dashboard first.")
        self._status.setStyleSheet(f"color: {TEXT_SECONDARY};")
        vbox.addWidget(self._status)

        # ── Row 1: correlation + covariance heatmaps ─────────────────────────
        row1 = QHBoxLayout()

        corr_gb = QGroupBox("Correlation Matrix")
        corr_inner = QVBoxLayout(corr_gb)
        self._corr_canvas = ChartCanvas(figsize=(5.5, 4.5))
        corr_inner.addWidget(self._corr_canvas)
        self._draw_placeholder(self._corr_canvas.ax, "Correlation heatmap")
        self._corr_canvas.refresh()

        cov_gb = QGroupBox("Covariance Matrix (annualised)")
        cov_inner = QVBoxLayout(cov_gb)
        self._cov_canvas = ChartCanvas(figsize=(5.5, 4.5))
        cov_inner.addWidget(self._cov_canvas)
        self._draw_placeholder(self._cov_canvas.ax, "Covariance heatmap")
        self._cov_canvas.refresh()

        row1.addWidget(corr_gb)
        row1.addWidget(cov_gb)
        vbox.addLayout(row1, stretch=1)

        # ── Row 2: correlation clustermap ────────────────────────────────────
        cluster_gb = QGroupBox("Correlation Clustering (hierarchical)")
        cluster_inner = QVBoxLayout(cluster_gb)

        # Container for the dynamically replaced clustermap canvas
        self._cluster_container = QWidget()
        self._cluster_vbox = QVBoxLayout(self._cluster_container)
        self._cluster_vbox.setContentsMargins(0, 0, 0, 0)

        placeholder_lbl = QLabel("Correlation clustering will appear here after analysis.")
        placeholder_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        placeholder_lbl.setStyleSheet(f"color: {TEXT_SECONDARY};")
        self._cluster_placeholder = placeholder_lbl
        self._cluster_vbox.addWidget(placeholder_lbl)

        cluster_inner.addWidget(self._cluster_container)
        vbox.addWidget(cluster_gb, stretch=1)

    @Slot(object)
    def set_result(self, result: AnalysisResult) -> None:
        if result.returns.empty:
            self._status.setText("No return data available.")
            return

        rets = result.returns
        n = rets.shape[1]
        self._status.setText(
            f"{n} assets · "
            f"Period: {result.portfolio.period if result.portfolio else '?'}"
        )

        # Correlation heatmap
        self._corr_canvas.ax.clear()
        draw_correlation_heatmap(self._corr_canvas.ax, rets, annot=n <= 10)
        self._corr_canvas.refresh()

        # Covariance heatmap
        self._cov_canvas.ax.clear()
        draw_covariance_heatmap(self._cov_canvas.ax, rets, annot=n <= 10)
        self._cov_canvas.refresh()

        # Clustermap (creates its own Figure)
        self._update_clustermap(rets)

    def _update_clustermap(self, returns) -> None:
        # Remove placeholder label
        if self._cluster_placeholder is not None:
            self._cluster_placeholder.setVisible(False)

        # Close and remove the old canvas
        if self._cluster_canvas is not None:
            self._cluster_vbox.removeWidget(self._cluster_canvas)
            self._cluster_canvas.close()
            plt.close(self._cluster_canvas.figure)
            self._cluster_canvas = None

        try:
            fig = draw_correlation_clustermap(returns, figsize=(11.0, 5.0))
            canvas = FigureCanvasQTAgg(fig)
            canvas.setSizePolicy(
                QSizePolicy.Policy.Expanding,
                QSizePolicy.Policy.Expanding,
            )
            self._cluster_vbox.addWidget(canvas)
            self._cluster_canvas = canvas
            canvas.draw()
        except Exception:
            lbl = QLabel("Clustering not available (need ≥ 2 assets).")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet(f"color: {TEXT_SECONDARY};")
            self._cluster_vbox.addWidget(lbl)

    def _draw_placeholder(self, ax, label: str) -> None:
        ax.text(
            0.5, 0.5, label,
            transform=ax.transAxes, ha="center", va="center",
            color=TEXT_SECONDARY, fontsize=9,
        )
        ax.set_xticks([])
        ax.set_yticks([])
