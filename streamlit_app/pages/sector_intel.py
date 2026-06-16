"""Sector Intelligence page — renders within the Research Hub."""

from __future__ import annotations

import math
import sys
from pathlib import Path

_ROOT = str(Path(__file__).resolve().parent.parent.parent)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import plotly.graph_objects as go
import streamlit as st

from research.analytics.sector_intelligence import analyze_sector
from research.data.sector_data import SECTOR_ETF_MAP, fetch_sector_prices
from research.cache.screener_cache import load_screener_rows
from research.data.universe import get_universe
from streamlit_app.styles.theme import (
    ACCENT, BG_SECONDARY, BORDER, DANGER, PLOTLY_TEMPLATE,
    SUCCESS, TEXT_PRIMARY, TEXT_SECONDARY, WARNING,
)

_SECTORS = sorted(SECTOR_ETF_MAP.keys())


def _pct(v: float, digits: int = 1) -> str:
    return "—" if math.isnan(v) else f"{v * 100:+.{digits}f}%"


def _val(v: float, digits: int = 1) -> str:
    return "—" if math.isnan(v) else f"{v:.{digits}f}"


def _outlook_color(outlook: str) -> str:
    return {"Bullish": SUCCESS, "Bearish": DANGER}.get(outlook, WARNING)


@st.cache_data(ttl=3600, show_spinner=False)
def _cached_sector_prices() -> dict:
    return fetch_sector_prices(period="1y")


def _all_screener_rows() -> list[dict]:
    """Combine screener cache rows from all universes."""
    rows: list[dict] = []
    seen: set[str] = set()
    for universe in ("S&P 500", "Nasdaq 100", "STOXX 600", "AEX"):
        tickers = get_universe(universe)
        cached = load_screener_rows(universe, tickers)
        if cached:
            for r in cached:
                t = r.get("ticker", "")
                if t not in seen:
                    seen.add(t)
                    rows.append(r)
    return rows


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
        f'<div style="font-size:20px; font-weight:700; color:{color};">{value}</div>'
        f'{sub_html}'
        f'</div>',
        unsafe_allow_html=True,
    )


def _section(title: str) -> None:
    st.markdown(
        f"<div style='border-left:3px solid {ACCENT}; padding-left:10px; margin:16px 0 10px 0;'>"
        f"<span style='font-size:11px; font-weight:700; color:{ACCENT}; text-transform:uppercase;"
        f"letter-spacing:0.08em;'>{title}</span></div>",
        unsafe_allow_html=True,
    )


