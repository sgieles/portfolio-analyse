"""Research Hub — screener, watchlists, and fundamentals viewer."""

from __future__ import annotations

import math
import sys
from pathlib import Path

# Ensure repo root is on sys.path when Streamlit runs this page standalone on Cloud
_ROOT = str(Path(__file__).resolve().parent.parent.parent)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import streamlit as st

from research.data.watchlist_store import (
    delete_watchlist, list_watchlists, load_watchlist, save_watchlist,
)
from research.data.fundamentals_fetcher import fetch_fundamentals, fetch_profile, fetch_quarterly
from research.models.fundamentals import Watchlist
from research.analytics.fundamental_scorer import score_fundamentals
from research.cache.screener_cache import load_screener_rows
from streamlit_app.styles.theme import (
    ACCENT, BG_PRIMARY, BG_SECONDARY, BG_TERTIARY, BORDER,
    DANGER, SUCCESS, TEXT_PRIMARY, TEXT_SECONDARY, WARNING,
)
from streamlit_app.pages import screener as _screener_page
from streamlit_app.pages import fundamentals as _fund_page
from streamlit_app.pages import valuation as _val_page
from streamlit_app.pages import insider as _insider_page
from streamlit_app.pages import sector_intel as _sector_page
from streamlit_app.pages import research_report as _report_page
from streamlit_app.pages import etf_analysis as _etf_page
from research.data.etf_fetcher import is_etf

_WL_KEY = "active_watchlist"


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


def _pct(v: float) -> str:
    return "—" if math.isnan(v) else f"{v * 100:.1f}%"


def _bn(v: float) -> str:
    """Format large USD values as $XB or $XM."""
    if math.isnan(v):
        return "—"
    if abs(v) >= 1e9:
        return f"${v / 1e9:.1f}B"
    if abs(v) >= 1e6:
        return f"${v / 1e6:.1f}M"
    return f"${v:,.0f}"


def render() -> None:
    tab_scr, tab_wl, tab_company, tab_sector = st.tabs(
        ["🔍 Screener", "📋 Watchlists", "🏢 Company Look-up", "🏭 Sector Intelligence"]
    )

    with tab_scr:
        _screener_page.render()

    with tab_wl:
        _render_watchlists()

    with tab_company:
        _render_company_lookup()

    with tab_sector:
        _sector_page.render()


# ── Watchlist tab ──────────────────────────────────────────────────────────────

def _render_watchlists() -> None:
    _h3("Watchlists")

    # Sidebar-like controls in two columns
    existing = list_watchlists()

    ctrl1, ctrl2 = st.columns([2, 1])
    with ctrl1:
        new_name = st.text_input("New watchlist name", placeholder="My Watchlist",
                                 key="wl_new_name")
    with ctrl2:
        st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
        if st.button("Create", key="wl_create", use_container_width=True):
            if new_name.strip():
                wl = Watchlist(name=new_name.strip())
                save_watchlist(wl)
                st.session_state[_WL_KEY] = new_name.strip()
                st.rerun()

    if not existing:
        st.info("No watchlists yet — create one above.")
        return

    selected = st.selectbox(
        "Open watchlist", existing,
        index=existing.index(st.session_state.get(_WL_KEY, existing[0]))
        if st.session_state.get(_WL_KEY) in existing else 0,
        key="wl_select",
    )
    st.session_state[_WL_KEY] = selected
    wl = load_watchlist(selected)

    _divider()

    # Add ticker
    add_col, btn_col = st.columns([3, 1])
    with add_col:
        add_ticker = st.text_input("Add ticker", placeholder="AAPL",
                                   key="wl_add_ticker")
        add_note = st.text_input("Note (optional)", placeholder="Q3 earnings beat",
                                 key="wl_add_note")
    with btn_col:
        st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
        if st.button("Add", key="wl_add", use_container_width=True):
            t = add_ticker.strip().upper()
            if t:
                wl.add(t, add_note.strip())
                save_watchlist(wl)
                st.rerun()

    if not wl.entries:
        st.caption("This watchlist is empty.")
        return

    _divider()

    # Table of entries
    st.caption(f"**{wl.name}** — {len(wl.entries)} tickers")

    rows = []
    for e in wl.entries:
        rows.append({
            "Ticker":   e.ticker,
            "Note":     e.note or "",
            "Added":    e.added_at or "",
        })
    st.dataframe(rows, use_container_width=True, hide_index=True)

    # Remove
    remove_sel = st.selectbox("Remove ticker", ["—"] + wl.tickers, key="wl_remove")
    r_col1, r_col2 = st.columns([1, 3])
    with r_col1:
        if st.button("Remove", key="wl_do_remove",
                     disabled=(remove_sel == "—")):
            wl.remove(remove_sel)
            save_watchlist(wl)
            st.rerun()

    _divider()

    # Download watchlist JSON
    import json as _json
    wl_json = _json.dumps(
        {"name": wl.name, "tickers": wl.tickers}, indent=2
    ).encode()
    st.download_button(
        "Download Watchlist JSON", data=wl_json,
        file_name=f"{wl.name.replace(' ', '_')}.json",
        mime="application/json", key="wl_dl",
    )

    with st.expander("Delete this watchlist"):
        if st.button(f"Permanently delete '{wl.name}'", key="wl_delete"):
            delete_watchlist(wl.name)
            st.session_state.pop(_WL_KEY, None)
            st.rerun()


