"""Monte Carlo simulation page (Phase 13)."""

from __future__ import annotations

import math
import sys
from pathlib import Path

_ROOT = str(Path(__file__).resolve().parent.parent.parent)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import numpy as np
import plotly.graph_objects as go
import streamlit as st

from analytics.monte_carlo import run_monte_carlo
from streamlit_app.state import session
from streamlit_app.styles.theme import (
    ACCENT, BG_PRIMARY, BG_SECONDARY, BG_TERTIARY, BORDER,
    DANGER, PLOTLY_TEMPLATE, SUCCESS, TEXT_PRIMARY, TEXT_SECONDARY, WARNING,
)

_MC_STATE = "mc_result"


def _apply_template(fig: go.Figure, height: int = 380) -> go.Figure:
    t = PLOTLY_TEMPLATE["layout"]
    fig.update_layout(
        paper_bgcolor=t["paper_bgcolor"], plot_bgcolor=t["plot_bgcolor"],
        font=t["font"], margin=t["margin"], height=height,
        legend=dict(bgcolor=t["legend"]["bgcolor"], bordercolor=t["legend"]["bordercolor"]),
    )
    fig.update_xaxes(gridcolor=BORDER, zerolinecolor=BORDER, linecolor=BORDER)
    fig.update_yaxes(gridcolor=BORDER, zerolinecolor=BORDER, linecolor=BORDER)
    return fig


def _h3(text: str) -> None:
    st.markdown(
        f"<h3 style='color:{TEXT_PRIMARY}; margin:0 0 12px 0; font-size:17px;'>{text}</h3>",
        unsafe_allow_html=True,
    )


def _divider() -> None:
    st.markdown(
        f"<hr style='border:none; border-top:1px solid {BORDER}; margin:14px 0 20px 0;'>",
        unsafe_allow_html=True,
    )


def _kpi(col, label: str, value: str, sub: str = "", color: str = TEXT_PRIMARY) -> None:
    kpi_style = (
        f"background:{BG_SECONDARY}; border:1px solid {BORDER}; border-radius:8px; "
        f"padding:14px 16px; text-align:center; box-shadow:0 1px 3px rgba(35,29,21,0.06);"
    )
    sub_html = (
        f'<div style="font-size:10px; color:{TEXT_SECONDARY}; margin-top:3px;">{sub}</div>'
        if sub else ""
    )
    # Build as a single unbroken string — a blank line in the HTML would cause
    # Streamlit's Markdown parser to end the HTML block early, leaving the
    # closing </div> to be rendered as literal text.
    col.markdown(
        f'<div style="{kpi_style}">'
        f'<div style="font-size:9px; color:{TEXT_SECONDARY}; text-transform:uppercase; '
        f'letter-spacing:0.07em; margin-bottom:4px;">{label}</div>'
        f'<div style="font-size:22px; font-weight:700; color:{color};">{value}</div>'
        f'{sub_html}'
        f'</div>',
        unsafe_allow_html=True,
    )