def render() -> None:
    """Render the full Sector Intelligence section."""
    st.markdown(
        f"<p style='font-size:13px; color:{TEXT_SECONDARY}; margin-bottom:16px;'>"
        "Sector momentum, relative strength, fundamentals, SWOT and PESTLE analysis.</p>",
        unsafe_allow_html=True,
    )

    sector = st.selectbox(
        "Sector", _SECTORS,
        index=_SECTORS.index("Technology") if "Technology" in _SECTORS else 0,
        key="si_sector",
        label_visibility="collapsed",
    )

    with st.spinner(f"Loading sector data for {sector}…"):
        prices       = _cached_sector_prices()
        scrn_rows    = _all_screener_rows()
        intel        = analyze_sector(sector, prices, scrn_rows)

    etf = intel.etf
    oc = _outlook_color(intel.outlook)

    # ── KPI strip ─────────────────────────────────────────────────────────────
    k1, k2, k3, k4, k5, k6 = st.columns(6)
    _kpi(k1, "Outlook",      intel.outlook,
         oc)
    _kpi(k2, "Sector Score", f"{intel.sector_score:.0f} / 100",
         SUCCESS if intel.sector_score >= 62 else DANGER if intel.sector_score <= 38 else WARNING)
    _kpi(k3, "Mom 1M",       _pct(intel.momentum_1m),
         SUCCESS if not math.isnan(intel.momentum_1m) and intel.momentum_1m > 0 else DANGER)
    _kpi(k4, "Mom 3M",       _pct(intel.momentum_3m),
         SUCCESS if not math.isnan(intel.momentum_3m) and intel.momentum_3m > 0 else DANGER)
    _kpi(k5, "vs S&P 500 (12m)", _pct(intel.relative_strength_spy),
         SUCCESS if not math.isnan(intel.relative_strength_spy) and intel.relative_strength_spy > 0 else DANGER)
    _kpi(k6, "vs World (12m)",   _pct(intel.relative_strength_world),
         SUCCESS if not math.isnan(intel.relative_strength_world) and intel.relative_strength_world > 0 else DANGER)

    st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)

    # ── Momentum chart (bar) ───────────────────────────────────────────────────
    _section("Price Momentum")

    mom_labels = ["1 Month", "3 Months", "6 Months", "12 Months"]
    mom_values = [intel.momentum_1m, intel.momentum_3m,
                  intel.momentum_6m, intel.momentum_12m]
    mom_pct    = [v * 100 if not math.isnan(v) else 0 for v in mom_values]
    mom_colors = [SUCCESS if v >= 0 else DANGER for v in mom_pct]
    mom_text   = [_pct(v) for v in mom_values]

    rs_labels = ["vs S&P 500 (12m)", "vs World (12m)"]
    rs_vals   = [intel.relative_strength_spy, intel.relative_strength_world]
    rs_pct    = [v * 100 if not math.isnan(v) else 0 for v in rs_vals]

    col_mom, col_rs = st.columns([3, 2])

    with col_mom:
        fig = go.Figure(go.Bar(
            x=mom_labels, y=mom_pct, marker_color=mom_colors,
            text=mom_text, textposition="outside",
            textfont=dict(color=TEXT_PRIMARY, size=11),
        ))
        t = PLOTLY_TEMPLATE["layout"]
        fig.update_layout(
            title=dict(text=f"{etf} Momentum", font=dict(size=13, color=TEXT_PRIMARY)),
            yaxis_title="%", bargap=0.35, height=280,
            paper_bgcolor=t["paper_bgcolor"], plot_bgcolor=t["plot_bgcolor"],
            font=t["font"], margin=t["margin"],
        )
        fig.update_xaxes(gridcolor=BORDER, linecolor=BORDER)
        fig.update_yaxes(gridcolor=BORDER, linecolor=BORDER,
                         zeroline=True, zerolinecolor=BORDER)
        st.plotly_chart(fig, use_container_width=True)

    with col_rs:
        rs_colors = [SUCCESS if v >= 0 else DANGER for v in rs_pct]
        fig2 = go.Figure(go.Bar(
            x=rs_labels, y=rs_pct, marker_color=rs_colors,
            text=[_pct(v) for v in rs_vals], textposition="outside",
            textfont=dict(color=TEXT_PRIMARY, size=11),
        ))
        fig2.update_layout(
            title=dict(text="Relative Strength (12m)", font=dict(size=13, color=TEXT_PRIMARY)),
            yaxis_title="Excess return (%)", bargap=0.4, height=280,
            paper_bgcolor=t["paper_bgcolor"], plot_bgcolor=t["plot_bgcolor"],
            font=t["font"], margin=t["margin"],
        )
        fig2.update_xaxes(gridcolor=BORDER, linecolor=BORDER)
        fig2.update_yaxes(gridcolor=BORDER, linecolor=BORDER,
                          zeroline=True, zerolinecolor=BORDER)
        st.plotly_chart(fig2, use_container_width=True)

    # ── Sector fundamentals ───────────────────────────────────────────────────
    if intel.n_peers > 0:
        _section(f"Sector Fundamentals ({intel.n_peers} peers in screener cache)")
        f1, f2, f3, f4, f5 = st.columns(5)
        _kpi(f1, "Avg Overall",   _val(intel.avg_overall_score, 0))
        _kpi(f2, "Avg Fund.",     _val(intel.avg_fund_score, 0))
        _kpi(f3, "Avg Val.",      _val(intel.avg_val_score, 0))
        _kpi(f4, "Median Rev Gth", _pct(intel.avg_rev_growth, 0))
        _kpi(f5, "Median ROE",    _pct(intel.avg_roe, 0))

        st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)

        g1, g2, g3 = st.columns(3)
        _kpi(g1, "Median P/E",     _val(intel.avg_pe, 1) + "×" if not math.isnan(intel.avg_pe) else "—")
        _kpi(g2, "Median Fwd P/E", _val(intel.avg_fwd_pe, 1) + "×" if not math.isnan(intel.avg_fwd_pe) else "—")
        _kpi(g3, "Median Div Yield", _pct(intel.avg_div_yield, 1))

    elif scrn_rows:
        st.caption(
            f"No screener data found for the **{sector}** sector. "
            "Run the Screener for a universe containing this sector first."
        )
    else:
        st.caption("Run the Screener first to populate sector fundamentals.")

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    # ── SWOT ──────────────────────────────────────────────────────────────────
    _section("SWOT Analysis")
    sw_col, ot_col = st.columns(2)

    with sw_col:
        st.markdown(
            f"<div style='font-size:12px; font-weight:700; color:{SUCCESS}; margin-bottom:4px;'>"
            "✅ Strengths</div>", unsafe_allow_html=True,
        )
        for item in intel.swot.get("Strengths", []):
            st.markdown(f"- {item}")

        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
        st.markdown(
            f"<div style='font-size:12px; font-weight:700; color:{DANGER}; margin-bottom:4px;'>"
            "⚠️ Weaknesses</div>", unsafe_allow_html=True,
        )
        for item in intel.swot.get("Weaknesses", []):
            st.markdown(f"- {item}")

    with ot_col:
        st.markdown(
            f"<div style='font-size:12px; font-weight:700; color:{ACCENT}; margin-bottom:4px;'>"
            "🚀 Opportunities</div>", unsafe_allow_html=True,
        )
        for item in intel.swot.get("Opportunities", []):
            st.markdown(f"- {item}")

        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
        st.markdown(
            f"<div style='font-size:12px; font-weight:700; color:{WARNING}; margin-bottom:4px;'>"
            "🔴 Threats</div>", unsafe_allow_html=True,
        )
        for item in intel.swot.get("Threats", []):
            st.markdown(f"- {item}")

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    # ── PESTLE ────────────────────────────────────────────────────────────────
    _section("PESTLE Analysis")
    with st.expander("Show PESTLE", expanded=False):
        icons = {
            "Political": "🏛️", "Economic": "📈", "Social": "👥",
            "Technological": "💻", "Legal": "⚖️", "Environmental": "🌍",
        }
        for category, items in intel.pestle.items():
            icon = icons.get(category, "•")
            st.markdown(
                f"**{icon} {category}**"
            )
            for item in items:
                st.markdown(f"  - {item}")
