"""Correlation and covariance heatmaps + clustering for Tab 3."""

from __future__ import annotations

import matplotlib.axes
import matplotlib.figure
import numpy as np
import pandas as pd
import seaborn as sns

from charts.style import BG_PANEL, BORDER, TEXT, TEXT_DIM, _apply_dark_axes


# ── Heatmap colour maps ───────────────────────────────────────────────────────
_CORR_CMAP  = "RdYlGn"   # red=−1 (bad), green=+1 (perfect)
_COV_CMAP   = "YlOrRd"   # yellow=low, red=high covariance


def draw_correlation_heatmap(
    ax: matplotlib.axes.Axes,
    returns: pd.DataFrame,
    annot: bool = True,
) -> None:
    """Seaborn correlation matrix heatmap.

    Args:
        ax:      Matplotlib Axes to draw on.
        returns: Daily returns DataFrame (rows = dates, columns = tickers).
        annot:   Whether to annotate cells with their value.
    """
    ax.clear()

    corr = returns.corr(numeric_only=False)
    mask = np.zeros_like(corr, dtype=bool)
    mask[np.triu_indices_from(mask, k=1)] = False   # show full matrix

    sns.heatmap(
        corr,
        ax=ax,
        annot=annot,
        fmt=".2f",
        cmap=_CORR_CMAP,
        vmin=-1.0,
        vmax=1.0,
        linewidths=0.5,
        linecolor=BORDER,
        annot_kws={"size": 8, "color": "black"},
        cbar_kws={"shrink": 0.8},
    )

    ax.set_title("Correlation Matrix", fontsize=10, color=TEXT)
    ax.tick_params(colors=TEXT_DIM, labelsize=8)
    ax.set_facecolor(BG_PANEL)


def draw_covariance_heatmap(
    ax: matplotlib.axes.Axes,
    returns: pd.DataFrame,
    annot: bool = True,
) -> None:
    """Seaborn annualised covariance matrix heatmap.

    Args:
        ax:      Matplotlib Axes to draw on.
        returns: Daily returns DataFrame.
        annot:   Whether to annotate cells with their value.
    """
    ax.clear()

    cov = returns.cov(ddof=1) * 252   # annualise

    sns.heatmap(
        cov,
        ax=ax,
        annot=annot,
        fmt=".4f",
        cmap=_COV_CMAP,
        linewidths=0.5,
        linecolor=BORDER,
        annot_kws={"size": 7, "color": "black"},
        cbar_kws={"shrink": 0.8},
    )

    ax.set_title("Covariance Matrix (annualised)", fontsize=10, color=TEXT)
    ax.tick_params(colors=TEXT_DIM, labelsize=8)
    ax.set_facecolor(BG_PANEL)


def draw_correlation_clustermap(
    returns: pd.DataFrame,
    figsize: tuple[float, float] = (8.0, 7.0),
) -> matplotlib.figure.Figure:
    """Seaborn correlation clustermap (creates and returns its own Figure).

    Assets are reordered by hierarchical clustering so that highly correlated
    assets appear adjacent to each other, revealing hidden concentration risk.

    Args:
        returns: Daily returns DataFrame.
        figsize: Figure dimensions in inches.

    Returns:
        The seaborn ClusterGrid's underlying Figure.
    """
    corr = returns.corr(numeric_only=False)

    g = sns.clustermap(
        corr,
        cmap=_CORR_CMAP,
        vmin=-1.0,
        vmax=1.0,
        annot=True,
        fmt=".2f",
        figsize=figsize,
        linewidths=0.5,
        linecolor=BORDER,
        annot_kws={"size": 8},
        dendrogram_ratio=0.15,
        cbar_pos=(0.02, 0.8, 0.03, 0.18),
    )

    g.figure.suptitle(
        "Correlation Clustering",
        fontsize=11,
        color=TEXT,
        y=1.01,
    )
    g.figure.patch.set_facecolor(BG_PANEL)

    return g.figure
