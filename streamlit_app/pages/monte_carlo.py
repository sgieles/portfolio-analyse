"""Monte Carlo simulation page."""

from __future__ import annotations

import math

import plotly.graph_objects as go
import streamlit as st

from analytics.monte_carlo import run_monte_carlo
from streamlit_app.state import session
from streamlit_app.styles.theme import (
    ACCENT, BORDER, DANGER, PLOTLY_TEMPLATE, SUCCESS, TEXT_SECONDARY, WARNING,
)


def _apply_template(fig: go.Figure) -> go.Figure:
    t = PLOTLY_TEMPLATE["layout"]
    fig.update_layout(
        paper_bgcolor=t["paper_bgcolor"], plot_bgcolor=t["plot_bgcolor"],
        font=t["font"], margin=t["margin"],
    )
    fig.update_xaxes(gridcolor=BORDER, zerolinecolor=BORDER)
    fig.update_yaxes(gridcolor=BORDER, zerolinecolor=BORDER)
    return fig


def render() -> None:
    result = session.get_result()
    if result is None:
        st.info("Run an analysis on the Dashboard first.")
        return

    st.markdown("### Monte Carlo Simulation")

    col_s, col_h = st.columns(2)
    with col_s:
        n_sims = st.slider("Simulations", 100, 5000, 1000, step=100)
    with col_h:
        horizon = st.slider("Horizon (years)", 1, 30, 5)

    if st.button("Run Simulation", type="primary"):
        weights = {t: m.weight for t, m in result.asset_metrics.items()}
        with st.spinner("Running Monte Carlo…"):
            mc = run_monte_carlo(
                result.returns, weights,
                n_simulations=n_sims, horizon_years=horizon,
                start_value=10_000,
            )

        # ── KPI cards ─────────────────────────────────────────────────────────
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Median", f"€ {mc.median:,.0f}")
        c2.metric("Mean",   f"€ {mc.mean:,.0f}")
        c3.metric("5th pct", f"€ {mc.pct_5:,.0f}")
        c4.metric("95th pct", f"€ {mc.pct_95:,.0f}")
        c5.metric("Prob. Loss", f"{mc.prob_loss * 100:.1f} %")

        # ── Paths chart ────────────────────────────────────────────────────────
        fig = go.Figure()
        for path in mc.sample_paths[:80]:
            fig.add_trace(go.Scatter(
                y=path, mode="lines",
                line=dict(color=ACCENT, width=0.4),
                opacity=0.3, showlegend=False,
            ))
        fig.add_trace(go.Scatter(y=mc.pct_95_path, mode="lines",
                                 line=dict(color=SUCCESS, width=1.5, dash="dash"), name="95th pct"))
        fig.add_trace(go.Scatter(y=mc.median_path, mode="lines",
                                 line=dict(color=ACCENT, width=2.5), name="Median"))
        fig.add_trace(go.Scatter(y=mc.pct_5_path, mode="lines",
                                 line=dict(color=DANGER, width=1.5, dash="dash"), name="5th pct"))
        fig.add_hline(y=10_000, line_dash="dot", line_color=TEXT_SECONDARY, annotation_text="Start €10k")
        fig.update_layout(title=f"{n_sims} Simulations · {horizon}y Horizon",
                          yaxis_title="Portfolio Value (€)", height=420)
        _apply_template(fig)
        st.plotly_chart(fig, use_container_width=True)

        # ── Ending-value histogram ─────────────────────────────────────────────
        import numpy as np
        fig2 = go.Figure(go.Histogram(
            x=mc.ending_values, nbinsx=60,
            marker_color=ACCENT, opacity=0.8,
        ))
        fig2.add_vline(x=mc.median, line_color=SUCCESS, line_dash="dash",
                       annotation_text=f"Median €{mc.median:,.0f}")
        fig2.add_vline(x=10_000, line_color=TEXT_SECONDARY, line_dash="dot",
                       annotation_text="Start")
        fig2.update_layout(title="Distribution of Ending Values",
                           xaxis_title="Portfolio Value (€)", yaxis_title="Count", height=320)
        _apply_template(fig2)
        st.plotly_chart(fig2, use_container_width=True)
