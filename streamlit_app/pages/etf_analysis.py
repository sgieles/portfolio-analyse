"""ETF Analysis page — renders within the Company Look-up for ETF tickers."""

from __future__ import annotations

import math
import sys
from pathlib import Path

_ROOT = str(Path(__file__).resolve().parent.parent.parent)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import plotly.graph_objects as go
import streamlit as st
import yfinance as yf

from research.data.etf_fetcher import ETFProfile, fetch_etf_profile, fetch_etf_price_history
from research.analytics.etf_scorer import ETFAnalysis, score_etf
from streamlit_app.styles.theme import (
    ACCENT, BG_SECONDARY, BG_TERTIARY, BORDER, DANGER, PLOTLY_TEMPLATE,
    SUCCESS, TEXT_PRIMARY, TEXT_SECONDARY, WARNING,
)

_NAN = float("nan")

_SIGNAL_COLORS = {
    "Excellent": SUCCESS,
    "Good":      "#4ade80",
    "Neutral":   WARNING,
    "Weak":      "#f97316",
    "Poor":      DANGER,
}

_STAR_FILL = "★"
_STAR_EMPTY = "☆"


# ── Cached fetchers ────────────────────────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def _cached_etf_profile(ticker: str) -> ETFProfile:
    return fetch_etf_profile(ticker)


@st.cache_data(ttl=3600, show_spinner=False)
def _cached_price_history(ticker: str, period: str = "5y"):
    return fetch_etf_price_history(ticker, period=period)


@st.cache_data(ttl=3600, show_spinner=False)
def _cached_spy_history():
    return fetch_etf_price_history("SPY", period="5y")


# ── UI helpers ─────────────────────────────────────────────────────────────────

def _kpi(col, label: str, value: str, color: str = TEXT_PRIMARY, sub: str = "") -> None:
    sub_html = (
        f'<div style="font-size:10px; color:{TEXT_SECONDARY}; margin-top:3px;">{sub}</div>'
        if sub else ""
    )
    col.markdown(
        f'<div style="background:{BG_SECONDARY}; border:1px solid {BORDER}; border-radius:8px;'
        f'padding:14px 16px; text-align:center;">'
        f'<div style="font-size:9px; color:{TEXT_SECONDARY}; text-transform:uppercase;'
        f'letter-spacing:0.07em; margin-bottom:4px;">{label}</div>'
        f'<div style="font-size:22px; font-weight:700; color:{color};">{value}</div>'
        f'{sub_html}'
        f'</div>',
        unsafe_allow_html=True,
    )


def _section(title: str) -> None:
    st.markdown(
        f"<div style='border-left:3px solid {ACCENT}; padding-left:10px; margin:18px 0 10px 0;'>"
        f"<span style='font-size:11px; font-weight:700; color:{ACCENT}; text-transform:uppercase;"
        f"letter-spacing:0.08em;'>{title}</span></div>",
        unsafe_allow_html=True,
    )


