"""Drawdown chart — historical peak-to-trough decline over time."""

from __future__ import annotations

import matplotlib.axes
import matplotlib.ticker as mticker
import pandas as pd

from charts.style import (
    DRAWDOWN_COLOR,
    TEXT,
    TEXT_DIM,
    _apply_dark_axes,
    pct_formatter,
)


def draw_drawdown_chart(
    ax: matplotlib.axes.Axes,
    drawdown: pd.Series,
) -> None:
    """Draw the historical drawdown series as a filled area chart on *ax*.

    The worst drawdown is highlighted with a horizontal dashed line and
    annotated with its magnitude.

    Args:
        ax:       Matplotlib Axes to draw on.
        drawdown: Drawdown time series in [0, 1] (positive = loss fraction),
                  as produced by analytics.risk.drawdown_series().
    """
    ax.clear()

    # Invert for conventional presentation (drawdowns shown as negatives)
    dd = -drawdown

    ax.fill_between(
        dd.index,
        dd.values,
        0,
        color=DRAWDOWN_COLOR,
        alpha=0.55,
        zorder=2,
    )
    ax.plot(
        dd.index,
        dd.values,
        color=DRAWDOWN_COLOR,
        linewidth=1.2,
        zorder=3,
    )

    # Highlight the maximum drawdown
    if len(dd) > 0:
        mdd_val = float(dd.min())
        mdd_idx = dd.idxmin()
        ax.axhline(
            mdd_val,
            color=DRAWDOWN_COLOR,
            linewidth=0.8,
            linestyle="--",
            alpha=0.6,
            zorder=1,
        )
        ax.annotate(
            f"Max: {abs(mdd_val) * 100:.1f} %",
            xy=(mdd_idx, mdd_val),
            xytext=(8, -2),
            textcoords="offset points",
            color=DRAWDOWN_COLOR,
            fontsize=8,
            fontweight="bold",
        )

    ax.axhline(0, color=TEXT_DIM, linewidth=0.6, zorder=1)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(pct_formatter))
    ax.set_ylabel("Drawdown", fontsize=9)
    ax.set_title("Historical Drawdown", fontsize=10, color=TEXT)

    _apply_dark_axes(ax)
    ax.figure.autofmt_xdate(rotation=30, ha="right")
