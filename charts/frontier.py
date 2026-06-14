"""Efficient frontier chart with four marked portfolios."""

from __future__ import annotations

import matplotlib.axes
import matplotlib.ticker as mticker

from charts.style import (
    BL_COLOR,
    BENCHMARK_COLOR,
    CURRENT_COLOR,
    MAX_SHARPE_COLOR,
    MIN_VAR_COLOR,
    TEXT,
    TEXT_DIM,
    _apply_dark_axes,
    pct_formatter,
)
from models.results import OptimizationResult


def draw_frontier_chart(
    ax: matplotlib.axes.Axes,
    frontier_risks: list[float],
    frontier_returns: list[float],
    current: OptimizationResult,
    max_sharpe_result: OptimizationResult,
    min_variance_result: OptimizationResult,
    black_litterman_result: OptimizationResult,
) -> None:
    """Draw the mean-variance efficient frontier with the four key portfolios.

    The frontier curve is drawn as a line; the four portfolios are plotted as
    distinct markers with labels.

    Args:
        ax:                    Matplotlib Axes to draw on.
        frontier_risks:        Volatilities along the frontier (x-axis).
        frontier_returns:      Expected returns along the frontier (y-axis).
        current:               User's current portfolio.
        max_sharpe_result:     Maximum Sharpe optimized portfolio.
        min_variance_result:   Minimum Variance optimized portfolio.
        black_litterman_result: Black-Litterman optimized portfolio.
    """
    ax.clear()

    # ── Frontier curve ────────────────────────────────────────────────────────
    if frontier_risks and frontier_returns:
        ax.plot(
            frontier_risks,
            frontier_returns,
            color=BENCHMARK_COLOR,
            linewidth=2.0,
            label="Efficient Frontier",
            zorder=2,
        )

    # ── Marked portfolios ─────────────────────────────────────────────────────
    _portfolios = [
        (current,               CURRENT_COLOR,   "o", 80,  "Current"),
        (max_sharpe_result,     MAX_SHARPE_COLOR, "*", 160, "Max Sharpe"),
        (min_variance_result,   MIN_VAR_COLOR,    "s", 80,  "Min Variance"),
        (black_litterman_result, BL_COLOR,        "D", 80,  "Black-Litterman"),
    ]
    for result, color, marker, size, label in _portfolios:
        if result is None:
            continue
        vol = result.volatility
        ret = result.expected_return
        import numpy as np
        if np.isnan(vol) or np.isnan(ret):
            continue
        ax.scatter(
            vol, ret,
            color=color,
            marker=marker,
            s=size,
            zorder=5,
            label=label,
            edgecolors="white",
            linewidths=0.5,
        )
        ax.annotate(
            label,
            xy=(vol, ret),
            xytext=(6, 4),
            textcoords="offset points",
            color=color,
            fontsize=7.5,
            fontweight="bold",
        )

    ax.xaxis.set_major_formatter(mticker.FuncFormatter(pct_formatter))
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(pct_formatter))
    ax.set_xlabel("Annualised Volatility (Risk)", fontsize=9)
    ax.set_ylabel("Expected Return", fontsize=9)
    ax.set_title("Efficient Frontier", fontsize=10, color=TEXT)

    legend = ax.legend(
        loc="lower right",
        fontsize=7.5,
        framealpha=0.3,
        edgecolor="none",
    )
    for text in legend.get_texts():
        text.set_color(TEXT_DIM)

    _apply_dark_axes(ax)
