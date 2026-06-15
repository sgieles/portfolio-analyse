"""Valuation page — Phase 19.

Renders relative multiples, historical comparison, DCF model, and
valuation score for one company.

Entry point:  render_detail(ticker, funds, profile)
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

_ROOT = str(Path(__file__).resolve().parent.parent.parent)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


import plotly.graph_objects as go
import streamlit as st

from research.analytics.valuation_engine import (
    DcfResult, ValuationAnalysis, ValuationMultiples,
    compute_historical_multiples, compute_sector_median,
    dcf_fair_value, fill_dcf_price, score_valuation,
)
from research.cache.screener_cache import load_screener_rows
from research.data.valuation_fetcher import (
    fetch_current_multiples, fetch_market_pe, fetch_year_end_prices,
)
from research.models.fundamentals import AnnualFundamentals, CompanyProfile
from streamlit_app.styles.theme import (
    ACCENT, BG_SECONDARY, BORDER, DANGER, PLOTLY_TEMPLATE,
    SUCCESS, TEXT_PRIMARY, TEXT_SECONDARY, WARNING,
)

_NAN = float("nan")


# ── Cached fetchers ───────────────────────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def _cached_current_multiples(ticker: str):
    return fetch_current_multiples(ticker)


@st.cache_data(ttl=3600, show_spinner=False)
def _cached_year_prices(ticker: str) -> dict:
    return fetch_year_end_prices(ticker, years=10)


@st.cache_data(ttl=3600, show_spinner=False)
def _cached_market_pe() -> float:
    return fetch_market_pe()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _ok(v: float) -> bool:
    return math.isfinite(v)


def _fmt(v: float, suffix: str = "×", digits: int = 1) -> str:
    return "—" if not _ok(v) else f"{v:.{digits}f}{suffix}"


def _pct(v: float, digits: int = 1) -> str:
    return "—" if not _ok(v) else f"{v * 100:.{digits}f}%"


def _color(v: float) -> str:
    if not _ok(v):
        return TEXT_SECONDARY
    if v >= 65:
        return SUCCESS
    if v >= 40:
        return WARNING
    return DANGER


def _vs_color(label: str) -> str:
    return {
        "cheap": SUCCESS, "fair": WARNING, "expensive": DANGER,
    }.get(label, TEXT_SECONDARY)


def _apply_theme(fig: go.Figure, height: int = 260) -> go.Figure:
    t = PLOTLY_TEMPLATE["layout"]
    fig.update_layout(
        paper_bgcolor=t["paper_bgcolor"], plot_bgcolor=t["plot_bgcolor"],
        font=t["font"], margin=t["margin"], height=height,
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


# ── Valuation score card ─────────────────────────────────────────────────────

def _render_score_strip(a: ValuationAnalysis) -> None:
    c_score = _color(a.valuation_score)
    val = f"{a.valuation_score:.0f}" if _ok(a.valuation_score) else "—"

    labels = [
        ("vs History", a.vs_history),
        ("vs Sector",  a.vs_sector),
        ("vs Market",  a.vs_market),
    ]
    cols = st.columns([2, 1, 1, 1])

    cols[0].markdown(
        f"""<div style="background:{c_score}11; border:2px solid {c_score}55;
                    border-radius:10px; padding:14px 16px; text-align:center;">
            <div style="font-size:9px; color:{TEXT_SECONDARY}; text-transform:uppercase;
                        letter-spacing:.07em; margin-bottom:4px;">Valuation Score</div>
            <div style="font-size:32px; font-weight:800; color:{c_score};">{val}</div>
            <div style="font-size:10px; color:{TEXT_SECONDARY}; margin-top:2px;">
                0 = expensive · 100 = very cheap</div>
        </div>""",
        unsafe_allow_html=True,
    )
    for col, (label, verdict) in zip(cols[1:], labels):
        c = _vs_color(verdict)
        col.markdown(
            f"""<div style="background:{c}11; border:1px solid {c}44;
                        border-radius:8px; padding:12px 10px; text-align:center; height:100%;">
                <div style="font-size:9px; color:{TEXT_SECONDARY}; text-transform:uppercase;
                            letter-spacing:.07em; margin-bottom:4px;">{label}</div>
                <div style="font-size:15px; font-weight:700; color:{c}; text-transform:capitalize;">
                    {verdict}</div>
            </div>""",
            unsafe_allow_html=True,
        )
    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)


# ── Multiples comparison table ────────────────────────────────────────────────

def _render_multiples_table(a: ValuationAnalysis) -> None:
    _h3("Relative Multiples")

    rows = [
        ("P/E (trailing)",    a.current.pe,         a.historical.pe_avg,    a.sector_median.pe,     a.market_pe),
        ("Forward P/E",       a.current.forward_pe,  _NAN,                   a.sector_median.forward_pe, _NAN),
        ("EV/EBITDA",         a.current.ev_ebitda,   _NAN,                   _NAN,                   _NAN),
        ("EV/Sales",          a.current.ev_sales,    _NAN,                   _NAN,                   _NAN),
        ("Price/Sales",       a.current.ps_ratio,    a.historical.ps_avg,    _NAN,                   _NAN),
        ("Price/Book",        a.current.pb_ratio,    a.historical.pb_avg,    a.sector_median.pb_ratio, _NAN),
        ("FCF Yield",         a.current.fcf_yield,   a.historical.fcf_yield_avg, _NAN,              _NAN),
    ]

    header_html = (
        f"<table style='width:100%; border-collapse:collapse; font-size:13px;'>"
        f"<thead><tr style='border-bottom:2px solid {BORDER};'>"
        f"<th style='text-align:left; padding:8px 6px; color:{TEXT_SECONDARY}; font-weight:600;'>Metric</th>"
        f"<th style='text-align:right; padding:8px 6px; color:{ACCENT}; font-weight:600;'>Current</th>"
        f"<th style='text-align:right; padding:8px 6px; color:{TEXT_SECONDARY}; font-weight:600;'>5Y Avg</th>"
        f"<th style='text-align:right; padding:8px 6px; color:{TEXT_SECONDARY}; font-weight:600;'>Sector Median</th>"
        f"<th style='text-align:right; padding:8px 6px; color:{TEXT_SECONDARY}; font-weight:600;'>Market</th>"
        f"</tr></thead><tbody>"
    )

    rows_html = ""
    for label, cur, hist, sec, mkt in rows:
        is_yield = "Yield" in label
        def _cell(v: float, bold: bool = False) -> str:
            if not _ok(v):
                return f"<td style='text-align:right; padding:6px 6px; color:{TEXT_SECONDARY};'>—</td>"
            disp = _pct(v) if is_yield else _fmt(v)
            color = TEXT_PRIMARY if not bold else ACCENT
            weight = "700" if bold else "400"
            return f"<td style='text-align:right; padding:6px 6px; color:{color}; font-weight:{weight};'>{disp}</td>"

        # Colour-code current vs historical
        row_bg = ""
        if _ok(cur) and _ok(hist) and hist > 0 and not is_yield:
            ratio = cur / hist
            if ratio < 0.85:
                row_bg = f"background:{SUCCESS}08;"
            elif ratio > 1.20:
                row_bg = f"background:{DANGER}08;"

        rows_html += (
            f"<tr style='border-bottom:1px solid {BORDER}; {row_bg}'>"
            f"<td style='padding:6px 6px; color:{TEXT_PRIMARY};'>{label}</td>"
            + _cell(cur, bold=True)
            + _cell(hist) + _cell(sec) + _cell(mkt)
            + "</tr>"
        )

    st.markdown(header_html + rows_html + "</tbody></table>", unsafe_allow_html=True)
    st.markdown(
        f"<p style='font-size:11px; color:{TEXT_SECONDARY}; margin-top:6px;'>"
        "Green rows = current below historical avg; red = above avg. "
        "FCF Yield: higher is cheaper.</p>",
        unsafe_allow_html=True,
    )


# ── DCF section ───────────────────────────────────────────────────────────────

def _render_dcf(
    ticker: str,
    funds: list[AnnualFundamentals],
    current_price: float,
    shares: float,
) -> DcfResult:
    """Render DCF controls + output; returns the computed DcfResult."""
    _h3("Intrinsic Valuation — DCF Model")
    st.markdown(
        f"<p style='font-size:12px; color:{TEXT_SECONDARY}; margin-bottom:10px;'>"
        "Two-stage DCF: high-growth phase → terminal value (Gordon Growth). "
        "Based on trailing Free Cash Flow. Adjust assumptions below.</p>",
        unsafe_allow_html=True,
    )

    # Default growth from Phase 18 revenue CAGR or reasonable estimate
    default_g = 0.08
    if funds:
        n = min(3, len(funds) - 1)
        if n > 0:
            r0, rn = funds[0].revenue, funds[n].revenue
            if r0 > 0 and rn > 0:
                cagr = (r0 / rn) ** (1.0 / n) - 1.0
                default_g = max(0.0, min(0.30, round(cagr, 2)))

    fcf_base = funds[0].free_cash_flow if (funds and _ok(funds[0].free_cash_flow)) else _NAN

    c1, c2, c3 = st.columns(3)
    g1 = c1.slider("Growth rate (5Y)", 0, 30, int(default_g * 100), 1,
                   key=f"dcf_g1_{ticker}", format="%d%%") / 100.0
    wacc = c2.slider("Discount rate (WACC)", 5, 20, 10, 1,
                     key=f"dcf_wacc_{ticker}", format="%d%%") / 100.0
    g_term = c3.slider("Terminal growth", 0, 5, 2, 1,
                       key=f"dcf_gterm_{ticker}", format="%d%%") / 100.0

    if not _ok(fcf_base) or fcf_base <= 0:
        st.warning("DCF requires positive Free Cash Flow — not available for this company.")
        return DcfResult()

    if not _ok(shares) or shares <= 0:
        st.warning("Shares outstanding not available — cannot compute per-share value.")
        return DcfResult()

    dcf = dcf_fair_value(fcf_base, shares, g1, g_term, wacc)
    dcf = fill_dcf_price(dcf, current_price)

    # Result display
    col_a, col_b, col_c = st.columns(3)
    fv  = dcf.fair_value_per_share
    mos = dcf.margin_of_safety

    def _kpi(col, label: str, value: str, color: str = TEXT_PRIMARY) -> None:
        col.markdown(
            f"""<div style="background:{color}11; border:1px solid {color}44;
                        border-radius:8px; padding:12px 14px; text-align:center;">
                <div style="font-size:9px; color:{TEXT_SECONDARY}; text-transform:uppercase;
                            letter-spacing:.07em; margin-bottom:4px;">{label}</div>
                <div style="font-size:20px; font-weight:800; color:{color};">{value}</div>
            </div>""",
            unsafe_allow_html=True,
        )

    fv_color  = SUCCESS if (_ok(fv) and _ok(current_price) and fv > current_price) else DANGER
    mos_color = SUCCESS if (_ok(mos) and mos > 0.10) else DANGER if (_ok(mos) and mos < -0.10) else WARNING

    _kpi(col_a, "DCF Fair Value",       f"${fv:.0f}" if _ok(fv) else "—", fv_color)
    _kpi(col_b, "Current Price",        f"${current_price:.0f}" if _ok(current_price) else "—", TEXT_PRIMARY)
    _kpi(col_c, "Margin of Safety",     _pct(mos) if _ok(mos) else "—", mos_color)

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    # Sensitivity table (3×3 grid: WACC vs growth)
    with st.expander("DCF Sensitivity Table", expanded=False):
        g_range   = [g1 - 0.03, g1, g1 + 0.03]
        w_range   = [wacc - 0.02, wacc, wacc + 0.02]
        g_labels  = [f"{int(g*100)}% growth" for g in g_range]
        w_labels  = [f"{int(w*100)}% WACC" for w in w_range]

        table_html = (
            f"<table style='border-collapse:collapse; font-size:12px; width:100%;'>"
            f"<tr><th style='padding:4px 8px; border:1px solid {BORDER};'></th>"
        )
        for gl in g_labels:
            table_html += f"<th style='padding:4px 8px; border:1px solid {BORDER}; color:{TEXT_SECONDARY};'>{gl}</th>"
        table_html += "</tr>"

        for w, wl in zip(w_range, w_labels):
            table_html += f"<tr><td style='padding:4px 8px; border:1px solid {BORDER}; color:{TEXT_SECONDARY}; font-weight:600;'>{wl}</td>"
            for g in g_range:
                if g_term >= w or w <= 0:
                    table_html += f"<td style='padding:4px 8px; border:1px solid {BORDER}; text-align:center;'>N/A</td>"
                    continue
                res = dcf_fair_value(fcf_base, shares, max(0, g), min(g_term, w - 0.005), w)
                fv_cell = res.fair_value_per_share
                if _ok(fv_cell) and _ok(current_price) and current_price > 0:
                    mos_cell = (fv_cell - current_price) / fv_cell
                    c = SUCCESS if mos_cell > 0.10 else DANGER if mos_cell < -0.10 else WARNING
                    table_html += (
                        f"<td style='padding:4px 8px; border:1px solid {BORDER}; "
                        f"text-align:center; color:{c}; font-weight:600;'>"
                        f"${fv_cell:.0f} ({_pct(mos_cell)})</td>"
                    )
                else:
                    table_html += f"<td style='padding:4px 8px; border:1px solid {BORDER}; text-align:center;'>—</td>"
            table_html += "</tr>"
        table_html += "</table>"
        st.markdown(table_html, unsafe_allow_html=True)

    return dcf


# ── Strengths & Weaknesses ────────────────────────────────────────────────────

def _render_signals(a: ValuationAnalysis) -> None:
    _h3("Valuation Signals")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(
            f"<div style='font-size:13px; font-weight:700; color:{SUCCESS}; margin-bottom:6px;'>✓ Cheap signals</div>",
            unsafe_allow_html=True,
        )
        for s in (a.strengths or ["No cheap signals identified."]):
            color = SUCCESS if a.strengths else TEXT_SECONDARY
            st.markdown(
                f"<div style='background:{color}11; border-left:3px solid {color}; "
                f"padding:5px 10px; border-radius:0 4px 4px 0; margin-bottom:4px; "
                f"font-size:13px; color:{TEXT_PRIMARY};'>{s}</div>",
                unsafe_allow_html=True,
            )
    with c2:
        st.markdown(
            f"<div style='font-size:13px; font-weight:700; color:{DANGER}; margin-bottom:6px;'>✗ Expensive signals</div>",
            unsafe_allow_html=True,
        )
        for w in (a.weaknesses or ["No expensive signals identified."]):
            color = DANGER if a.weaknesses else TEXT_SECONDARY
            st.markdown(
                f"<div style='background:{color}11; border-left:3px solid {color}; "
                f"padding:5px 10px; border-radius:0 4px 4px 0; margin-bottom:4px; "
                f"font-size:13px; color:{TEXT_PRIMARY};'>{w}</div>",
                unsafe_allow_html=True,
            )


# ── Main entry point ──────────────────────────────────────────────────────────

def render_detail(
    ticker: str,
    funds: list[AnnualFundamentals],
    profile: CompanyProfile,
) -> None:
    """Render the full valuation breakdown for one ticker."""
    with st.spinner("Loading valuation data…"):
        multiples, current_price, shares = _cached_current_multiples(ticker)
        year_prices = _cached_year_prices(ticker)
        market_pe   = _cached_market_pe()

    # Historical multiples from price history + fundamentals
    historical = compute_historical_multiples(funds, year_prices)

    # Sector median from screener cache
    sector_rows: list[dict] = []
    if profile.sector:
        for universe in ("S&P 500", "Nasdaq 100", "STOXX 600", "AEX"):
            cached = load_screener_rows(universe)
            if cached:
                sector_rows.extend(r for r in cached if r.get("sector") == profile.sector)

    sector_median = compute_sector_median(sector_rows) if sector_rows else ValuationMultiples()

    # Run DCF first so we have it for the score
    _divider()
    dcf = _render_dcf(ticker, funds, current_price, shares)

    # Score valuation
    analysis = score_valuation(
        ticker, multiples, historical, sector_median, dcf, market_pe,
    )

    _divider()
    _render_score_strip(analysis)
    _divider()
    _render_multiples_table(analysis)
    _divider()
    _render_signals(analysis)
