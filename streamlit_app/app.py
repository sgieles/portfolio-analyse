"""Portfolio Analyser — Streamlit web application entry point."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st

from streamlit_app.state import session
from streamlit_app.styles.theme import (
    ACCENT, BORDER, BG_SECONDARY, TEXT_PRIMARY, TEXT_SECONDARY, DARK_CSS,
)
from streamlit_app.components import portfolio_builder, export_panel
from streamlit_app.pages import dashboard, asset_analysis, monte_carlo, research_hub


# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Portfolio Analyser",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(DARK_CSS, unsafe_allow_html=True)
session.init()

# ── Hub switcher (top of sidebar) ─────────────────────────────────────────────
hub = st.sidebar.radio(
    "Hub",
    ["🔬 Research Hub", "📊 Portfolio Hub"],
    key="active_hub",
    label_visibility="collapsed",
)

st.sidebar.divider()


# ── Portfolio Hub ──────────────────────────────────────────────────────────────
def _portfolio_hub() -> None:
    portfolio_builder.render()
    st.sidebar.divider()
    export_panel.render()
    st.sidebar.divider()

    page = st.sidebar.radio(
        "Navigation",
        ["Dashboard", "Asset Analysis", "Monte Carlo"],
        label_visibility="visible",
        key="portfolio_page",
    )

    pf = session.get_portfolio()
    pf_name = pf.name if pf.name else "My Portfolio"
    st.markdown(
        f"""
        <div style="display:flex; align-items:baseline; gap:10px; margin-bottom:4px;">
            <span style="font-size:26px; font-weight:800; color:{TEXT_PRIMARY};
                         letter-spacing:-0.03em;">{pf_name}</span>
            <span style="font-size:13px; font-weight:600; color:{ACCENT};
                         text-transform:uppercase; letter-spacing:0.06em;">Portfolio Analyser</span>
        </div>
        <hr style="border:none; border-top:1px solid {BORDER}; margin:6px 0 18px 0;">
        """,
        unsafe_allow_html=True,
    )

    if page == "Dashboard":
        dashboard.render()
    elif page == "Asset Analysis":
        asset_analysis.render()
    elif page == "Monte Carlo":
        monte_carlo.render()


# ── Research Hub ───────────────────────────────────────────────────────────────
def _research_hub() -> None:
    st.sidebar.markdown(
        f"<p style='font-size:12px; color:{TEXT_SECONDARY};'>"
        "Company fundamentals, watchlists, and investment research.</p>",
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""
        <div style="display:flex; align-items:baseline; gap:10px; margin-bottom:4px;">
            <span style="font-size:26px; font-weight:800; color:{TEXT_PRIMARY};
                         letter-spacing:-0.03em;">Research Hub</span>
            <span style="font-size:13px; font-weight:600; color:{ACCENT};
                         text-transform:uppercase; letter-spacing:0.06em;">
                SEC EDGAR · yfinance</span>
        </div>
        <hr style="border:none; border-top:1px solid {BORDER}; margin:6px 0 18px 0;">
        """,
        unsafe_allow_html=True,
    )

    research_hub.render()


# ── Route ──────────────────────────────────────────────────────────────────────
if hub == "🔬 Research Hub":
    _research_hub()
else:
    _portfolio_hub()
