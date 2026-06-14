"""Chart colour palette and formatting helpers.

These constants mirror the dark theme in ui/theme.py but live in charts/
so chart modules never need to import from the ui layer.
"""

from __future__ import annotations

import matplotlib.ticker as mticker
import pandas as pd

# ── Colour palette ────────────────────────────────────────────────────────────
PALETTE: list[str] = [
    "#e94560",  # accent red
    "#00b4d8",  # cyan
    "#90e0ef",  # light cyan
    "#f77f00",  # orange
    "#4cc9f0",  # bright blue
    "#a8dadc",  # pale teal
    "#f4a261",  # warm orange
    "#2ec4b6",  # teal
    "#cbf3f0",  # near-white teal
    "#ff6b6b",  # coral
]

PORTFOLIO_COLOR   = "#e94560"
BENCHMARK_COLOR   = "#00b4d8"
MAX_SHARPE_COLOR  = "#f77f00"
MIN_VAR_COLOR     = "#4cc9f0"
BL_COLOR          = "#a8dadc"
CURRENT_COLOR     = "#e94560"

DRAWDOWN_COLOR    = "#e94560"
ROLLING_VOL_COLOR = "#f77f00"

BG_PANEL  = "#16213e"
BORDER    = "#2a2a4a"
TEXT      = "#eaeaea"
TEXT_DIM  = "#a0a0b0"


# ── Formatting helpers ────────────────────────────────────────────────────────

def pct_formatter(x: float, _pos: int | None = None) -> str:
    return f"{x * 100:.1f} %"


def eur_formatter(x: float, _pos: int | None = None) -> str:
    if abs(x) >= 1_000:
        return f"€{x:,.0f}"
    return f"€{x:.0f}"


def _apply_dark_axes(ax) -> None:
    """Apply consistent dark-theme styling to a single Axes."""
    ax.set_facecolor(BG_PANEL)
    ax.tick_params(colors=TEXT_DIM, labelsize=9)
    ax.xaxis.label.set_color(TEXT_DIM)
    ax.yaxis.label.set_color(TEXT_DIM)
    if ax.get_title():
        ax.title.set_color(TEXT)
    for spine in ax.spines.values():
        spine.set_edgecolor(BORDER)
    ax.grid(True, color=BORDER, linewidth=0.5, alpha=0.7)
