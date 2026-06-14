"""Dashboard page — portfolio metrics and charts."""

from __future__ import annotations

import math

import numpy as np
import plotly.graph_objects as go
import streamlit as st

from analytics.health_score import portfolio_health_score
from analytics.scenario import run_scenario_analysis
from streamlit_app.components import analysis_runner
from streamlit_app.state import session
from streamlit_app.styles.theme import (
    ACCENT, BG_PRIMARY, BG_SECONDARY, BG_TERTIARY, BORDER,
    DANGER, PLOTLY_TEMPLATE, SUCCESS, TEXT_PRIMARY, TEXT_SECONDARY, WARNING,
)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _pct(v: float, dec: int = 2) -> str:
    return "—" if math.isnan(v) else f"{v * 100:.{dec}f} %"


def _num(v: float, dec: int = 2) -> str:
    return "—" if math.isnan(v) else f"{v:.{dec}f}"


def _color(v: float, good_above: float, warn_above: float) -> str:
    if math.isnan(v):
        return TEXT_SECONDARY
    return SUCCESS if v > good_above else WARNING if v > warn_above else DANGER


def _metric(label: str, value: str, color: str = TEXT_PRIMARY) -> None:
    """Render a single metric card with warm-theme styling."""
    st.markdown(
        f"""
        <div style="background:{BG_SECONDARY}; border:1px solid {BORDER};
                    border-radius:8px; padding:14px 18px; margin-bottom:8px;
                    box-shadow:0 1px 3px rgba(35,29,21,0.06);">
            <div style="font-size:10px; color:{TEXT_SECONDARY}; text-transform:uppercase;
                        letter-spacing:0.06em; margin-bottom:6px;">{label}</div>
            <div style="font-size:22px; font-weight:700; color:{color};
                        text-align:right; letter-spacing:-0.02em;">{value}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _section_header(title: str, accent_color: str = ACCENT) -> None:
    """Render a section label with a coloured left border."""
    st.markdown(
        f"""
        <div style="border-left:3px solid {accent_color}; padding-left:10px;
                    margin:0 0 10px 0;">
            <span style="font-size:11px; font-weight:700; color:{accent_color};
                         text-transform:uppercase; letter-spacing:0.08em;">{title}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _apply_template(fig: go.Figure) -> go.Figure:
    t = PLOTLY_TEMPLATE["layout"]
    fig.update_layout(
        paper_bgcolor=t["paper_bgcolor"],
        plot_bgcolor=t["plot_bgcolor"],
        font=t["font"],
        margin=t["margin"],
        legend=dict(bgcolor=t["legend"]["bgcolor"], bordercolor=t["legend"]["bordercolor"]),
    )
    fig.update_xaxes(gridcolor=BORDER, zerolinecolor=BORDER, linecolor=BORDER)
    fig.update_yaxes(gridcolor=BORDER, zerolinecolor=BORDER, linecolor=BORDER)
    return fig


def _chart_card(fig: go.Figure) -> None:
    """Wrap a plotly chart in a card-styled container."""
    st.plotly_chart(fig, use_container_width=True)


# ── Page ───────────────────────────────────────────────────────────────────────

def render() -> None:
    result = session.get_result()

    # ── Analyse button ─────────────────────────────────────────────────────────
    pf = session.get_portfolio()
    if pf.assets:
        col_btn, col_info = st.columns([1, 4])
        with col_btn:
            if st.button("Analyse Portfolio", type="primary", use_container_width=True):
                result = analysis_runner.run_analysis()
        if result:
            with col_info:
                st.caption(
                    f"Period: **{result.portfolio.period}**  ·  "
                    f"Benchmark: **{result.portfolio.benchmark}**  ·  "
                    f"{len(result.asset_metrics)} assets"
                )

    if result is None:
        st.markdown(
            f"""
            <div style="background:{BG_SECONDARY}; border:1px solid {BORDER};
                        border-radius:10px; padding:32px; text-align:center; margin-top:24px;">
                <div style="font-size:36px; margin-bottom:12px;">📊</div>
                <div style="font-size:16px; font-weight:600; color:{TEXT_PRIMARY}; margin-bottom:6px;">
                    No portfolio yet
                </div>
                <div style="font-size:13px; color:{TEXT_SECONDARY};">
                    Add tickers in the sidebar, then click <strong>Analyse Portfolio</strong>.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    # ── Section A: KPI strip ───────────────────────────────────────────────────
    weights_dict = {t: m.weight for t, m in result.asset_metrics.items()}
    hs, _ = portfolio_health_score(
        result.sharpe_ratio, result.max_drawdown,
        result.portfolio_volatility, result.diversification_score, weights_dict,
    )
    hs_color = SUCCESS if hs >= 60 else WARNING if hs >= 35 else DANGER

    kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)
    kpi_style = (
        f"background:{BG_SECONDARY}; border:1px solid {BORDER}; border-radius:8px; "
        f"padding:12px 14px; box-shadow:0 1px 3px rgba(35,29,21,0.06); text-align:center;"
    )

    def _kpi(col, label: str, value: str, color: str = TEXT_PRIMARY) -> None:
        col.markdown(
            f"""<div style="{kpi_style}">
                <div style="font-size:9px; color:{TEXT_SECONDARY}; text-transform:uppercase;
                            letter-spacing:0.07em; margin-bottom:4px;">{label}</div>
                <div style="font-size:20px; font-weight:700; color:{color};">{value}</div>
            </div>""",
            unsafe_allow_html=True,
        )

    _kpi(kpi1, "CAGR", _pct(result.portfolio_cagr),
         _color(result.portfolio_cagr, 0.08, 0.02))
    _kpi(kpi2, "Volatility", _pct(result.portfolio_volatility),
         SUCCESS if result.portfolio_volatility < 0.15 else WARNING if result.portfolio_volatility < 0.25 else DANGER)
    _kpi(kpi3, "Sharpe Ratio", _num(result.sharpe_ratio),
         SUCCESS if result.sharpe_ratio > 1.0 else WARNING if result.sharpe_ratio > 0.5 else DANGER)
    _kpi(kpi4, "Beta", _num(result.beta),
         SUCCESS if 0.8 <= result.beta <= 1.2 else WARNING)
    _kpi(kpi5, "Health Score", f"{hs:.0f} / 100", hs_color)

    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

    # ── Section B: Growth chart (full width, prominent) ───────────────────────
    if not result.portfolio_value_series.empty:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=result.portfolio_value_series.index,
            y=result.portfolio_value_series.values,
            name="Portfolio",
            line=dict(color=ACCENT, width=2.5),
            fill="tozeroy",
            fillcolor=f"rgba(194,65,12,0.08)",
        ))
        if not result.benchmark_value_series.empty:
            fig.add_trace(go.Scatter(
                x=result.benchmark_value_series.index,
                y=result.benchmark_value_series.values,
                name=pf.benchmark,
                line=dict(color="#2563eb", width=1.5, dash="dot"),
            ))
        fig.update_layout(
            title=dict(text="Portfolio Growth from €10,000", font=dict(size=14, color=TEXT_PRIMARY)),
            xaxis_title="", yaxis_title="Value (€)", height=360,
        )
        _apply_template(fig)
        st.plotly_chart(fig, use_container_width=True)

    # ── Section C: Drawdown + Rolling Volatility ───────────────────────────────
    col_dd, col_rv = st.columns(2)
    with col_dd:
        if not result.drawdown_series.empty:
            fig2 = go.Figure(go.Scatter(
                x=result.drawdown_series.index,
                y=(result.drawdown_series * 100).values,
                fill="tozeroy",
                fillcolor=f"rgba(177,66,35,0.15)",
                line=dict(color=DANGER, width=1.5),
                name="Drawdown",
            ))
            fig2.update_layout(
                title=dict(text="Drawdown", font=dict(size=13, color=TEXT_PRIMARY)),
                yaxis_title="%", height=280,
            )
            _apply_template(fig2)
            st.plotly_chart(fig2, use_container_width=True)

    with col_rv:
        if not result.rolling_volatility_series.empty:
            rv = result.rolling_volatility_series.dropna()
            fig3 = go.Figure(go.Scatter(
                x=rv.index, y=(rv * 100).values,
                line=dict(color="#2563eb", width=1.5),
                fill="tozeroy",
                fillcolor="rgba(37,99,235,0.08)",
                name="Rolling Vol",
            ))
            fig3.update_layout(
                title=dict(text="Rolling Volatility (252d)", font=dict(size=13, color=TEXT_PRIMARY)),
                yaxis_title="%", height=280,
            )
            _apply_template(fig3)
            st.plotly_chart(fig3, use_container_width=True)

    st.markdown(f"<hr style='border-color:{BORDER}; margin:8px 0 16px 0'>", unsafe_allow_html=True)

    # ── Section D: Metrics detail ──────────────────────────────────────────────
    st.markdown(
        f"<h3 style='color:{TEXT_PRIMARY}; margin-bottom:16px'>Portfolio Metrics</h3>",
        unsafe_allow_html=True,
    )
    col1, col2, col3 = st.columns(3)

    with col1:
        _section_header("Return", ACCENT)
        _metric("Expected Return (ann.)", _pct(result.portfolio_return),
                _color(result.portfolio_return, 0.08, 0.02))
        _metric("CAGR", _pct(result.portfolio_cagr),
                _color(result.portfolio_cagr, 0.08, 0.02))
        _metric("CAPM Expected Return", _pct(result.portfolio_expected_return_capm))

    with col2:
        _section_header("Risk", "#2563eb")
        _metric("Volatility (ann.)", _pct(result.portfolio_volatility),
                SUCCESS if result.portfolio_volatility < 0.15 else WARNING if result.portfolio_volatility < 0.25 else DANGER)
        _metric("Sharpe Ratio", _num(result.sharpe_ratio),
                SUCCESS if result.sharpe_ratio > 1.0 else WARNING if result.sharpe_ratio > 0.5 else DANGER)
        _metric("Beta vs Benchmark", _num(result.beta),
                SUCCESS if 0.8 <= result.beta <= 1.2 else WARNING)

    with col3:
        _section_header("Diversification", SUCCESS)
        _metric("Number of Assets", str(len(result.asset_metrics)))
        _metric("Avg Correlation", _num(result.avg_correlation),
                SUCCESS if result.avg_correlation < 0.5 else WARNING if result.avg_correlation < 0.75 else DANGER)
        _metric("Diversification Score", _num(result.diversification_score),
                SUCCESS if result.diversification_score > 0.3 else WARNING if result.diversification_score > 0.1 else DANGER)
        _metric("Health Score", f"{hs:.0f} / 100", hs_color)

    st.markdown(f"<hr style='border-color:{BORDER}; margin:8px 0 16px 0'>", unsafe_allow_html=True)

    # ── Section E: Efficient Frontier ─────────────────────────────────────────
    if result.frontier_risk:
        st.markdown(
            f"<h3 style='color:{TEXT_PRIMARY}; margin-bottom:16px'>Efficient Frontier</h3>",
            unsafe_allow_html=True,
        )
        fig4 = go.Figure()
        fig4.add_trace(go.Scatter(
            x=[r * 100 for r in result.frontier_risk],
            y=[r * 100 for r in result.frontier_return],
            mode="lines",
            line=dict(color=BORDER, width=2),
            name="Frontier",
        ))
        opt_points = {
            "Current":         ("current",         ACCENT,    "circle"),
            "Max Sharpe":      ("max_sharpe",       SUCCESS,   "star"),
            "Min Variance":    ("min_variance",     "#2563eb", "diamond"),
            "Black-Litterman": ("black_litterman",  WARNING,   "square"),
        }
        for label, (key, color, symbol) in opt_points.items():
            opt = result.optimization.get(key)
            if opt and not math.isnan(opt.volatility):
                fig4.add_trace(go.Scatter(
                    x=[opt.volatility * 100], y=[opt.expected_return * 100],
                    mode="markers+text", name=label,
                    marker=dict(color=color, size=14, symbol=symbol,
                                line=dict(color="#ffffff", width=1.5)),
                    text=[label], textposition="top center",
                    textfont=dict(size=10, color=color),
                ))
        fig4.update_layout(
            title=dict(text="Efficient Frontier", font=dict(size=13, color=TEXT_PRIMARY)),
            height=380,
            xaxis_title="Risk (Volatility %)",
            yaxis_title="Expected Return %",
        )
        _apply_template(fig4)
        st.plotly_chart(fig4, use_container_width=True)

        st.markdown(f"<hr style='border-color:{BORDER}; margin:8px 0 16px 0'>", unsafe_allow_html=True)

    # ── Section F: Scenario Analysis ───────────────────────────────────────────
    st.markdown(
        f"<h3 style='color:{TEXT_PRIMARY}; margin-bottom:16px'>Scenario Analysis</h3>",
        unsafe_allow_html=True,
    )
    try:
        weights = {t: m.weight for t, m in result.asset_metrics.items()}
        start_val = (
            float(result.portfolio_value_series.iloc[-1])
            if not result.portfolio_value_series.empty
            else 10_000.0
        )
        scenarios = run_scenario_analysis(
            result.returns, weights, result.benchmark_returns, start_value=start_val
        )

        sc_names  = [s.name for s in scenarios]
        sc_rets   = [s.portfolio_return * 100 for s in scenarios]
        sc_colors = [
            SUCCESS if r > 0 else DANGER
            for r in sc_rets
        ]

        s_col1, s_col2 = st.columns([3, 2])
        with s_col1:
            fig5 = go.Figure(go.Bar(
                x=sc_names, y=sc_rets,
                marker_color=sc_colors,
                text=[f"{r:.1f}%" for r in sc_rets],
                textposition="outside",
                textfont=dict(color=TEXT_PRIMARY, size=11),
            ))
            fig5.update_layout(
                title=dict(text="Portfolio Return per Scenario", font=dict(size=13, color=TEXT_PRIMARY)),
                yaxis_title="%", height=320,
                bargap=0.35,
            )
            _apply_template(fig5)
            st.plotly_chart(fig5, use_container_width=True)

        with s_col2:
            rows = []
            for s in scenarios:
                rows.append({
                    "Scenario":        s.name,
                    "Mkt Return":      _pct(s.market_return),
                    "Pf Return":       _pct(s.portfolio_return),
                    "Pf Value":        f"€ {s.new_value:,.0f}",
                })
            st.dataframe(rows, use_container_width=True, hide_index=True, height=320)
    except Exception:
        st.caption("Scenario analysis unavailable.")

    st.markdown(f"<hr style='border-color:{BORDER}; margin:8px 0 16px 0'>", unsafe_allow_html=True)

    # ── Section G: Risk & Return Contribution ──────────────────────────────────
    st.markdown(
        f"<h3 style='color:{TEXT_PRIMARY}; margin-bottom:16px'>Risk & Return Contribution</h3>",
        unsafe_allow_html=True,
    )
    rc_col1, rc_col2 = st.columns(2)
    tickers = list(result.asset_metrics.keys())
    risk_contribs   = [result.asset_metrics[t].risk_contribution   for t in tickers]
    return_contribs = [result.asset_metrics[t].return_contribution for t in tickers]

    with rc_col1:
        fig6 = go.Figure(go.Bar(
            x=tickers, y=[v * 100 for v in risk_contribs],
            marker_color=ACCENT,
            text=[f"{v*100:.1f}%" for v in risk_contribs],
            textposition="outside",
            textfont=dict(color=TEXT_PRIMARY, size=11),
        ))
        fig6.update_layout(
            title=dict(text="Risk Contribution", font=dict(size=13, color=TEXT_PRIMARY)),
            yaxis_title="%", height=300, bargap=0.35,
        )
        _apply_template(fig6)
        st.plotly_chart(fig6, use_container_width=True)

    with rc_col2:
        fig7 = go.Figure(go.Bar(
            x=tickers, y=[v * 100 for v in return_contribs],
            marker_color="#2563eb",
            text=[f"{v*100:.1f}%" for v in return_contribs],
            textposition="outside",
            textfont=dict(color=TEXT_PRIMARY, size=11),
        ))
        fig7.update_layout(
            title=dict(text="Return Contribution", font=dict(size=13, color=TEXT_PRIMARY)),
            yaxis_title="%", height=300, bargap=0.35,
        )
        _apply_template(fig7)
        st.plotly_chart(fig7, use_container_width=True)
