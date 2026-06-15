"""Dashboard page — portfolio metrics and charts (Phase 12)."""

from __future__ import annotations

import math
import sys
from datetime import date, timedelta
from pathlib import Path

_ROOT = str(Path(__file__).resolve().parent.parent.parent)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import numpy as np
import plotly.graph_objects as go
import plotly.figure_factory as ff
import streamlit as st

from analytics.health_score import portfolio_health_score
from analytics.scenario import run_scenario_analysis
from streamlit_app.components import analysis_runner
from streamlit_app.state import session
from streamlit_app.styles.theme import (
    ACCENT, BG_PRIMARY, BG_SECONDARY, BG_TERTIARY, BORDER,
    DANGER, PLOTLY_TEMPLATE, SUCCESS, TEXT_PRIMARY, TEXT_SECONDARY, WARNING,
)


# ── Formatting helpers ─────────────────────────────────────────────────────────

def _pct(v: float, dec: int = 2) -> str:
    return "—" if math.isnan(v) else f"{v * 100:.{dec}f} %"


def _num(v: float, dec: int = 2) -> str:
    return "—" if math.isnan(v) else f"{v:.{dec}f}"


def _color(v: float, good_above: float, warn_above: float) -> str:
    if math.isnan(v):
        return TEXT_SECONDARY
    return SUCCESS if v > good_above else WARNING if v > warn_above else DANGER


# ── UI components ──────────────────────────────────────────────────────────────

