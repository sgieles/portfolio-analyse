"""Risk and return contribution bar charts."""

from __future__ import annotations

import matplotlib.axes
import matplotlib.ticker as mticker

from charts.style import (
    PALETTE,
    TEXT,
    TEXT_DIM,
    _apply_dark_axes,
    pct_formatter,
)


def draw_risk_contribution_chart(
    ax: matplotlib.axes.Axes,
    risk_contributions: dict[str, float],
    title: str = "Risk Contribution",
) -> None:
    """Horizontal bar chart of each asset's fractional risk contribution.

    Args:
        ax:                 Matplotlib Axes to draw on.
        risk_contributions: Dict {ticker: fraction} summing to ≈1.0.
                            As produced by analytics.diversification.risk_contributions().
        title:              Chart title.
    """
    ax.clear()

    tickers = list(risk_contributions.keys())
    values  = [risk_contributions[t] * 100 for t in tickers]   # to percent
    colors  = [PALETTE[i % len(PALETTE)] for i in range(len(tickers))]

    bars = ax.barh(tickers, values, color=colors, edgecolor="none", height=0.55)

    # Value labels inside / next to bars
    for bar, val in zip(bars, values):
        ax.text(
            bar.get_width() + 0.3,
            bar.get_y() + bar.get_height() / 2,
            f"{val:.1f} %",
            va="center",
            fontsize=8,
            color=TEXT_DIM,
        )

    ax.set_xlabel("Contribution (%)", fontsize=9)
    ax.set_title(title, fontsize=10, color=TEXT)
    ax.set_xlim(0, max(values) * 1.20 if values else 100)
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:.0f} %"))

    _apply_dark_axes(ax)


def draw_return_contribution_chart(
    ax: matplotlib.axes.Axes,
    return_contributions: dict[str, float],
    title: str = "Return Contribution",
) -> None:
    """Horizontal bar chart of each asset's absolute return contribution.

    Positive contributions are shown in green-toned palette, negative in red.

    Args:
        ax:                  Matplotlib Axes to draw on.
        return_contributions: Dict {ticker: contribution} where contribution =
                              weight × annualised_return. As produced by
                              analytics.diversification.return_contributions().
        title:               Chart title.
    """
    ax.clear()

    tickers = list(return_contributions.keys())
    values  = [return_contributions[t] * 100 for t in tickers]   # to percent
    colors  = [
        PALETTE[0] if v < 0 else PALETTE[1]
        for v in values
    ]

    bars = ax.barh(tickers, values, color=colors, edgecolor="none", height=0.55)

    # Zero reference line
    ax.axvline(0, color=TEXT_DIM, linewidth=0.7, zorder=1)

    for bar, val in zip(bars, values):
        x_pos = bar.get_width() + (0.2 if val >= 0 else -0.2)
        ha = "left" if val >= 0 else "right"
        ax.text(
            x_pos,
            bar.get_y() + bar.get_height() / 2,
            f"{val:+.2f} %",
            va="center",
            ha=ha,
            fontsize=8,
            color=TEXT_DIM,
        )

    ax.set_xlabel("Contribution (% pa)", fontsize=9)
    ax.set_title(title, fontsize=10, color=TEXT)
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:+.1f} %"))

    _apply_dark_axes(ax)
