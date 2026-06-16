"""Insider Activity tab — renders within the Company Look-up."""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = str(Path(__file__).resolve().parent.parent.parent)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import math

import plotly.graph_objects as go
import streamlit as st

from research.data.insider_fetcher import fetch_insider_transactions
from research.analytics.insider_scorer import score_insider_activity
from streamlit_app.styles.theme import (
    ACCENT, BG_SECONDARY, BORDER, DANGER, PLOTLY_TEMPLATE,
    SUCCESS, TEXT_PRIMARY, TEXT_SECONDARY, WARNING,
)


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


def _signal_color(signal: str) -> str:
    return {"Bullish": SUCCESS, "Bearish": DANGER}.get(signal, WARNING)


@st.cache_data(ttl=3600, show_spinner=False)
def _cached_insider(ticker: str):
    return fetch_insider_transactions(ticker)


def render_detail(ticker: str) -> None:
    """Render insider activity section for *ticker*."""
    with st.spinner(f"Loading insider data for {ticker}…"):
        df = _cached_insider(ticker)

    analysis = score_insider_activity(ticker, df)

    if df.empty:
        st.info(
            f"No insider transaction data available for **{ticker}** via yfinance. "
            "Insider data is typically available for US-listed stocks only."
        )
        return

    # ── KPI strip ─────────────────────────────────────────────────────────────
    k1, k2, k3, k4, k5 = st.columns(5)
    sig_color = _signal_color(analysis.signal)
    _kpi(k1, "Signal (12m)",    analysis.signal,   sig_color)
    _kpi(k2, "Insider Score",   f"{analysis.insider_score:.0f} / 100", sig_color)
    _kpi(k3, "Buys (12m)",
         str(analysis.h12.n_buys),    SUCCESS,
         sub=f"${analysis.h12.value_bought/1e6:.1f}M")
    _kpi(k4, "Sells (12m)",
         str(analysis.h12.n_sells),   DANGER,
         sub=f"${analysis.h12.value_sold/1e6:.1f}M")
    _kpi(k5, "Net Buy / Sell",
         f"${(analysis.h12.value_bought - analysis.h12.value_sold)/1e6:+.1f}M",
         SUCCESS if analysis.h12.value_bought >= analysis.h12.value_sold else DANGER)

    st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)

    # ── Horizon comparison bar chart ──────────────────────────────────────────
    horizons  = ["3 months", "6 months", "12 months"]
    buy_vals  = [analysis.h3.value_bought,  analysis.h6.value_bought,  analysis.h12.value_bought]
    sell_vals = [analysis.h3.value_sold,    analysis.h6.value_sold,    analysis.h12.value_sold]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="Buys",  x=horizons,
        y=[v / 1e6 for v in buy_vals],
        marker_color=SUCCESS, text=[f"${v/1e6:.1f}M" for v in buy_vals],
        textposition="outside", textfont=dict(color=TEXT_PRIMARY, size=10),
    ))
    fig.add_trace(go.Bar(
        name="Sells", x=horizons,
        y=[-v / 1e6 for v in sell_vals],
        marker_color=DANGER,  text=[f"${v/1e6:.1f}M" for v in sell_vals],
        textposition="outside", textfont=dict(color=TEXT_PRIMARY, size=10),
    ))
    t = PLOTLY_TEMPLATE["layout"]
    fig.update_layout(
        title=dict(text="Insider Buy vs Sell Value by Horizon",
                   font=dict(size=13, color=TEXT_PRIMARY)),
        barmode="relative", yaxis_title="Value ($M)",
        paper_bgcolor=t["paper_bgcolor"], plot_bgcolor=t["plot_bgcolor"],
        font=t["font"], margin=t["margin"], height=300,
        legend=dict(bgcolor=t["legend"]["bgcolor"]),
    )
    fig.update_xaxes(gridcolor=BORDER, linecolor=BORDER)
    fig.update_yaxes(gridcolor=BORDER, linecolor=BORDER, zeroline=True,
                     zerolinecolor=BORDER)
    st.plotly_chart(fig, use_container_width=True)

    # ── Horizon score strip ───────────────────────────────────────────────────
    sc1, sc2, sc3 = st.columns(3)
    for col, summary, label in [
        (sc1, analysis.h3,  "Score (3m)"),
        (sc2, analysis.h6,  "Score (6m)"),
        (sc3, analysis.h12, "Score (12m)"),
    ]:
        col.metric(label, f"{summary.score:.0f} / 100",
                   delta=summary.signal,
                   delta_color="normal" if summary.signal == "Neutral"
                               else ("off" if summary.signal == "Bearish" else "normal"))

    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

    # ── Transaction table ─────────────────────────────────────────────────────
    if analysis.transactions:
        st.markdown(
            f"<div style='font-size:12px; font-weight:700; color:{TEXT_SECONDARY}; "
            f"text-transform:uppercase; letter-spacing:0.06em; margin-bottom:6px;'>"
            f"Recent Transactions (12 months)</div>",
            unsafe_allow_html=True,
        )
        st.dataframe(analysis.transactions, use_container_width=True, hide_index=True)
    else:
        st.caption("No Buy or Sell transactions found in the last 12 months.")

    # ── Score interpretation ──────────────────────────────────────────────────
    with st.expander("How the Insider Score works"):
        st.markdown("""
**Score 0–100 · 50 = neutral · >65 = Bullish · <35 = Bearish**

Each buy or sell is weighted by:
- **CEO / Chief Executive:** 1.0×
- **CFO / Chief Financial:** 0.9×
- **President:** 0.8×
- **Officer (generic):** 0.65×
- **Director:** 0.5×

The score is then scaled by transaction value (in $M, capped at 5×) to give larger
transactions more influence. Gifts, options exercises and other non-market transactions
are excluded.

*Score = weighted buys / (weighted buys + weighted sells) × 100*

**Why it matters:** Corporate insiders must file with the SEC within 2 business days.
Clusters of buying — especially by the CEO or CFO — have historically preceded positive
stock performance. Selling is less informative as it often reflects diversification needs.
        """)
