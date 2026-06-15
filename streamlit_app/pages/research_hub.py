"""Research Hub — watchlist management and fundamentals viewer (Phase 16)."""

from __future__ import annotations

import math

import streamlit as st

from research.data.watchlist_store import (
    delete_watchlist, list_watchlists, load_watchlist, save_watchlist,
)
from research.data.fundamentals_fetcher import fetch_fundamentals, fetch_profile
from research.models.fundamentals import Watchlist
from streamlit_app.styles.theme import (
    ACCENT, BG_PRIMARY, BG_SECONDARY, BG_TERTIARY, BORDER,
    DANGER, SUCCESS, TEXT_PRIMARY, TEXT_SECONDARY, WARNING,
)

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
    st.markdown(
        f"<p style='color:{TEXT_SECONDARY}; font-size:13px; margin-bottom:16px;'>"
        "Research Hub — watchlists, fundamentals, company profiles</p>",
        unsafe_allow_html=True,
    )

    tab_wl, tab_company = st.tabs(["Watchlists", "Company Look-up"])

    with tab_wl:
        _render_watchlists()

    with tab_company:
        _render_company_lookup()


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

    if not search or not ticker_in.strip():
        st.caption("Enter a ticker and click Look up.")
        return

    ticker = ticker_in.strip().upper()

    # Profile
    with st.spinner(f"Loading {ticker}…"):
        profile = fetch_profile(ticker)
        funds   = fetch_fundamentals(ticker, n_years=5)

    # Company header
    st.markdown(
        f"""<div style="background:{BG_SECONDARY}; border:1px solid {BORDER};
                    border-radius:8px; padding:16px 20px; margin-bottom:16px;">
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

    # KPI cards — most recent year
    f0 = funds[0]
    k1, k2, k3, k4, k5 = st.columns(5)
    kpi_style = (
        f"background:{BG_SECONDARY}; border:1px solid {BORDER}; border-radius:8px;"
        f" padding:12px 14px; text-align:center;"
    )

    def _kpi(col, label: str, value: str, color: str = TEXT_PRIMARY) -> None:
        col.markdown(
            f"""<div style="{kpi_style}">
                <div style="font-size:9px; color:{TEXT_SECONDARY}; text-transform:uppercase;
                            letter-spacing:.07em; margin-bottom:4px;">{label}</div>
                <div style="font-size:18px; font-weight:700; color:{color};">{value}</div>
            </div>""",
            unsafe_allow_html=True,
        )

    _kpi(k1, "Revenue", _bn(f0.revenue))
    _kpi(k2, "Net Income", _bn(f0.net_income),
         SUCCESS if f0.net_income > 0 else DANGER)
    _kpi(k3, "Net Margin", _pct(f0.net_margin),
         SUCCESS if f0.net_margin > 0.10 else WARNING if f0.net_margin > 0 else DANGER)
    _kpi(k4, "ROE", _pct(f0.return_on_equity),
         SUCCESS if f0.return_on_equity > 0.15 else WARNING if f0.return_on_equity > 0 else DANGER)
    _kpi(k5, "Free Cash Flow", _bn(f0.free_cash_flow),
         SUCCESS if f0.free_cash_flow > 0 else DANGER)

    _divider()

    # Historical table
    _h3(f"Annual Financials — {f0.source.upper()}")
    rows = []
    for f in funds:
        rows.append({
            "FY":             f.fiscal_year,
            "Revenue":        _bn(f.revenue),
            "Gross Profit":   _bn(f.gross_profit),
            "Operating Inc.": _bn(f.operating_income),
            "Net Income":     _bn(f.net_income),
            "EPS (diluted)":  f"${f.eps_diluted:.2f}" if not math.isnan(f.eps_diluted) else "—",
            "Gross Margin":   _pct(f.gross_margin),
            "Op. Margin":     _pct(f.operating_margin),
            "Net Margin":     _pct(f.net_margin),
            "ROE":            _pct(f.return_on_equity),
            "ROA":            _pct(f.return_on_assets),
            "Debt/Equity":    f"{f.debt_to_equity:.2f}" if not math.isnan(f.debt_to_equity) else "—",
            "Free CF":        _bn(f.free_cash_flow),
        })
    st.dataframe(rows, use_container_width=True, hide_index=True)

    _divider()

    # Charts
    import plotly.graph_objects as go
    from streamlit_app.styles.theme import PLOTLY_TEMPLATE

    def _apply(fig: go.Figure, h: int = 280) -> go.Figure:
        t = PLOTLY_TEMPLATE["layout"]
        fig.update_layout(paper_bgcolor=t["paper_bgcolor"], plot_bgcolor=t["plot_bgcolor"],
                          font=t["font"], margin=t["margin"], height=h,
                          legend=dict(bgcolor=t["legend"]["bgcolor"],
                                      bordercolor=t["legend"]["bordercolor"]))
        fig.update_xaxes(gridcolor=BORDER, zerolinecolor=BORDER)
        fig.update_yaxes(gridcolor=BORDER, zerolinecolor=BORDER)
        return fig

    years_r = [f.fiscal_year for f in reversed(funds)]

    ch1, ch2 = st.columns(2)
    with ch1:
        fig_r = go.Figure()
        fig_r.add_trace(go.Bar(x=years_r,
                               y=[f.revenue / 1e9 for f in reversed(funds)],
                               marker_color=ACCENT, name="Revenue"))
        fig_r.add_trace(go.Bar(x=years_r,
                               y=[f.net_income / 1e9 for f in reversed(funds)],
                               marker_color=SUCCESS, name="Net Income"))
        fig_r.update_layout(title="Revenue & Net Income ($B)", barmode="group")
        st.plotly_chart(_apply(fig_r), use_container_width=True)

    with ch2:
        fig_m = go.Figure()
        fig_m.add_trace(go.Scatter(
            x=years_r, y=[f.gross_margin * 100 for f in reversed(funds)],
            name="Gross", line=dict(color=ACCENT, width=2)))
        fig_m.add_trace(go.Scatter(
            x=years_r, y=[f.operating_margin * 100 for f in reversed(funds)],
            name="Operating", line=dict(color="#2563eb", width=2)))
        fig_m.add_trace(go.Scatter(
            x=years_r, y=[f.net_margin * 100 for f in reversed(funds)],
            name="Net", line=dict(color=SUCCESS, width=2)))
        fig_m.update_layout(title="Margins %", yaxis_title="%")
        st.plotly_chart(_apply(fig_m), use_container_width=True)

    ch3, ch4 = st.columns(2)
    with ch3:
        fig_cf = go.Figure()
        fig_cf.add_trace(go.Bar(
            x=years_r, y=[f.operating_cash_flow / 1e9 for f in reversed(funds)],
            name="Op. CF", marker_color=ACCENT))
        fig_cf.add_trace(go.Bar(
            x=years_r, y=[f.free_cash_flow / 1e9 for f in reversed(funds)],
            name="Free CF", marker_color=SUCCESS))
        fig_cf.update_layout(title="Cash Flow ($B)", barmode="group")
        st.plotly_chart(_apply(fig_cf), use_container_width=True)

    with ch4:
        fig_de = go.Figure(go.Bar(
            x=years_r, y=[f.debt_to_equity for f in reversed(funds)],
            marker_color=[DANGER if f.debt_to_equity > 2 else
                          WARNING if f.debt_to_equity > 1 else SUCCESS
                          for f in reversed(funds)],
            name="D/E",
        ))
        fig_de.update_layout(title="Debt / Equity Ratio")
        st.plotly_chart(_apply(fig_de), use_container_width=True)

    if profile.description:
        with st.expander("Business description"):
            st.write(profile.description)
