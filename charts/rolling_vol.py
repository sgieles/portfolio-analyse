"""Rolling volatility chart — 12-month annualised volatility over time."""

from __future__ import annotations

import matplotlib.axes
import matplotlib.ticker as mticker
import pandas as pd

from charts.style import (
    ROLLING_VOL_COLOR,
    TEXT,
    TEXT_DIM,
    _apply_dark_axes,
    pct_formatter,
)


def draw_rolling_vol_chart(
    ax: matplotlib.axes.Axes,
    rolling_vol: pd.Series,
    window_label: str = "252-day",
) -> None:
    """Draw rolling annualised volatility on *ax*.

    Fills the area under the curve for emphasis and marks the current
    (most recent) value with a horizontal reference line.

    Args:
        ax:           Matplotlib Axes to draw on.
        rolling_vol:  Rolling annualised volatility series, as produced by
                      analytics.risk.rolling_volatility(). NaN values at the
                      start (before the window fills) are dropped silently.
        window_label: Human-readable window description for the chart title.
    """
    ax.clear()

    rv = rolling_vol.dropna()

    if rv.empty:
        ax.text(
            0.5, 0.5,
            "Insufficient data for rolling volatility",
            transform=ax.transAxes,
            ha="center",
            va="center",
            color=TEXT_DIM,
            fontsize=9,
        )
        _apply_dark_axes(ax)
        return

    ax.fill_between(
        rv.index,
        rv.values,
        color=ROLLING_VOL_COLOR,
        alpha=0.25,
        zorder=1,
    )
    ax.plot(
        rv.index,
        rv.values,
        color=ROLLING_VOL_COLOR,
        linewidth=1.8,
        zorder=2,
    )

    # Reference line at the current (most recent) value
    current_vol = float(rv.iloc[-1])
    ax.axhline(
        current_vol,
        color=ROLLING_VOL_COLOR,
        linewidth=0.8,
        linestyle="--",
        alpha=0.6,
        zorder=1,
    )
    ax.annotate(
        f"Now: {current_vol * 100:.1f} %",
        xy=(rv.index[-1], current_vol),
        xytext=(-8, 4),
        textcoords="offset points",
        color=ROLLING_VOL_COLOR,
        fontsize=8,
        ha="right",
    )

    ax.yaxis.set_major_formatter(mticker.FuncFormatter(pct_formatter))
    ax.set_ylabel("Annualised Volatility", fontsize=9)
    ax.set_title(f"Rolling Volatility ({window_label} window)", fontsize=10, color=TEXT)

    _apply_dark_axes(ax)
    ax.figure.autofmt_xdate(rotation=30, ha="right")