def _score_bar(score: float, label: str) -> None:
    if math.isnan(score):
        st.caption(f"{label}: N/A")
        return
    pct = int(max(0, min(100, score)))
    color = SUCCESS if pct >= 62 else DANGER if pct <= 38 else WARNING
    st.markdown(
        f'<div style="margin-bottom:6px;">'
        f'<div style="font-size:11px; color:{TEXT_SECONDARY}; margin-bottom:3px;">{label}</div>'
        f'<div style="background:{BG_TERTIARY}; border-radius:4px; height:8px; overflow:hidden;">'
        f'<div style="background:{color}; width:{pct}%; height:100%; border-radius:4px;"></div>'
        f'</div>'
        f'<div style="font-size:10px; color:{color}; text-align:right;">{pct}/100</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def _pct(v: float, digits: int = 1, sign: bool = False) -> str:
    if math.isnan(v):
        return "—"
    fmt = f"{'+' if sign else ''}.{digits}f"
    return f"{v * 100:{fmt}}%"


def _fmt(v: float, digits: int = 1, suffix: str = "") -> str:
    return "—" if math.isnan(v) else f"{v:.{digits}f}{suffix}"


def _stars(rating: int) -> str:
    return _STAR_FILL * rating + _STAR_EMPTY * (5 - rating) if 1 <= rating <= 5 else "—"


def _score_color(s: float) -> str:
    if math.isnan(s):
        return TEXT_SECONDARY
    return SUCCESS if s >= 62 else DANGER if s <= 38 else WARNING


def _bar_chart(labels: list[str], values: list[float],
               title: str, yaxis: str = "Weight (%)",
               color: str = ACCENT) -> go.Figure:
    t = PLOTLY_TEMPLATE["layout"]
    colors = [SUCCESS if v >= 0 else DANGER for v in values]
    fig = go.Figure(go.Bar(
        x=labels, y=values,
        marker_color=colors if any(v < 0 for v in values) else color,
        text=[f"{v:.1f}%" for v in values],
        textposition="outside",
        textfont=dict(color=TEXT_PRIMARY, size=10),
    ))
    fig.update_layout(
        title=dict(text=title, font=dict(size=13, color=TEXT_PRIMARY)),
        yaxis_title=yaxis, bargap=0.35,
        paper_bgcolor=t["paper_bgcolor"], plot_bgcolor=t["plot_bgcolor"],
        font=t["font"], margin=t["margin"], height=320,
    )
    fig.update_xaxes(gridcolor=BORDER, linecolor=BORDER)
    fig.update_yaxes(gridcolor=BORDER, linecolor=BORDER, zeroline=True, zerolinecolor=BORDER)
    return fig


def _pie_chart(labels: list[str], values: list[float], title: str) -> go.Figure:
    t = PLOTLY_TEMPLATE["layout"]
    fig = go.Figure(go.Pie(
        labels=labels, values=values,
        hole=0.4, textinfo="label+percent",
        textfont=dict(color=TEXT_PRIMARY, size=11),
        marker=dict(line=dict(color=BG_SECONDARY, width=2)),
    ))
    fig.update_layout(
        title=dict(text=title, font=dict(size=13, color=TEXT_PRIMARY)),
        paper_bgcolor=t["paper_bgcolor"],
        font=t["font"], margin=dict(l=10, r=10, t=40, b=10), height=340,
        legend=dict(bgcolor=t["legend"]["bgcolor"], font=dict(size=10)),
        showlegend=True,
    )
    return fig


# ── Tab renderers ──────────────────────────────────────────────────────────────

def _render_overview(a: ETFAnalysis) -> None:
    p = a.profile
    sig_color = _SIGNAL_COLORS.get(a.signal, WARNING)

    # Header KPI strip
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    _kpi(c1, "ETF Score",    f"{a.etf_score:.0f} / 100", sig_color, a.signal)
    _kpi(c2, "Expense Ratio",
         _pct(p.expense_ratio, 2) if not math.isnan(p.expense_ratio) else "—",
         SUCCESS if not math.isnan(p.expense_ratio) and p.expense_ratio < 0.002 else
         WARNING if not math.isnan(p.expense_ratio) and p.expense_ratio < 0.005 else DANGER)
    _kpi(c3, "AUM",
         f"${p.aum/1e9:.1f}B" if not math.isnan(p.aum) and p.aum >= 1e9
         else f"${p.aum/1e6:.0f}M" if not math.isnan(p.aum) else "—")
    _kpi(c4, "Div. Yield",   _pct(p.dividend_yield, 2), sub=p.category or "")
    _kpi(c5, "1Y Return",    _pct(a.return_1y, 1, sign=True),
         SUCCESS if not math.isnan(a.return_1y) and a.return_1y > 0 else DANGER)
    _kpi(c6, "Sharpe (1Y)",  _fmt(a.sharpe_1y, 2),
         SUCCESS if not math.isnan(a.sharpe_1y) and a.sharpe_1y > 0.8 else
         WARNING if not math.isnan(a.sharpe_1y) and a.sharpe_1y > 0 else DANGER)

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

    # Fund metadata card
    meta_items = [
        ("Fund Family",       p.fund_family or "—"),
        ("Category",          p.category    or "—"),
        ("# Holdings",        str(p.n_holdings) if p.n_holdings else "—"),
        ("NAV",               f"${p.nav:.2f}" if not math.isnan(p.nav) else "—"),
        ("Beta (3Y)",         _fmt(p.beta_3y, 2)),
        ("Morningstar Risk",  f"{p.morningstar_risk}/5" if p.morningstar_risk else "—"),
        ("Morningstar Rating", _stars(p.morningstar_rating)),
    ]
    cols = st.columns(len(meta_items))
    for col, (label, val) in zip(cols, meta_items):
        col.markdown(
            f'<div style="text-align:center; padding:8px 4px;">'
            f'<div style="font-size:9px; color:{TEXT_SECONDARY}; text-transform:uppercase;'
            f'letter-spacing:0.06em; margin-bottom:3px;">{label}</div>'
            f'<div style="font-size:13px; font-weight:600; color:{TEXT_PRIMARY};">{val}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    # Strengths / Weaknesses
    if a.strengths or a.weaknesses:
        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
        sw_col, wk_col = st.columns(2)
        with sw_col:
            st.markdown(
                f"<div style='font-size:11px; font-weight:700; color:{SUCCESS};'>"
                "Strengths</div>", unsafe_allow_html=True,
            )
            for s in a.strengths:
                st.markdown(f"- {s}")
        with wk_col:
            st.markdown(
                f"<div style='font-size:11px; font-weight:700; color:{DANGER};'>"
                "Weaknesses</div>", unsafe_allow_html=True,
            )
            for w in a.weaknesses:
                st.markdown(f"- {w}")

    # Description
    if p.description:
        with st.expander("Fund description"):
            st.write(p.description)


def _render_holdings(a: ETFAnalysis) -> None:
    _section("Top Holdings")
    p = a.profile

    if not p.top_holdings:
        st.caption("Holdings data not available via yfinance for this ETF.")
        return

    # KPI cards
    hc1, hc2, hc3 = st.columns(3)
    _kpi(hc1, "# Holdings",    str(p.n_holdings) if p.n_holdings else "—")
    _kpi(hc2, "Top-10 Weight",
         _pct(a.top10_weight, 1),
         DANGER if not math.isnan(a.top10_weight) and a.top10_weight > 0.60 else
         WARNING if not math.isnan(a.top10_weight) and a.top10_weight > 0.35 else SUCCESS)
    _kpi(hc3, "Sector HHI",
         _fmt(a.hhi_sector, 3),
         DANGER if not math.isnan(a.hhi_sector) and a.hhi_sector > 0.30 else
         WARNING if not math.isnan(a.hhi_sector) and a.hhi_sector > 0.15 else SUCCESS,
         sub="0=diversified, 1=concentrated")

    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

    tbl_col, pie_col = st.columns([3, 2])

    with tbl_col:
        rows = []
        for i, h in enumerate(p.top_holdings, 1):
            wt = h.get("weight", _NAN)
            rows.append({
                "#":       i,
                "Symbol":  h.get("symbol", "—"),
                "Name":    h.get("name", "—"),
                "Weight":  _pct(wt, 2) if not math.isnan(wt) else "—",
            })
        st.dataframe(rows, use_container_width=True, hide_index=True)

    with pie_col:
        top_n = p.top_holdings[:8]
        valid  = [(h.get("symbol", "?"), h.get("weight", 0))
                  for h in top_n if not math.isnan(h.get("weight", _NAN))]
        if valid:
            labels = [v[0] for v in valid]
            vals   = [v[1] * 100 for v in valid]
            # Add "Others" bucket
            shown = sum(vals) / 100
            if shown < 0.99:
                labels.append("Others")
                vals.append((1 - shown) * 100)
            fig = _pie_chart(labels, vals, "Top Holding Weights")
            st.plotly_chart(fig, use_container_width=True)


def _render_exposure(a: ETFAnalysis) -> None:
    p = a.profile

    if p.sector_weights:
        _section("Sector Allocation")
        sw_sorted = sorted(p.sector_weights.items(), key=lambda x: x[1], reverse=True)
        labels = [k for k, _ in sw_sorted]
        vals   = [v * 100 for _, v in sw_sorted]
        exp_col, table_col = st.columns([3, 2])
        with exp_col:
            fig = _bar_chart(labels, vals, "Sector Weights", "Weight (%)", ACCENT)
            st.plotly_chart(fig, use_container_width=True)
        with table_col:
            rows = [{"Sector": k, "Weight": f"{v*100:.1f}%"} for k, v in sw_sorted]
            st.dataframe(rows, use_container_width=True, hide_index=True)
    else:
        st.caption("Sector allocation not available for this ETF.")

    if p.asset_allocation:
        _section("Asset Allocation")
        aa_sorted = sorted(p.asset_allocation.items(), key=lambda x: x[1], reverse=True)
        labels = [k for k, _ in aa_sorted]
        vals   = [v * 100 for _, v in aa_sorted]
        fig = _pie_chart(labels, vals, "Asset Class Breakdown")
        aa_col, _ = st.columns([2, 3])
        with aa_col:
            st.plotly_chart(fig, use_container_width=True)

    if p.country_weights:
        _section("Geographic Exposure")
        cw_sorted = sorted(p.country_weights.items(), key=lambda x: x[1], reverse=True)[:10]
        labels = [k for k, _ in cw_sorted]
        vals   = [v * 100 for _, v in cw_sorted]
        fig = _bar_chart(labels, vals, "Country / Region Weights", "Weight (%)", ACCENT)
        st.plotly_chart(fig, use_container_width=True)


def _render_performance(a: ETFAnalysis, prices: "pd.DataFrame", spy: "pd.DataFrame") -> None:
    import pandas as pd

    _section("Performance & Risk")

    # Metric strip
    p1, p2, p3, p4, p5 = st.columns(5)
    _kpi(p1, "1Y Return",     _pct(a.return_1y,    1, True),
         SUCCESS if not math.isnan(a.return_1y) and a.return_1y > 0 else DANGER)
    _kpi(p2, "3Y Ann. Return", _pct(a.return_3y_ann, 1, True),
         SUCCESS if not math.isnan(a.return_3y_ann) and a.return_3y_ann > 0 else DANGER)
    _kpi(p3, "Volatility (1Y)", _pct(a.volatility_1y, 1),
         SUCCESS if not math.isnan(a.volatility_1y) and a.volatility_1y < 0.15 else
         WARNING if not math.isnan(a.volatility_1y) and a.volatility_1y < 0.22 else DANGER)
    _kpi(p4, "Max Drawdown",  _pct(a.max_drawdown,  1, True),
         DANGER if not math.isnan(a.max_drawdown) and a.max_drawdown < -0.25 else
         WARNING if not math.isnan(a.max_drawdown) and a.max_drawdown < -0.15 else SUCCESS)
    _kpi(p5, "Tracking Error", _pct(a.tracking_error, 2) if not math.isnan(a.tracking_error) else "—",
         sub="vs SPY")

    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

    if prices.empty or "Close" not in prices.columns:
        st.caption("Price history not available for chart.")
        return

    t = PLOTLY_TEMPLATE["layout"]
    close = prices["Close"].dropna()
    base  = float(close.iloc[0])
    growth = (close / base * 100)

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=growth.index, y=growth.values,
        mode="lines", name=a.ticker,
        line=dict(color=ACCENT, width=2),
    ))

    if not spy.empty and "Close" in spy.columns:
        spy_close = spy["Close"].dropna()
        spy_common = spy_close.reindex(close.index, method="ffill").dropna()
        spy_base = float(spy_common.iloc[0]) if not spy_common.empty else None
        if spy_base:
            spy_growth = spy_common / spy_base * 100
            fig.add_trace(go.Scatter(
                x=spy_growth.index, y=spy_growth.values,
                mode="lines", name="SPY (benchmark)",
                line=dict(color=TEXT_SECONDARY, width=1.5, dash="dash"),
            ))

    fig.update_layout(
        title=dict(text="Growth of 100 (indexed)", font=dict(size=13, color=TEXT_PRIMARY)),
        yaxis_title="Indexed value",
        paper_bgcolor=t["paper_bgcolor"], plot_bgcolor=t["plot_bgcolor"],
        font=t["font"], margin=t["margin"], height=320,
        legend=dict(bgcolor=t["legend"]["bgcolor"]),
        hovermode="x unified",
    )
    fig.update_xaxes(gridcolor=BORDER, linecolor=BORDER)
    fig.update_yaxes(gridcolor=BORDER, linecolor=BORDER)
    st.plotly_chart(fig, use_container_width=True)