# ── Company look-up tab ────────────────────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def _cached_quarterly(ticker: str) -> list:
    return fetch_quarterly(ticker, n_quarters=8)


def _render_company_lookup() -> None:
    _h3("Company Fundamentals")

    lookup_col, btn_col = st.columns([3, 1])
    with lookup_col:
        ticker_in = st.text_input("Ticker symbol", placeholder="AAPL",
                                  key="research_ticker")
    with btn_col:
        st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
        search = st.button("Look up", type="primary",
                           use_container_width=True, key="research_search")

    if not search and not st.session_state.get("research_ticker_active"):
        st.caption("Enter a ticker and click Look up.")
        return

    raw = ticker_in.strip() or st.session_state.get("research_ticker_active", "")
    if not raw:
        return
    ticker = raw.upper()
    st.session_state["research_ticker_active"] = ticker

    with st.spinner(f"Loading {ticker}…"):
        profile  = fetch_profile(ticker)
        funds    = fetch_fundamentals(ticker, n_years=10)
        quarters = _cached_quarterly(ticker)

    # Detect ETF / mutual fund and route to dedicated page
    import yfinance as _yf
    _info = _yf.Ticker(ticker).info or {}
    if is_etf(_info):
        st.markdown(
            f'<div style="background:{BG_SECONDARY}; border:1px solid {BORDER}; border-radius:8px;'
            f'padding:14px 20px; margin-bottom:14px;">'
            f'<div style="font-size:20px; font-weight:800; color:{TEXT_PRIMARY};">'
            f'{profile.name or ticker}'
            f'<span style="font-size:13px; font-weight:400; color:{TEXT_SECONDARY}; margin-left:10px;">{ticker}</span>'
            f'</div>'
            f'<div style="font-size:12px; color:{TEXT_SECONDARY}; margin-top:4px;">'
            f'{_info.get("fundFamily","—")} · ETF / Fund'
            f'</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
        _etf_page.render_detail(ticker)
        return

    # Company header (stocks)
    st.markdown(
        f"""<div style="background:{BG_SECONDARY}; border:1px solid {BORDER};
                    border-radius:8px; padding:16px 20px; margin-bottom:14px;">
            <div style="font-size:20px; font-weight:800; color:{TEXT_PRIMARY};">
                {profile.name or ticker}
                <span style="font-size:13px; font-weight:400; color:{TEXT_SECONDARY};
                             margin-left:10px;">{ticker}</span>
            </div>
            <div style="font-size:12px; color:{TEXT_SECONDARY}; margin-top:4px;">
                {profile.sector or "—"} · {profile.industry or "—"} ·
                {profile.country or "—"} · {profile.exchange or "—"}
            </div>
        </div>""",
        unsafe_allow_html=True,
    )

    if not funds:
        st.warning(f"No fundamental data found for {ticker}.")
        return

    # Peer scores from screener cache for same sector
    sector_scores: list[float] = []
    if profile.sector:
        for universe in ("S&P 500", "Nasdaq 100", "STOXX 600", "AEX"):
            cached = load_screener_rows(universe)
            if cached:
                for row in cached:
                    if row.get("sector") == profile.sector:
                        v = row.get("fundamental_score")
                        if v is not None and not math.isnan(float(v)):
                            sector_scores.append(float(v))

    # Run full fundamental analysis
    analysis = score_fundamentals(ticker, funds, sector_scores or None)

    # Annual financials table (collapsible)
    with st.expander(f"Annual Financials — {funds[0].source.upper()} ({len(funds)} years)", expanded=False):
        rows = []
        for f in funds:
            rows.append({
                "FY":             f.fiscal_year,
                "Revenue":        _bn(f.revenue),
                "Gross Profit":   _bn(f.gross_profit),
                "Op. Income":     _bn(f.operating_income),
                "Net Income":     _bn(f.net_income),
                "EPS":            f"${f.eps_diluted:.2f}" if not math.isnan(f.eps_diluted) else "—",
                "Gross Margin":   _pct(f.gross_margin),
                "Op. Margin":     _pct(f.operating_margin),
                "Net Margin":     _pct(f.net_margin),
                "ROE":            _pct(f.return_on_equity),
                "ROA":            _pct(f.return_on_assets),
                "D/E":            f"{f.debt_to_equity:.2f}" if not math.isnan(f.debt_to_equity) else "—",
                "Free CF":        _bn(f.free_cash_flow),
                "Int. Coverage":  f"{f.operating_income/f.interest_expense:.1f}×"
                                  if not (math.isnan(f.interest_expense) or f.interest_expense == 0
                                          or math.isnan(f.operating_income)) else "—",
            })
        st.dataframe(rows, use_container_width=True, hide_index=True)

    if profile.description:
        with st.expander("Business description"):
            st.write(profile.description)

    _divider()

    # Fundamentals / Valuation / Insider / Report tabs
    tab_fund, tab_val, tab_ins, tab_rep = st.tabs(
        ["📊 Fundamentals", "💰 Valuation", "🕵️ Insider Activity", "📋 Research Report"]
    )
    with tab_fund:
        _fund_page.render_detail(ticker, funds, quarters, analysis)
    with tab_val:
        _val_page.render_detail(ticker, funds, profile)
    with tab_ins:
        _insider_page.render_detail(ticker)
    with tab_rep:
        _report_page.render_report(ticker, funds, quarters, analysis, profile)
