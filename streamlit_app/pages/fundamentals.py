"""Fundamental analysis detail view — Phase 18.

Renders the full breakdown of a company's fundamental score:
sub-scores, 5-/10-year trend charts, quarterly trends, peer positioning,
and strengths/weaknesses.

Entry point:  render_detail(ticker, funds, quarterly, analysis)
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

_ROOT = str(Path(__file__).resolve().parent.parent.parent)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
from typing import Sequence

import plotly.graph_objects as go
import streamlit as st

from research.analytics.fundamental_scorer import FundamentalAnalysis
from research.models.fundamentals import AnnualFundamentals, QuarterlyFundamentals
from streamlit_app.styles.theme import (
    ACCENT, BG_SECONDARY, BORDER, DANGER, PLOTLY_TEMPLATE,
    SUCCESS, TEXT_PRIMARY, TEXT_SECONDARY, WARNING,
)

_NAN = float("nan")


# ── Shared helpers ────────────────────────────────────────────────────────────

def _pct(v: float, digits: int = 1) -> str:
    return "—" if math.isnan(v) else f"{v * 100:.{digits}f}%"


def _x(v: float, digits: int = 2) -> str:
    return "—" if math.isnan(v) else f"{v:.{digits}f}×"


def _bn(v: float) -> str:
    if math.isnan(v):
        return "—"
    if abs(v) >= 1e12:
        return f"${v/1e12:.1f}T"
    if abs(v) >= 1e9:
        return f"${v/1e9:.1f}B"
    if abs(v) >= 1e6:
        return f"${v/1e6:.0f}M"
    return f"${v:,.0f}"


def _color(v: float) -> str:
    if math.isnan(v):
        return TEXT_SECONDARY
    if v >= 65:
        return SUCCESS
    if v >= 40:
        return WARNING
    return DANGER


def _apply_theme(fig: go.Figure, height: int = 260) -> go.Figure:
    t = PLOTLY_TEMPLATE["layout"]
    fig.update_layout(
        paper_bgcolor=t["paper_bgcolor"], plot_bgcolor=t["plot_bgcolor"],
        font=t["font"], margin=t["margin"], height=height,
        legend=dict(bgcolor=t["legend"]["bgcolor"],
                    bordercolor=t["legend"]["bordercolor"],
                    orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    fig.update_xaxes(gridcolor=BORDER, zerolinecolor=BORDER)
    fig.update_yaxes(gridcolor=BORDER, zerolinecolor=BORDER)
    return fig


def _h3(text: str) -> None:
    st.markdown(
        f"<h3 style='color:{TEXT_PRIMARY}; margin:16px 0 8px 0; font-size:16px;'>{text}</h3>",
        unsafe_allow_html=True,
    )


def _divider() -> None:
    st.markdown(
        f"<hr style='border:none; border-top:1px solid {BORDER}; margin:12px 0 14px 0;'>",
        unsafe_allow_html=True,
    )


# ── Score card strip ──────────────────────────────────────────────────────────

def _render_score_cards(a: FundamentalAnalysis) -> None:
    cards = [
        ("Overall Fund.", a.fundamental_score),
        ("Growth",        a.growth_score),
        ("Profitability", a.profitability_score),
        ("Cap. Efficiency", a.capital_efficiency_score),
        ("Balance Sheet", a.balance_sheet_score),
    ]
    cols = st.columns(len(cards))
    for col, (label, v) in zip(cols, cards):
        c = _color(v)
        val = f"{v:.0f}" if not math.isnan(v) else "—"
        col.markdown(
            f"""<div style="background:{c}11; border:2px solid {c}55;
                        border-radius:10px; padding:12px 10px; text-align:center;">
                <div style="font-size:9px; color:{TEXT_SECONDARY}; text-transform:uppercase;
                            letter-spacing:.07em; margin-bottom:4px;">{label}</div>
                <div style="font-size:26px; font-weight:800; color:{c};">{val}</div>
            </div>""",
            unsafe_allow_html=True,
        )
    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)


# ── Trend indicators ──────────────────────────────────────────────────────────

def _render_trend_badges(a: FundamentalAnalysis) -> None:
    _TREND_ICON = {
        "expanding": ("▲", SUCCESS), "compressing": ("▼", DANGER), "stable": ("▶", WARNING),
        "accelerating": ("▲▲", SUCCESS), "decelerating": ("▼▼", DANGER),
    }
    items = [
        ("Margin Trend", a.margin_trend),
        ("Revenue Trend", a.revenue_trend),
    ]
    if not math.isnan(a.sector_percentile):
        pct_label = f"{a.sector_percentile:.0f}th pct"
        c = SUCCESS if a.sector_percentile >= 75 else DANGER if a.sector_percentile < 25 else WARNING
        st.markdown(
            f"<span style='background:{c}22; color:{c}; border-radius:4px; "
            f"padding:3px 8px; font-size:12px; font-weight:600;'>"
            f"Sector rank {pct_label}</span>",
            unsafe_allow_html=True,
        )

    badge_html = ""
    for label, val in items:
        icon, c = _TREND_ICON.get(val, ("◆", TEXT_SECONDARY))
        badge_html += (
            f"<span style='background:{c}22; color:{c}; border-radius:4px; "
            f"padding:3px 8px; font-size:12px; font-weight:600; margin-right:6px;'>"
            f"{icon} {label}: {val.capitalize()}</span>"
        )
    st.markdown(badge_html, unsafe_allow_html=True)
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)


# ── Key metrics grid ──────────────────────────────────────────────────────────

def _render_key_metrics(a: FundamentalAnalysis, f0: AnnualFundamentals) -> None:
    _h3("Key Metrics")
    metrics = [
        ("Rev CAGR 3Y",   _pct(a.revenue_cagr_3y)),
        ("EPS CAGR 3Y",   _pct(a.eps_cagr_3y)),
        ("FCF CAGR 3Y",   _pct(a.fcf_cagr_3y)),
        ("ROIC",          _pct(a.roic)),
        ("ROE",           _pct(f0.return_on_equity)),
        ("ROA",           _pct(f0.return_on_assets)),
        ("Gross Margin",  _pct(f0.gross_margin)),
        ("Op. Margin",    _pct(f0.operating_margin)),
        ("Net Margin",    _pct(f0.net_margin)),
        ("FCF Margin",    _pct(a.fcf_margin)),
        ("D/E Ratio",     _x(f0.debt_to_equity)),
        ("Interest Cov.", _x(a.interest_coverage, 1)),
        ("Current Ratio", _x(a.current_ratio, 2)),
        ("Free Cash Flow", _bn(f0.free_cash_flow)),
        ("Net Income",    _bn(f0.net_income)),
        ("Revenue",       _bn(f0.revenue)),
    ]
    kpi_style = (
        f"background:{BG_SECONDARY}; border:1px solid {BORDER}; border-radius:6px;"
        " padding:8px 10px; text-align:center; margin-bottom:8px;"
    )
    cols = st.columns(8)
    for i, (label, value) in enumerate(metrics):
        cols[i % 8].markdown(
            f"""<div style="{kpi_style}">
                <div style="font-size:8px; color:{TEXT_SECONDARY}; text-transform:uppercase;
                            letter-spacing:.07em; margin-bottom:3px;">{label}</div>
                <div style="font-size:13px; font-weight:600; color:{TEXT_PRIMARY};">{value}</div>
            </div>""",
            unsafe_allow_html=True,
        )


# ── Annual trend charts ───────────────────────────────────────────────────────

def _render_annual_charts(funds: list[AnnualFundamentals], view_years: int) -> None:
    _h3(f"Annual Trends — {view_years}-Year View")
    shown = funds[:view_years]
    years = [f.fiscal_year for f in reversed(shown)]

    def _vals(attr: str) -> list[float | None]:
        return [v if not math.isnan(v) else None
                for v in [getattr(f, attr) for f in reversed(shown)]]

    # Revenue + Net Income
    ch1, ch2 = st.columns(2)
    with ch1:
        fig = go.Figure()
        fig.add_trace(go.Bar(x=years, y=[v/1e9 if v else None for v in _vals("revenue")],
                             name="Revenue", marker_color=ACCENT))
        fig.add_trace(go.Bar(x=years, y=[v/1e9 if v else None for v in _vals("net_income")],
                             name="Net Income", marker_color=SUCCESS))
        fig.update_layout(title="Revenue & Net Income ($B)", barmode="group")
        st.plotly_chart(_apply_theme(fig), use_container_width=True)

    with ch2:
        fig = go.Figure()
        for attr, name, color in [
            ("gross_margin", "Gross", ACCENT),
            ("operating_margin", "Op.", "#2563eb"),
            ("net_margin", "Net", SUCCESS),
        ]:
            vals = [v * 100 if v is not None else None for v in _vals(attr)]
            fig.add_trace(go.Scatter(x=years, y=vals, name=name,
                                     line=dict(color=color, width=2),
                                     mode="lines+markers"))
        fig.update_layout(title="Margins %", yaxis_title="%")
        st.plotly_chart(_apply_theme(fig), use_container_width=True)

    # EPS + Free Cash Flow
    ch3, ch4 = st.columns(2)
    with ch3:
        fig = go.Figure(go.Bar(
            x=years, y=_vals("eps_diluted"),
            marker_color=[SUCCESS if (v or 0) >= 0 else DANGER for v in _vals("eps_diluted")],
            name="EPS",
        ))
        fig.update_layout(title="EPS (diluted, USD)")
        st.plotly_chart(_apply_theme(fig), use_container_width=True)

    with ch4:
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=years, y=[v/1e9 if v else None for v in _vals("operating_cash_flow")],
            name="Op. CF", marker_color=ACCENT))
        fig.add_trace(go.Bar(
            x=years, y=[v/1e9 if v else None for v in _vals("free_cash_flow")],
            name="Free CF", marker_color=SUCCESS))
        fig.update_layout(title="Cash Flow ($B)", barmode="group")
        st.plotly_chart(_apply_theme(fig), use_container_width=True)

    # ROIC / ROE / ROA   +   Debt
    ch5, ch6 = st.columns(2)
    with ch5:
        roics = [_compute_roic_from(f) for f in reversed(shown)]
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=years, y=[v * 100 if v is not None else None for v in roics],
            name="ROIC", line=dict(color=ACCENT, width=2), mode="lines+markers"))
        fig.add_trace(go.Scatter(
            x=years, y=[v * 100 if v is not None else None for v in _vals("return_on_equity")],
            name="ROE", line=dict(color=SUCCESS, width=2), mode="lines+markers"))
        fig.add_trace(go.Scatter(
            x=years, y=[v * 100 if v is not None else None for v in _vals("return_on_assets")],
            name="ROA", line=dict(color="#2563eb", width=2), mode="lines+markers"))
        fig.update_layout(title="Capital Returns %", yaxis_title="%")
        st.plotly_chart(_apply_theme(fig), use_container_width=True)

    with ch6:
        fig = go.Figure(go.Bar(
            x=years, y=_vals("debt_to_equity"),
            marker_color=[DANGER if (v or 0) > 2 else WARNING if (v or 0) > 1 else SUCCESS
                          for v in _vals("debt_to_equity")],
            name="D/E Ratio",
        ))
        fig.update_layout(title="Debt / Equity Ratio")
        st.plotly_chart(_apply_theme(fig), use_container_width=True)


def _compute_roic_from(f: AnnualFundamentals) -> float | None:
    if not (math.isnan(f.operating_income) or math.isnan(f.total_equity)):
        nopat = f.operating_income * 0.75
        debt = f.total_debt if not math.isnan(f.total_debt) else 0.0
        cash = f.cash if not math.isnan(f.cash) else 0.0
        ic = f.total_equity + debt - cash
        if ic > 0:
            return nopat / ic
    return None


# ── Quarterly trend charts ────────────────────────────────────────────────────

def _render_quarterly_charts(quarters: list[QuarterlyFundamentals]) -> None:
    if not quarters:
        st.info("No quarterly data available.")
        return

    _h3("Quarterly Trends")
    shown = list(reversed(quarters[:8]))
    labels = [f"Q{q.fiscal_quarter} {q.fiscal_year}" for q in shown]

    ch1, ch2 = st.columns(2)
    with ch1:
        fig = go.Figure(go.Bar(
            x=labels,
            y=[q.revenue / 1e9 if not math.isnan(q.revenue) else None for q in shown],
            marker_color=ACCENT, name="Revenue",
        ))
        fig.update_layout(title="Quarterly Revenue ($B)")
        st.plotly_chart(_apply_theme(fig), use_container_width=True)

    with ch2:
        fig = go.Figure()
        for attr, name, color in [
            ("gross_margin", "Gross", ACCENT),
            ("operating_margin", "Op.", "#2563eb"),
            ("net_margin", "Net", SUCCESS),
        ]:
            vals = [getattr(q, attr) * 100 if not math.isnan(getattr(q, attr)) else None
                    for q in shown]
            fig.add_trace(go.Scatter(x=labels, y=vals, name=name,
                                     line=dict(color=color, width=2),
                                     mode="lines+markers"))
        fig.update_layout(title="Quarterly Margins %", yaxis_title="%")
        st.plotly_chart(_apply_theme(fig), use_container_width=True)

    ch3, ch4 = st.columns(2)
    with ch3:
        fig = go.Figure(go.Bar(
            x=labels,
            y=[q.eps_diluted if not math.isnan(q.eps_diluted) else None for q in shown],
            marker_color=[SUCCESS if (q.eps_diluted or 0) >= 0 else DANGER for q in shown],
            name="EPS",
        ))
        fig.update_layout(title="Quarterly EPS (diluted)")
        st.plotly_chart(_apply_theme(fig), use_container_width=True)

    with ch4:
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=labels,
            y=[q.free_cash_flow / 1e9 if not math.isnan(q.free_cash_flow) else None
               for q in shown],
            name="Free CF", marker_color=SUCCESS,
        ))
        fig.update_layout(title="Quarterly Free Cash Flow ($B)")
        st.plotly_chart(_apply_theme(fig), use_container_width=True)


# ── Strengths & Weaknesses ────────────────────────────────────────────────────

def _render_explainability(a: FundamentalAnalysis) -> None:
    _h3("Investment Signals")
    sw1, sw2 = st.columns(2)
    with sw1:
        st.markdown(
            f"<div style='font-size:13px; font-weight:700; color:{SUCCESS}; "
            f"margin-bottom:8px;'>✓ Strengths</div>",
            unsafe_allow_html=True,
        )
        if a.strengths:
            for s in a.strengths:
                st.markdown(
                    f"<div style='background:{SUCCESS}11; border-left:3px solid {SUCCESS}; "
                    f"padding:6px 10px; border-radius:0 4px 4px 0; margin-bottom:4px; "
                    f"font-size:13px; color:{TEXT_PRIMARY};'>{s}</div>",
                    unsafe_allow_html=True,
                )
        else:
            st.caption("No notable strengths identified.")

    with sw2:
        st.markdown(
            f"<div style='font-size:13px; font-weight:700; color:{DANGER}; "
            f"margin-bottom:8px;'>✗ Weaknesses</div>",
            unsafe_allow_html=True,
        )
        if a.weaknesses:
            for w in a.weaknesses:
                st.markdown(
                    f"<div style='background:{DANGER}11; border-left:3px solid {DANGER}; "
                    f"padding:6px 10px; border-radius:0 4px 4px 0; margin-bottom:4px; "
                    f"font-size:13px; color:{TEXT_PRIMARY};'>{w}</div>",
                    unsafe_allow_html=True,
                )
        else:
            st.caption("No notable weaknesses identified.")


# ── Main entry point ──────────────────────────────────────────────────────────

def render_detail(
    ticker: str,
    funds: list[AnnualFundamentals],
    quarters: list[QuarterlyFundamentals],
    analysis: FundamentalAnalysis,
) -> None:
    """Render the full fundamental breakdown for one ticker."""
    if not funds:
        st.warning(f"No fundamental data available for {ticker}.")
        return

    _render_score_cards(analysis)
    _render_trend_badges(analysis)
    _divider()
    _render_key_metrics(analysis, funds[0])
    _divider()

    # Annual trends with 5Y / 10Y toggle
    view_opts = ["5Y"]
    if len(funds) >= 8:
        view_opts.append("10Y")
    view = st.radio("View period", view_opts, horizontal=True,
                    key=f"fund_view_{ticker}", label_visibility="collapsed")
    view_years = 10 if view == "10Y" else 5
    _render_annual_charts(funds, view_years)

    _divider()

    # Quarterly section (lazy: only load when user expands)
    with st.expander("Quarterly Trends (last 8 quarters)", expanded=False):
        _render_quarterly_charts(quarters)

    _divider()
    _render_explainability(analysis)