def render() -> None:
    result = session.get_result()
    if result is None:
        st.info("Run an analysis on the Dashboard first.")
        return

    pf = result.portfolio

    # ── Controls ───────────────────────────────────────────────────────────────
    ctrl1, ctrl2, ctrl3 = st.columns([2, 2, 1])
    with ctrl1:
        n_sims = st.slider("Number of simulations", 100, 5000, 1000, step=100,
                           key="mc_n_sims")
    with ctrl2:
        horizon = st.slider("Horizon (years)", 1, 30, 10, key="mc_horizon")
    with ctrl3:
        st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
        run = st.button("Run Simulation", type="primary", use_container_width=True)

    if run:
        weights = {t: m.weight for t, m in result.asset_metrics.items()}
        with st.spinner(f"Running {n_sims:,} simulations over {horizon} years…"):
            mc = run_monte_carlo(
                result.returns, weights,
                n_simulations=n_sims,
                horizon_years=horizon,
                start_value=10_000,
            )
        st.session_state[_MC_STATE] = mc

    mc = st.session_state.get(_MC_STATE)
    if mc is None:
        st.markdown(
            f"""<div style="background:{BG_SECONDARY}; border:1px solid {BORDER};
                        border-radius:10px; padding:40px; text-align:center; margin-top:16px;">
                <div style="font-size:36px; margin-bottom:10px;">🎲</div>
                <div style="font-size:14px; color:{TEXT_SECONDARY};">
                    Set your parameters above and click <strong>Run Simulation</strong>.
                </div>
            </div>""",
            unsafe_allow_html=True,
        )
        return

    _divider()

    # ── KPI strip ─────────────────────────────────────────────────────────────
    k1, k2, k3, k4, k5, k6 = st.columns(6)
    _kpi(k1, "Median (end)", f"€ {mc.median:,.0f}")
    _kpi(k2, "Mean (end)",   f"€ {mc.mean:,.0f}")
    _kpi(k3, "5th pct",  f"€ {mc.pct_5:,.0f}",
         sub="worst 5% of paths", color=DANGER)
    _kpi(k4, "95th pct", f"€ {mc.pct_95:,.0f}",
         sub="best 5% of paths",  color=SUCCESS)
    _kpi(k5, "Prob. of Loss", f"{mc.prob_loss * 100:.1f} %",
         color=DANGER if mc.prob_loss > 0.2 else WARNING if mc.prob_loss > 0.1 else SUCCESS)
    gain_median = (mc.median / 10_000 - 1) * 100
    _kpi(k6, "Median Gain", f"{gain_median:+.1f} %",
         color=SUCCESS if gain_median > 0 else DANGER)

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    # ── Paths chart ────────────────────────────────────────────────────────────
    _h3("Simulation Paths")

    fig = go.Figure()
    # Fan of sample paths (thin, transparent)
    n_shown = min(120, len(mc.sample_paths))
    for path in mc.sample_paths[:n_shown]:
        fig.add_trace(go.Scatter(
            y=path, mode="lines",
            line=dict(color=ACCENT, width=0.4),
            opacity=0.25, showlegend=False,
        ))
    # Confidence band fill
    x_axis = list(range(len(mc.pct_95_path)))
    fig.add_trace(go.Scatter(
        x=x_axis, y=mc.pct_95_path, mode="lines",
        line=dict(color=SUCCESS, width=0), showlegend=False,
    ))
    fig.add_trace(go.Scatter(
        x=x_axis, y=mc.pct_5_path, mode="lines",
        line=dict(color=DANGER, width=0),
        fill="tonexty", fillcolor="rgba(47,125,87,0.10)",
        name="5th–95th pct band",
    ))
    fig.add_trace(go.Scatter(
        y=mc.pct_95_path, mode="lines",
        line=dict(color=SUCCESS, width=1.5, dash="dash"), name="95th pct"))
    fig.add_trace(go.Scatter(
        y=mc.median_path, mode="lines",
        line=dict(color=ACCENT, width=2.5), name="Median"))
    fig.add_trace(go.Scatter(
        y=mc.pct_5_path, mode="lines",
        line=dict(color=DANGER, width=1.5, dash="dash"), name="5th pct"))
    fig.add_hline(y=10_000, line_dash="dot", line_color=TEXT_SECONDARY,
                  annotation_text="Start €10k", annotation_font_color=TEXT_SECONDARY)
    fig.update_layout(
        title=dict(text=f"{n_sims:,} Simulations · {horizon}y Horizon",
                   font=dict(size=13, color=TEXT_PRIMARY)),
        xaxis_title=f"Trading days (1 year ≈ 252)",
        yaxis_title="Portfolio Value (€)",
    )
    _apply_template(fig, height=420)
    st.plotly_chart(fig, use_container_width=True)

    _divider()

    # ── Ending-value distribution ──────────────────────────────────────────────
    _h3("Distribution of Ending Values")

    hist_col, stats_col = st.columns([3, 1])

    with hist_col:
        fig2 = go.Figure(go.Histogram(
            x=mc.ending_values, nbinsx=70,
            marker=dict(color=ACCENT, line=dict(color=BG_SECONDARY, width=0.5)),
            opacity=0.85, name="Simulations",
        ))
        # Colour the left tail (loss region)
        fig2.add_vrect(
            x0=min(mc.ending_values), x1=10_000,
            fillcolor=f"rgba(177,66,35,0.10)", line_width=0,
            annotation_text="Loss zone", annotation_position="top left",
            annotation_font_color=DANGER,
        )
        fig2.add_vline(x=mc.pct_5,    line_color=DANGER,  line_dash="dash",
                       annotation_text=f"5th pct", annotation_font_color=DANGER)
        fig2.add_vline(x=mc.median,   line_color=ACCENT,  line_dash="solid",
                       annotation_text=f"Median", annotation_font_color=ACCENT)
        fig2.add_vline(x=mc.pct_95,   line_color=SUCCESS, line_dash="dash",
                       annotation_text=f"95th pct", annotation_font_color=SUCCESS)
        fig2.add_vline(x=10_000,      line_color=TEXT_SECONDARY, line_dash="dot",
                       annotation_text="Start", annotation_font_color=TEXT_SECONDARY)
        fig2.update_layout(
            title=dict(text="Ending Portfolio Value Distribution",
                       font=dict(size=13, color=TEXT_PRIMARY)),
            xaxis_title="Portfolio Value (€)", yaxis_title="Count",
        )
        _apply_template(fig2, height=320)
        st.plotly_chart(fig2, use_container_width=True)

    with stats_col:
        ev = np.array(mc.ending_values)
        percentiles = [5, 10, 25, 50, 75, 90, 95]
        stat_rows = [{"Percentile": f"{p}th", "Value": f"€ {np.percentile(ev, p):,.0f}"}
                     for p in percentiles]
        stat_rows.append({"Percentile": "Mean", "Value": f"€ {ev.mean():,.0f}"})
        stat_rows.append({"Percentile": "Std Dev", "Value": f"€ {ev.std():,.0f}"})
        st.markdown("<div style='height:44px'></div>", unsafe_allow_html=True)
        st.dataframe(stat_rows, use_container_width=True, hide_index=True, height=300)