def _metric(label: str, value: str, color: str = TEXT_PRIMARY) -> None:
    st.markdown(
        f"""
        <div style="background:{BG_SECONDARY}; border:1px solid {BORDER};
                    border-radius:8px; padding:12px 16px; margin-bottom:7px;
                    box-shadow:0 1px 3px rgba(35,29,21,0.06);">
            <div style="font-size:10px; color:{TEXT_SECONDARY}; text-transform:uppercase;
                        letter-spacing:0.06em; margin-bottom:5px;">{label}</div>
            <div style="font-size:20px; font-weight:700; color:{color};
                        text-align:right; letter-spacing:-0.02em;">{value}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _section_header(title: str, color: str = ACCENT) -> None:
    st.markdown(
        f"""<div style="border-left:3px solid {color}; padding-left:10px; margin:0 0 10px 0;">
            <span style="font-size:11px; font-weight:700; color:{color};
                         text-transform:uppercase; letter-spacing:0.08em;">{title}</span>
        </div>""",
        unsafe_allow_html=True,
    )


def _h3(title: str) -> None:
    st.markdown(
        f"<h3 style='color:{TEXT_PRIMARY}; margin:0 0 14px 0; font-size:17px;'>{title}</h3>",
        unsafe_allow_html=True,
    )


def _divider() -> None:
    st.markdown(
        f"<hr style='border:none; border-top:1px solid {BORDER}; margin:14px 0 20px 0;'>",
        unsafe_allow_html=True,
    )


def _apply_template(fig: go.Figure, height: int | None = None) -> go.Figure:
    t = PLOTLY_TEMPLATE["layout"]
    update = dict(
        paper_bgcolor=t["paper_bgcolor"],
        plot_bgcolor=t["plot_bgcolor"],
        font=t["font"],
        margin=t["margin"],
        legend=dict(bgcolor=t["legend"]["bgcolor"], bordercolor=t["legend"]["bordercolor"]),
    )
    if height:
        update["height"] = height
    fig.update_layout(**update)
    fig.update_xaxes(gridcolor=BORDER, zerolinecolor=BORDER, linecolor=BORDER)
    fig.update_yaxes(gridcolor=BORDER, zerolinecolor=BORDER, linecolor=BORDER)
    return fig


# ── Period filter helper ───────────────────────────────────────────────────────

def _filter_series(series, period_label: str):
    """Slice a DatetimeIndex series by the selected period label."""
    if series.empty:
        return series
    today = series.index[-1]
    cutoffs = {
        "1M":  today - timedelta(days=30),
        "3M":  today - timedelta(days=91),
        "6M":  today - timedelta(days=182),
        "YTD": today.replace(month=1, day=1),
        "1Y":  today - timedelta(days=365),
        "All": series.index[0],
    }
    start = cutoffs.get(period_label, series.index[0])
    return series[series.index >= start]


# ── Page ───────────────────────────────────────────────────────────────────────

def render() -> None:
    result = session.get_result()
    pf = session.get_portfolio()

    # ── Analyse button ─────────────────────────────────────────────────────────
    if pf.assets:
        col_btn, col_info = st.columns([1, 5])
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
            f"""<div style="background:{BG_SECONDARY}; border:1px solid {BORDER};
                        border-radius:10px; padding:40px; text-align:center; margin-top:24px;">
                <div style="font-size:40px; margin-bottom:12px;">📊</div>
                <div style="font-size:16px; font-weight:600; color:{TEXT_PRIMARY}; margin-bottom:6px;">
                    No portfolio analysed yet
                </div>
                <div style="font-size:13px; color:{TEXT_SECONDARY};">
                    Add tickers in the sidebar, then click <strong>Analyse Portfolio</strong>.
                </div>
            </div>""",
            unsafe_allow_html=True,
        )
        return

    # ── Show warnings / failed tickers ────────────────────────────────────────
    if result.failed_tickers:
        st.warning(f"Could not load data for: {', '.join(result.failed_tickers)}")

    # ── KPI strip ─────────────────────────────────────────────────────────────
    weights_dict = {t: m.weight for t, m in result.asset_metrics.items()}
    hs, _ = portfolio_health_score(
        result.sharpe_ratio, result.max_drawdown,
        result.portfolio_volatility, result.diversification_score, weights_dict,
    )
    hs_color = SUCCESS if hs >= 60 else WARNING if hs >= 35 else DANGER

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

    k1, k2, k3, k4, k5, k6, k7 = st.columns(7)
    _kpi(k1, "CAGR", _pct(result.portfolio_cagr),
         _color(result.portfolio_cagr, 0.08, 0.02))
    _kpi(k2, "Ann. Return", _pct(result.portfolio_return),
         _color(result.portfolio_return, 0.08, 0.02))
    _kpi(k3, "Volatility", _pct(result.portfolio_volatility),
         SUCCESS if result.portfolio_volatility < 0.15 else WARNING if result.portfolio_volatility < 0.25 else DANGER)
    _kpi(k4, "Sharpe", _num(result.sharpe_ratio),
         SUCCESS if result.sharpe_ratio > 1.0 else WARNING if result.sharpe_ratio > 0.5 else DANGER)
    _kpi(k5, "Sortino", _num(result.sortino_ratio),
         SUCCESS if result.sortino_ratio > 1.0 else WARNING if result.sortino_ratio > 0.5 else DANGER)
    _kpi(k6, "Max Drawdown", _pct(result.max_drawdown),
         DANGER if result.max_drawdown < -0.20 else WARNING if result.max_drawdown < -0.10 else SUCCESS)
    _kpi(k7, "Health Score", f"{hs:.0f} / 100", hs_color)

    st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)

    # ═══════════════════════════════════════════════════════════════════════════
    # SECTION C — Performance chart with period selector
    # ═══════════════════════════════════════════════════════════════════════════
    _h3("Performance")

    period_col, _ = st.columns([3, 7])
    with period_col:
        period_sel = st.radio(
            "Period", ["1M", "3M", "6M", "YTD", "1Y", "All"],
            index=5, horizontal=True, label_visibility="collapsed",
            key="perf_period",
        )

    if not result.portfolio_value_series.empty:
        pv = _filter_series(result.portfolio_value_series, period_sel)
        # Re-base to 10k at the start of the selected window
        if not pv.empty:
            base = pv.iloc[0]
            pv = pv / base * 10_000

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=pv.index, y=pv.values,
            name="Portfolio",
            line=dict(color=ACCENT, width=2.5),
            fill="tozeroy",
            fillcolor="rgba(194,65,12,0.08)",
        ))
        if not result.benchmark_value_series.empty:
            bv = _filter_series(result.benchmark_value_series, period_sel)
            if not bv.empty:
                bv = bv / bv.iloc[0] * 10_000
            if not bv.empty:
                fig.add_trace(go.Scatter(
                    x=bv.index, y=bv.values,
                    name=pf.benchmark,
                    line=dict(color="#2563eb", width=1.5, dash="dot"),
                ))
        fig.update_layout(
            title=dict(text=f"Growth from €10,000 · {period_sel}", font=dict(size=13, color=TEXT_PRIMARY)),
            xaxis_title="", yaxis_title="Value (€)",
        )
        _apply_template(fig, height=340)
        st.plotly_chart(fig, use_container_width=True)

    _divider()

    # ═══════════════════════════════════════════════════════════════════════════
    # SECTION D — Allocation Analysis (sector donut + weight donut)
    # ═══════════════════════════════════════════════════════════════════════════
    _h3("Allocation")

    d_col1, d_col2 = st.columns(2)

    with d_col1:
        # Weight allocation donut
        tickers_w  = list(result.asset_metrics.keys())
        weights_w  = [result.asset_metrics[t].weight * 100 for t in tickers_w]
        donut_colors = [ACCENT, "#2563eb", SUCCESS, WARNING, "#8b5cf6",
                        "#0ea5a4", "#64748b", "#f59e0b", DANGER, "#3f6f8f"]
        fig_d = go.Figure(go.Pie(
            labels=tickers_w, values=weights_w,
            hole=0.55,
            marker=dict(colors=donut_colors[:len(tickers_w)],
                        line=dict(color=BG_SECONDARY, width=2)),
            textinfo="label+percent",
            textfont=dict(size=11, color=TEXT_PRIMARY),
        ))
        fig_d.update_layout(
            title=dict(text="Portfolio Weights", font=dict(size=13, color=TEXT_PRIMARY)),
            showlegend=False,
        )
        _apply_template(fig_d, height=300)
        st.plotly_chart(fig_d, use_container_width=True)

    with d_col2:
        # Sector allocation (fetched from yfinance info, cached)
        _render_sector_donut(tickers_w, weights_w, donut_colors)

    _divider()

    # ═══════════════════════════════════════════════════════════════════════════
    # SECTION B — Full metrics detail
    # ═══════════════════════════════════════════════════════════════════════════
    _h3("Portfolio Metrics")

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
        _metric("Sortino Ratio", _num(result.sortino_ratio),
                SUCCESS if result.sortino_ratio > 1.0 else WARNING if result.sortino_ratio > 0.5 else DANGER)
        _metric("Beta vs Benchmark", _num(result.beta),
                SUCCESS if 0.8 <= result.beta <= 1.2 else WARNING)
        _metric("Max Drawdown", _pct(result.max_drawdown),
                DANGER if result.max_drawdown < -0.20 else WARNING if result.max_drawdown < -0.10 else SUCCESS)
        _metric("VaR 95 %", _pct(result.var_95))
        _metric("VaR 99 %", _pct(result.var_99))
        _metric("CVaR (ES)", _pct(result.cvar))

    with col3:
        _section_header("Diversification", SUCCESS)
        _metric("Number of Assets", str(len(result.asset_metrics)))
        _metric("Avg Correlation", _num(result.avg_correlation),
                SUCCESS if result.avg_correlation < 0.5 else WARNING if result.avg_correlation < 0.75 else DANGER)
        _metric("Diversification Score", _num(result.diversification_score),
                SUCCESS if result.diversification_score > 0.3 else WARNING if result.diversification_score > 0.1 else DANGER)
        _metric("Health Score", f"{hs:.0f} / 100", hs_color)

    _divider()

    # ═══════════════════════════════════════════════════════════════════════════
    # SECTION G — Correlation Matrix
    # ═══════════════════════════════════════════════════════════════════════════
    _h3("Correlation Matrix")

    if not result.returns.empty and len(result.returns.columns) > 1:
        corr = result.returns.corr()
        tickers_c = list(corr.columns)
        z = corr.values.tolist()
        text = [[f"{v:.2f}" for v in row] for row in corr.values]

        fig_c = go.Figure(go.Heatmap(
            z=z, x=tickers_c, y=tickers_c,
            text=text, texttemplate="%{text}",
            colorscale=[
                [0.0,  DANGER],
                [0.5,  BG_TERTIARY],
                [1.0,  SUCCESS],
            ],
            zmin=-1, zmax=1,
            showscale=True,
            colorbar=dict(
                thickness=12, len=0.8,
                title=dict(text="r", font=dict(color=TEXT_SECONDARY, size=11)),
                tickfont=dict(color=TEXT_SECONDARY),
            ),
            textfont=dict(size=11, color=TEXT_PRIMARY),
        ))
        fig_c.update_layout(
            title=dict(text="Pearson Correlation (daily returns)", font=dict(size=13, color=TEXT_PRIMARY)),
        )
        _apply_template(fig_c, height=max(280, len(tickers_c) * 60))
        fig_c.update_yaxes(autorange="reversed")
        st.plotly_chart(fig_c, use_container_width=True)

    _divider()

    # ═══════════════════════════════════════════════════════════════════════════
    # SECTION H & I — Drawdown + Rolling Volatility
    # ═══════════════════════════════════════════════════════════════════════════
    _h3("Risk Charts")

    col_dd, col_rv = st.columns(2)
    with col_dd:
        if not result.drawdown_series.empty:
            dd_f = _filter_series(result.drawdown_series, period_sel)
            fig2 = go.Figure(go.Scatter(
                x=dd_f.index, y=(dd_f * 100).values,
                fill="tozeroy", fillcolor="rgba(177,66,35,0.15)",
                line=dict(color=DANGER, width=1.5), name="Drawdown",
            ))
            fig2.update_layout(
                title=dict(text="Drawdown", font=dict(size=13, color=TEXT_PRIMARY)),
                yaxis_title="%",
            )
            _apply_template(fig2, height=260)
            st.plotly_chart(fig2, use_container_width=True)

    with col_rv:
        if not result.rolling_volatility_series.empty:
            rv = _filter_series(result.rolling_volatility_series.dropna(), period_sel)
            fig3 = go.Figure(go.Scatter(
                x=rv.index, y=(rv * 100).values,
                line=dict(color="#2563eb", width=1.5),
                fill="tozeroy", fillcolor="rgba(37,99,235,0.08)",
                name="Rolling Vol",
            ))
            fig3.update_layout(
                title=dict(text="Rolling Volatility (252d)", font=dict(size=13, color=TEXT_PRIMARY)),
                yaxis_title="%",
            )
            _apply_template(fig3, height=260)
            st.plotly_chart(fig3, use_container_width=True)

    _divider()

    # ═══════════════════════════════════════════════════════════════════════════
    # SECTION E — Efficient Frontier
    # ═══════════════════════════════════════════════════════════════════════════
    if result.frontier_risk:
        _h3("Efficient Frontier")
        fig4 = go.Figure()
        fig4.add_trace(go.Scatter(
            x=[r * 100 for r in result.frontier_risk],
            y=[r * 100 for r in result.frontier_return],
            mode="lines", line=dict(color=BORDER, width=2), name="Frontier",
        ))
        opt_pts = {
            "Current":         ("current",        ACCENT,    "circle"),
            "Max Sharpe":      ("max_sharpe",      SUCCESS,   "star"),
            "Min Variance":    ("min_variance",    "#2563eb", "diamond"),
            "Black-Litterman": ("black_litterman", WARNING,   "square"),
        }
        for label, (key, color, symbol) in opt_pts.items():
            opt = result.optimization.get(key)
            if opt and not math.isnan(opt.volatility):
                fig4.add_trace(go.Scatter(
                    x=[opt.volatility * 100], y=[opt.expected_return * 100],
                    mode="markers+text", name=label,
                    marker=dict(color=color, size=14, symbol=symbol,
                                line=dict(color=BG_SECONDARY, width=1.5)),
                    text=[label], textposition="top center",
                    textfont=dict(size=10, color=color),
                ))
        fig4.update_layout(
            title=dict(text="Efficient Frontier", font=dict(size=13, color=TEXT_PRIMARY)),
            xaxis_title="Risk (Volatility %)", yaxis_title="Expected Return %",
        )
        _apply_template(fig4, height=380)
        st.plotly_chart(fig4, use_container_width=True)
        _divider()

    # ═══════════════════════════════════════════════════════════════════════════
    # SECTION F — Optimization panel
    # ═══════════════════════════════════════════════════════════════════════════
    _h3("Optimization")
    _render_optimization_panel(result, pf)
    _divider()

    # ═══════════════════════════════════════════════════════════════════════════
    # SECTION J — Scenario Analysis
    # ═══════════════════════════════════════════════════════════════════════════
    _h3("Scenario Analysis")
    try:
        weights = {t: m.weight for t, m in result.asset_metrics.items()}
        start_val = (
            float(result.portfolio_value_series.iloc[-1])
            if not result.portfolio_value_series.empty else 10_000.0
        )
        scenarios = run_scenario_analysis(
            result.returns, weights, result.benchmark_returns, start_value=start_val
        )
        sc_names  = [s.name for s in scenarios]
        sc_rets   = [s.portfolio_return * 100 for s in scenarios]
        sc_colors = [SUCCESS if r > 0 else DANGER for r in sc_rets]

        s_col1, s_col2 = st.columns([3, 2])
        with s_col1:
            fig5 = go.Figure(go.Bar(
                x=sc_names, y=sc_rets,
                marker_color=sc_colors,
                text=[f"{r:.1f}%" for r in sc_rets], textposition="outside",
                textfont=dict(color=TEXT_PRIMARY, size=11),
            ))
            fig5.update_layout(
                title=dict(text="Portfolio Return per Scenario", font=dict(size=13, color=TEXT_PRIMARY)),
                yaxis_title="%", bargap=0.35,
            )
            _apply_template(fig5, height=300)
            st.plotly_chart(fig5, use_container_width=True)

        with s_col2:
            rows = [
                {"Scenario": s.name, "Mkt Return": _pct(s.market_return),
                 "Pf Return": _pct(s.portfolio_return), "Pf Value": f"€ {s.new_value:,.0f}"}
                for s in scenarios
            ]
            st.dataframe(rows, use_container_width=True, hide_index=True, height=300)
    except Exception:
        st.caption("Scenario analysis unavailable.")

    _divider()

    # ═══════════════════════════════════════════════════════════════════════════
    # Risk & Return Contribution
    # ═══════════════════════════════════════════════════════════════════════════
    _h3("Risk & Return Contribution")
    rc_col1, rc_col2 = st.columns(2)
    tickers_r = list(result.asset_metrics.keys())
    risk_contribs   = [result.asset_metrics[t].risk_contribution   for t in tickers_r]
    return_contribs = [result.asset_metrics[t].return_contribution for t in tickers_r]

    with rc_col1:
        fig6 = go.Figure(go.Bar(
            x=tickers_r, y=[v * 100 for v in risk_contribs],
            marker_color=ACCENT,
            text=[f"{v*100:.1f}%" for v in risk_contribs],
            textposition="outside", textfont=dict(color=TEXT_PRIMARY, size=11),
        ))
        fig6.update_layout(
            title=dict(text="Risk Contribution", font=dict(size=13, color=TEXT_PRIMARY)),
            yaxis_title="%", bargap=0.35,
        )
        _apply_template(fig6, height=280)
        st.plotly_chart(fig6, use_container_width=True)

    with rc_col2:
        fig7 = go.Figure(go.Bar(
            x=tickers_r, y=[v * 100 for v in return_contribs],
            marker_color="#2563eb",
            text=[f"{v*100:.1f}%" for v in return_contribs],
            textposition="outside", textfont=dict(color=TEXT_PRIMARY, size=11),
        ))
        fig7.update_layout(
            title=dict(text="Return Contribution", font=dict(size=13, color=TEXT_PRIMARY)),
            yaxis_title="%", bargap=0.35,
        )
        _apply_template(fig7, height=280)
        st.plotly_chart(fig7, use_container_width=True)


# ── Sector allocation helper ───────────────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def _fetch_sectors(tickers: tuple[str, ...]) -> dict[str, str]:
    """Return {ticker: sector} using yfinance, cached for 1h."""
    import yfinance as yf
    result: dict[str, str] = {}
    for t in tickers:
        try:
            info = yf.Ticker(t).info
            sector = info.get("sector") or info.get("quoteType") or "Other"
            result[t] = sector
        except Exception:
            result[t] = "Other"
    return result


def _render_sector_donut(tickers: list[str], weights_pct: list[float],
                          colors: list[str]) -> None:
    with st.spinner("Loading sector data…"):
        sector_map = _fetch_sectors(tuple(tickers))

    # Aggregate weights by sector
    sector_weights: dict[str, float] = {}
    for t, w in zip(tickers, weights_pct):
        s = sector_map.get(t, "Other")
        sector_weights[s] = sector_weights.get(s, 0.0) + w

    labels = list(sector_weights.keys())
    vals   = list(sector_weights.values())

    palette = [ACCENT, "#2563eb", SUCCESS, WARNING, "#8b5cf6",
               "#0ea5a4", "#64748b", "#f59e0b", DANGER, "#3f6f8f"]

    fig = go.Figure(go.Pie(
        labels=labels, values=vals,
        hole=0.55,
        marker=dict(colors=palette[:len(labels)],
                    line=dict(color=BG_SECONDARY, width=2)),
        textinfo="label+percent",
        textfont=dict(size=11, color=TEXT_PRIMARY),
    ))
    fig.update_layout(
        title=dict(text="Sector Allocation", font=dict(size=13, color=TEXT_PRIMARY)),
        showlegend=False,
    )
    t = PLOTLY_TEMPLATE["layout"]
    fig.update_layout(
        paper_bgcolor=t["paper_bgcolor"], plot_bgcolor=t["plot_bgcolor"],
        font=t["font"], margin=t["margin"], height=300,
    )
    st.plotly_chart(fig, use_container_width=True)


# ── Optimization panel helper ──────────────────────────────────────────────────

def _render_optimization_panel(result, pf) -> None:
    """Show current vs optimised weight/metric table and apply-weights buttons."""
    from models.asset import Asset

    opt = result.optimization
    methods = {
        "Current":         "current",
        "Max Sharpe":      "max_sharpe",
        "Min Variance":    "min_variance",
        "Black-Litterman": "black_litterman",
    }
    tickers = list(result.asset_metrics.keys())

    # ── Weight comparison table ────────────────────────────────────────────────
    weight_rows = []
    for t in tickers:
        row = {"Ticker": t}
        for label, key in methods.items():
            o = opt.get(key)
            w = o.weights.get(t, 0.0) if o and o.weights else 0.0
            row[label] = f"{w * 100:.1f} %"
        weight_rows.append(row)
    st.caption("**Weights comparison**")
    st.dataframe(weight_rows, use_container_width=True, hide_index=True)

    # ── Metrics comparison table ───────────────────────────────────────────────
    metric_rows = []
    for label, key in methods.items():
        o = opt.get(key)
        if o is None:
            continue
        metric_rows.append({
            "Method":          label,
            "Exp. Return":     _pct(o.expected_return),
            "Volatility":      _pct(o.volatility),
            "Sharpe":          _num(o.sharpe),
            "Max Drawdown":    _pct(o.max_drawdown),
        })
    st.caption("**Metrics comparison**")
    st.dataframe(metric_rows, use_container_width=True, hide_index=True)

    # ── Apply buttons ──────────────────────────────────────────────────────────
    st.caption("**Apply optimised weights to portfolio**")
    apply_cols = st.columns(3)
    apply_map = [
        ("Max Sharpe",      "max_sharpe",      apply_cols[0]),
        ("Min Variance",    "min_variance",     apply_cols[1]),
        ("Black-Litterman", "black_litterman",  apply_cols[2]),
    ]
    for label, key, col in apply_map:
        o = opt.get(key)
        disabled = not (o and o.weights and not math.isnan(o.volatility))
        if col.button(f"Apply {label}", key=f"apply_{key}", disabled=disabled):
            new_assets = []
            for t in tickers:
                w = o.weights.get(t, 0.0)
                new_assets.append(Asset(ticker=t, weight=w))
            pf.assets = new_assets
            session.set_portfolio(pf)
            session.clear_result()
            st.success(f"{label} weights applied — click Analyse Portfolio to refresh.")
            st.rerun()
