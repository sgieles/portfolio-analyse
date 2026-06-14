"""Portfolio vs benchmark growth chart — from a starting value of €10,000."""

from __future__ import annotations

import matplotlib.axes
import matplotlib.ticker as mticker
import pandas as pd

from charts.style import (
    BENCHMARK_COLOR,
    PORTFOLIO_COLOR,
    TEXT,
    TEXT_DIM,
    _apply_dark_axes,
    eur_formatter,
)


def draw_growth_chart(
    ax: matplotlib.axes.Axes,
    portfolio_values: pd.Series,
    benchmark_values: pd.Series,
    portfolio_label: str = "Portfolio",
    benchmark_label: str = "Benchmark",
) -> None:
    """Draw portfolio vs benchmark cumulative growth on *ax*.

    Both series should start at the same value (e.g. €10,000) and be indexed
    by date. Produces a dual-line chart with the final values annotated.

    Args:
        ax:               Matplotlib Axes to draw on.
        portfolio_values: Portfolio value time series (pd.Series, date index).
        benchmark_values: Benchmark value time series (pd.Series, date index).
        portfolio_label:  Legend label for the portfolio line.
        benchmark_label:  Legend label for the benchmark line.
    """
    ax.clear()

    ax.plot(
        portfolio_values.index,
        portfolio_values.values,
        color=PORTFOLIO_COLOR,
        linewidth=2.0,
        label=portfolio_label,
        zorder=3,
    )
    ax.plot(
        benchmark_values.index,
        benchmark_values.values,
        color=BENCHMARK_COLOR,
        linewidth=1.8,
        linestyle="--",
        label=benchmark_label,
        zorder=2,
    )

    # Shade outperformance / underperformance
    common_idx = portfolio_values.index.intersection(benchmark_values.index)
    if len(common_idx) > 1:
        pv = portfolio_values.reindex(common_idx)
        bv = benchmark_values.reindex(common_idx)
        ax.fill_between(
            common_idx,
            pv,
            bv,
            where=(pv >= bv),
            interpolate=True,
            color=PORTFOLIO_COLOR,
            alpha=0.12,
            zorder=1,
        )
        ax.fill_between(
            common_idx,
            pv,
            bv,
            where=(pv < bv),
            interpolate=True,
            color=BENCHMARK_COLOR,
            alpha=0.12,
            zorder=1,
        )

    # Annotate final values
    if len(portfolio_values) > 0:
        p_final = float(portfolio_values.iloc[-1])
        ax.annotate(
            eur_formatter(p_final),
            xy=(portfolio_values.index[-1], p_final),
            xytext=(-6, 6),
            textcoords="offset points",
            color=PORTFOLIO_COLOR,
            fontsize=8,
            fontweight="bold",
            ha="right",
        )
    if len(benchmark_values) > 0:
        b_final = float(benchmark_values.iloc[-1])
        ax.annotate(
            eur_formatter(b_final),
            xy=(benchmark_values.index[-1], b_final),
            xytext=(-6, -12),
            textcoords="offset points",
            color=BENCHMARK_COLOR,
            fontsize=8,
            ha="right",
        )

    ax.yaxis.set_major_formatter(mticker.FuncFormatter(eur_formatter))
    ax.set_ylabel("Portfolio Value", fontsize=9)
    ax.set_title("Portfolio Growth (€10,000 start)", fontsize=10, color=TEXT)

    legend = ax.legend(
        loc="upper left",
        fontsize=8,
        framealpha=0.3,
        edgecolor="none",
    )
    for text in legend.get_texts():
        text.set_color(TEXT_DIM)

    _apply_dark_axes(ax)
    ax.figure.autofmt_xdate(rotation=30, ha="right")
