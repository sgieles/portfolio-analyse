"""ChartCanvas — FigureCanvasQTAgg wrapper for embedding matplotlib in Qt."""

from __future__ import annotations

import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from PySide6.QtWidgets import QSizePolicy, QWidget

from ui.theme import BG_SECONDARY


class ChartCanvas(FigureCanvasQTAgg):
    """Matplotlib figure embedded as a Qt widget.

    Args:
        nrows:   Number of subplot rows.
        ncols:   Number of subplot columns.
        figsize: Figure size in inches.
        parent:  Qt parent widget.
    """

    def __init__(
        self,
        nrows: int = 1,
        ncols: int = 1,
        figsize: tuple[float, float] = (5.0, 3.5),
        parent: QWidget | None = None,
    ) -> None:
        fig, raw_axes = plt.subplots(
            nrows, ncols, figsize=figsize, facecolor=BG_SECONDARY,
        )
        if nrows == 1 and ncols == 1:
            axes_list = [raw_axes]
        elif nrows == 1 or ncols == 1:
            axes_list = list(raw_axes)
        else:
            axes_list = [ax for row in raw_axes for ax in row]

        self.fig  = fig
        self.axes = axes_list
        self.ax   = axes_list[0]

        super().__init__(fig)
        self.setParent(parent)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )

    def refresh(self) -> None:
        """Tighten layout and redraw onto the Qt canvas."""
        try:
            self.fig.tight_layout(pad=1.5)
        except Exception:
            pass
        self.draw()