def _render_score(a: ETFAnalysis) -> None:
    _section("ETF Score Breakdown")

    sig_color = _SIGNAL_COLORS.get(a.signal, WARNING)
    st.markdown(
        f'<div style="background:{BG_SECONDARY}; border:2px solid {sig_color}; border-radius:10px;'
        f'padding:16px 22px; margin-bottom:16px; display:flex; align-items:center; gap:20px;">'
        f'<div style="font-size:26px; font-weight:800; color:{sig_color};">{a.signal}</div>'
        f'<div>'
        f'<div style="font-size:9px; color:{TEXT_SECONDARY}; text-transform:uppercase; letter-spacing:0.07em;">ETF Score</div>'
        f'<div style="font-size:28px; font-weight:800; color:{sig_color};">{a.etf_score:.0f}'
        f'<span style="font-size:14px; font-weight:400;">/100</span></div>'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    weights = {"Cost": 25, "Diversification": 30, "Performance": 25, "Risk": 20}
    for comp, score in a.score_components.items():
        _score_bar(score, f"{comp} ({weights.get(comp, 25)}% weight)")

    with st.expander("How the ETF Score works"):
        st.markdown(f"""
**Composite score (0-100) — weights:**

| Dimension | Weight | What it measures |
|-----------|--------|-----------------|
| Diversification | 30% | Number of holdings, top-10 concentration, sector spread (HHI) |
| Cost | 25% | Annual expense ratio vs benchmarks |
| Performance | 25% | Risk-adjusted returns (Sharpe), 1Y and 3Y return |
| Risk | 20% | Volatility, max drawdown, tracking error vs SPY |

**Signal thresholds:** Excellent ≥72 · Good ≥60 · Neutral ≥45 · Weak ≥32 · Poor <32
        """)


# ── Main entry point ───────────────────────────────────────────────────────────

def render_detail(ticker: str) -> None:
    """Render the full ETF analysis page for *ticker*."""
    with st.spinner(f"Loading ETF data for {ticker}…"):
        profile  = _cached_etf_profile(ticker)
        prices   = _cached_price_history(ticker)
        spy      = _cached_spy_history()

    analysis = score_etf(ticker, profile, prices, spy)

    # Fund header
    st.markdown(
        f'<div style="background:{BG_SECONDARY}; border:1px solid {BORDER}; border-radius:8px;'
        f'padding:14px 20px; margin-bottom:14px;">'
        f'<div style="font-size:20px; font-weight:800; color:{TEXT_PRIMARY};">'
        f'{profile.name or ticker}'
        f'<span style="font-size:13px; font-weight:400; color:{TEXT_SECONDARY}; margin-left:10px;">{ticker}</span>'
        f'</div>'
        f'<div style="font-size:12px; color:{TEXT_SECONDARY}; margin-top:4px;">'
        f'{profile.fund_family or "—"} · {profile.category or "—"} · ETF'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    tab_ov, tab_hold, tab_exp, tab_perf, tab_score = st.tabs(
        ["📊 Overview", "🏢 Holdings", "🗺️ Exposure", "📈 Performance", "⭐ Score"]
    )

    with tab_ov:
        _render_overview(analysis)
    with tab_hold:
        _render_holdings(analysis)
    with tab_exp:
        _render_exposure(analysis)
    with tab_perf:
        _render_performance(analysis, prices, spy)
    with tab_score:
        _render_score(analysis)
