"""Research Report page — unified company analysis with investment thesis.

Entry point: render_report(ticker, funds, quarters, analysis, profile)
Called from research_hub.py Company Look-up when user opens the Report tab.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

_ROOT = str(Path(__file__).resolve().parent.parent.parent)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import yfinance as yf
import streamlit as st

from research.analytics.fundamental_scorer import FundamentalAnalysis
from research.analytics.insider_scorer import score_insider_activity, InsiderAnalysis
from research.analytics.technical_scorer import score_technical, TechnicalAnalysis
from research.analytics.thesis_generator import generate_thesis, InvestmentThesis
from research.analytics.sector_intelligence import analyze_sector, SectorIntelligence
from research.analytics.valuation_engine import (
    DcfResult, ValuationAnalysis, ValuationMultiples,
    compute_historical_multiples, compute_sector_median,
    dcf_fair_value, fill_dcf_price, score_valuation,
)
from research.data.insider_fetcher import fetch_insider_transactions
from research.data.sector_data import fetch_sector_prices, SECTOR_ETF_MAP
from research.data.valuation_fetcher import fetch_current_multiples, fetch_year_end_prices, fetch_market_pe
from research.cache.screener_cache import load_screener_rows
from research.data.universe import get_universe
from research.models.fundamentals import AnnualFundamentals, CompanyProfile
from streamlit_app.styles.theme import (
    ACCENT, BG_PRIMARY, BG_SECONDARY, BG_TERTIARY, BORDER,
    DANGER, SUCCESS, TEXT_PRIMARY, TEXT_SECONDARY, WARNING,
)

_NAN = float("nan")

_VERDICT_COLORS = {
    "Strong Buy": SUCCESS,
    "Buy":        "#4ade80",
    "Hold":       WARNING,
    "Reduce":     "#f97316",
    "Avoid":      DANGER,
}


# ── Cached data fetchers ───────────────────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def _cached_price_history(ticker: str):
    return yf.Ticker(ticker).history(period="2y")


@st.cache_data(ttl=3600, show_spinner=False)
def _cached_insider(ticker: str):
    df = fetch_insider_transactions(ticker)
    return score_insider_activity(ticker, df)


@st.cache_data(ttl=3600, show_spinner=False)
def _cached_sector_prices():
    return fetch_sector_prices(period="1y")


@st.cache_data(ttl=3600, show_spinner=False)
def _cached_multiples(ticker: str):
    return fetch_current_multiples(ticker)  # returns (ValuationMultiples, price, shares)


@st.cache_data(ttl=3600, show_spinner=False)
def _cached_year_prices(ticker: str):
    return fetch_year_end_prices(ticker, years=10)


@st.cache_data(ttl=3600, show_spinner=False)
def _cached_market_pe() -> float:
    return fetch_market_pe()


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
    pct = int(max(0.0, min(100.0, score)))
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


def _pct(v: float, digits: int = 1) -> str:
    return "—" if math.isnan(v) else f"{v * 100:+.{digits}f}%"


def _num(v: float, digits: int = 1) -> str:
    return "—" if math.isnan(v) else f"{v:.{digits}f}"


def _score_color(s: float) -> str:
    if math.isnan(s):
        return TEXT_SECONDARY
    return SUCCESS if s >= 62 else DANGER if s <= 38 else WARNING


# ── Section renderers ──────────────────────────────────────────────────────────

def _render_verdict_banner(thesis: InvestmentThesis) -> None:
    color = _VERDICT_COLORS.get(thesis.verdict_label, WARNING)
    st.markdown(
        f'<div style="background:{BG_SECONDARY}; border:2px solid {color}; border-radius:10px;'
        f'padding:20px 24px; margin-bottom:18px;">'
        f'<div style="display:flex; align-items:center; gap:16px; flex-wrap:wrap;">'
        f'<div style="font-size:28px; font-weight:900; color:{color};">{thesis.verdict_label}</div>'
        f'<div style="font-size:13px; color:{TEXT_SECONDARY}; flex:1;">{thesis.verdict_rationale}</div>'
        f'<div style="text-align:right;">'
        f'<div style="font-size:9px; color:{TEXT_SECONDARY}; text-transform:uppercase; letter-spacing:0.07em;">Overall Score</div>'
        f'<div style="font-size:26px; font-weight:800; color:{color};">{thesis.overall_score:.0f}'
        f'<span style="font-size:14px; font-weight:400;">/100</span></div>'
        f'</div>'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def _render_score_strip(
    fund_score: float, val_score: float, tech_score: float,
    sector_score: float, insider_score: float,
) -> None:
    c1, c2, c3, c4, c5 = st.columns(5)
    _kpi(c1, "Fundamentals",  _num(fund_score, 0),    _score_color(fund_score),    "Quality")
    _kpi(c2, "Valuation",     _num(val_score, 0),     _score_color(val_score),     "Price vs Value")
    _kpi(c3, "Technical",     _num(tech_score, 0),    _score_color(tech_score),    "Price Action")
    _kpi(c4, "Sector",        _num(sector_score, 0),  _score_color(sector_score),  "Macro Tailwind")
    _kpi(c5, "Insider",       _num(insider_score, 0), _score_color(insider_score), "Smart Money")
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)


def _render_thesis_text(thesis: InvestmentThesis) -> None:
    _section("Investment Thesis")
    paragraphs = [
        ("Business Quality", thesis.quality_paragraph),
        ("Valuation",        thesis.valuation_paragraph),
        ("Sector Context",   thesis.sector_paragraph),
        ("Insider Activity", thesis.insider_paragraph),
        ("Technical Setup",  thesis.technical_paragraph),
    ]
    for title, text in paragraphs:
        if text:
            st.markdown(
                f'<div style="margin-bottom:12px;">'
                f'<span style="font-size:11px; font-weight:700; color:{ACCENT};">{title} — </span>'
                f'<span style="font-size:13px; color:{TEXT_PRIMARY};">{text}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )

    if thesis.risk_bullets:
        st.markdown(
            f"<div style='font-size:11px; font-weight:700; color:{DANGER}; margin-top:12px; margin-bottom:4px;'>"
            "Key Risks</div>",
            unsafe_allow_html=True,
        )
        for risk in thesis.risk_bullets:
            st.markdown(f"- {risk}")


def _render_technical_section(ta: TechnicalAnalysis) -> None:
    _section("Technical Analysis")
    c1, c2, c3, c4 = st.columns(4)
    rsi_color = (DANGER if ta.rsi_14 > 70
                 else SUCCESS if ta.rsi_14 < 30
                 else WARNING)
    _kpi(c1, "RSI-14",      _num(ta.rsi_14, 1), rsi_color)
    _kpi(c2, "vs 52w High", _pct(ta.pct_from_52w_high, 1),
         SUCCESS if not math.isnan(ta.pct_from_52w_high) and ta.pct_from_52w_high > -0.10 else DANGER)
    _kpi(c3, "Above MA200",
         "Yes" if ta.above_ma200 else "No" if ta.above_ma200 is not None else "—",
         SUCCESS if ta.above_ma200 else (DANGER if ta.above_ma200 is not None else TEXT_SECONDARY))
    _kpi(c4, "Golden Cross",
         "Yes" if ta.golden_cross else "No" if ta.golden_cross is not None else "—",
         SUCCESS if ta.golden_cross else (DANGER if ta.golden_cross is not None else TEXT_SECONDARY))

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    m1, m2, m3 = st.columns(3)
    _kpi(m1, "1M Return", _pct(ta.momentum_1m, 1),
         SUCCESS if not math.isnan(ta.momentum_1m) and ta.momentum_1m > 0 else DANGER)
    _kpi(m2, "3M Return", _pct(ta.momentum_3m, 1),
         SUCCESS if not math.isnan(ta.momentum_3m) and ta.momentum_3m > 0 else DANGER)
    _kpi(m3, "6M Return", _pct(ta.momentum_6m, 1),
         SUCCESS if not math.isnan(ta.momentum_6m) and ta.momentum_6m > 0 else DANGER)

    if ta.components:
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        st.caption("Score components")
        for comp, score in ta.components.items():
            _score_bar(score, comp)


def _render_macro_section(sector: str, intel: SectorIntelligence | None) -> None:
    _section("Macro & Sector Environment")
    if intel is None:
        st.caption("Sector data not available.")
        return

    oc = SUCCESS if intel.outlook == "Bullish" else DANGER if intel.outlook == "Bearish" else WARNING
    st.markdown(
        f'<div style="background:{BG_SECONDARY}; border:1px solid {BORDER}; border-radius:8px;'
        f'padding:14px 18px; margin-bottom:12px; font-size:13px; color:{TEXT_PRIMARY};">'
        f'<span style="font-weight:700; color:{oc};">{intel.outlook}</span> outlook for the '
        f'<strong>{sector}</strong> sector (Score: {intel.sector_score:.0f}/100). '
        f'Momentum: 1M {_pct(intel.momentum_1m)} · 3M {_pct(intel.momentum_3m)} · '
        f'12M {_pct(intel.momentum_12m)}. '
        f'Relative strength vs S&P 500: {_pct(intel.relative_strength_spy)}.'
        f'</div>',
        unsafe_allow_html=True,
    )

    if intel.swot:
        sw_col, ot_col = st.columns(2)
        with sw_col:
            st.markdown(
                f"<div style='font-size:11px; font-weight:700; color:{SUCCESS};'>Sector Strengths</div>",
                unsafe_allow_html=True,
            )
            for item in intel.swot.get("Strengths", [])[:3]:
                st.markdown(f"- {item}")
        with ot_col:
            st.markdown(
                f"<div style='font-size:11px; font-weight:700; color:{DANGER};'>Sector Threats</div>",
                unsafe_allow_html=True,
            )
            for item in intel.swot.get("Threats", [])[:3]:
                st.markdown(f"- {item}")


def _render_risk_section(thesis: InvestmentThesis) -> None:
    _section("Risk Factors")
    if not thesis.risk_bullets:
        st.caption("No specific risk factors identified.")
        return
    for i, risk in enumerate(thesis.risk_bullets, 1):
        severity = DANGER if i <= 2 else WARNING
        st.markdown(
            f'<div style="background:{BG_SECONDARY}; border-left:3px solid {severity};'
            f'border-radius:0 6px 6px 0; padding:10px 14px; margin-bottom:8px;'
            f'font-size:13px; color:{TEXT_PRIMARY};">'
            f'<span style="font-weight:700; color:{severity};">Risk {i}:</span> {risk}'
            f'</div>',
            unsafe_allow_html=True,
        )


# ── Main entry point ───────────────────────────────────────────────────────────

def render_report(
    ticker: str,
    funds: list[AnnualFundamentals],
    quarters: list,
    analysis: FundamentalAnalysis,
    profile: CompanyProfile,
) -> None:
    """Render the full Research Report for one company."""
    company_name = profile.name or ticker
    sector = profile.sector or "Unknown"

    with st.spinner("Building research report…"):
        # Technical analysis
        try:
            price_hist = _cached_price_history(ticker)
            ta: TechnicalAnalysis = score_technical(ticker, price_hist)
        except Exception:
            ta = TechnicalAnalysis(ticker=ticker)

        # Insider analysis
        try:
            insider: InsiderAnalysis | None = _cached_insider(ticker)
        except Exception:
            insider = None

        # Valuation analysis
        val_analysis: ValuationAnalysis | None = None
        try:
            multiples, current_price, shares = _cached_multiples(ticker)
            year_prices = _cached_year_prices(ticker)
            market_pe   = _cached_market_pe()
            historical  = compute_historical_multiples(funds, year_prices)

            sector_rows: list[dict] = []
            if profile.sector:
                for universe in ("S&P 500", "Nasdaq 100", "STOXX 600", "AEX"):
                    cached_rows = load_screener_rows(universe)
                    if cached_rows:
                        sector_rows.extend(
                            r for r in cached_rows if r.get("sector") == profile.sector
                        )
            sector_median = compute_sector_median(sector_rows) if sector_rows else ValuationMultiples()

            # Compute DCF with defaults (no UI sliders in report context)
            dcf = DcfResult()
            if (funds and math.isfinite(funds[0].free_cash_flow)
                    and funds[0].free_cash_flow > 0
                    and math.isfinite(shares) and shares > 0):
                dcf = dcf_fair_value(funds[0].free_cash_flow, shares)
                dcf = fill_dcf_price(dcf, current_price if math.isfinite(current_price) else _NAN)

            val_analysis = score_valuation(
                ticker, multiples, historical, sector_median, dcf, market_pe,
            )
        except Exception:
            val_analysis = None

        # Sector intelligence
        sector_intel: SectorIntelligence | None = None
        if sector in SECTOR_ETF_MAP:
            try:
                sector_prices = _cached_sector_prices()
                all_rows: list[dict] = []
                for universe in ("S&P 500", "Nasdaq 100", "STOXX 600", "AEX"):
                    tickers = get_universe(universe)
                    cached_rows = load_screener_rows(universe, tickers)
                    if cached_rows:
                        all_rows.extend(cached_rows)
                sector_intel = analyze_sector(sector, sector_prices, all_rows)
            except Exception:
                sector_intel = None

    # ── Gather scores ──────────────────────────────────────────────────────────
    fund_score    = analysis.fundamental_score if analysis else _NAN
    val_score     = val_analysis.valuation_score if val_analysis else _NAN
    tech_score    = ta.technical_score
    sector_score  = sector_intel.sector_score if sector_intel else _NAN
    insider_score = float(insider.insider_score) if insider else _NAN

    # Gather narrative inputs
    strengths      = analysis.strengths       if analysis else []
    weaknesses     = analysis.weaknesses      if analysis else []
    cheap_signals  = val_analysis.strengths   if val_analysis else []
    expensive_sigs = val_analysis.weaknesses  if val_analysis else []
    sector_outlook = sector_intel.outlook                    if sector_intel else "Neutral"
    sector_rs      = sector_intel.relative_strength_spy      if sector_intel else _NAN
    sector_threats = sector_intel.swot.get("Threats", [])   if sector_intel and sector_intel.swot else []
    insider_signal = insider.h12.signal  if insider else "Neutral"
    n_buys         = insider.h12.n_buys  if insider else 0
    n_sells        = insider.h12.n_sells if insider else 0
    tech_signal    = ta.signal

    thesis = generate_thesis(
        company_name=company_name,
        sector=sector,
        fund_score=fund_score,
        val_score=val_score,
        tech_score=tech_score,
        sector_score=sector_score,
        insider_score=insider_score,
        strengths=strengths,
        weaknesses=weaknesses,
        cheap_signals=cheap_signals,
        expensive_signals=expensive_sigs,
        sector_outlook=sector_outlook,
        sector_rs=sector_rs,
        sector_threats=sector_threats,
        insider_signal=insider_signal,
        n_buys=n_buys,
        n_sells=n_sells,
        tech_signal=tech_signal,
        ta=ta,
    )

    # ── Verdict banner ─────────────────────────────────────────────────────────
    _render_verdict_banner(thesis)

    # ── 5-score strip ──────────────────────────────────────────────────────────
    _render_score_strip(fund_score, val_score, tech_score, sector_score, insider_score)

    # ── Score breakdown bars ───────────────────────────────────────────────────
    with st.expander("Score breakdown", expanded=False):
        _score_bar(fund_score,    "Fundamental Quality (30%)")
        _score_bar(val_score,     "Valuation Attractiveness (25%)")
        _score_bar(tech_score,    "Technical Strength (20%)")
        _score_bar(sector_score,  "Sector Momentum (15%)")
        _score_bar(insider_score, "Insider Conviction (10%)")

    # ── Tabs ───────────────────────────────────────────────────────────────────
    tab_thesis, tab_tech, tab_macro, tab_risk = st.tabs(
        ["📝 Investment Thesis", "📈 Technical", "🌍 Macro & Sector", "⚠️ Risks"]
    )

    with tab_thesis:
        _render_thesis_text(thesis)

    with tab_tech:
        _render_technical_section(ta)

    with tab_macro:
        _render_macro_section(sector, sector_intel)

    with tab_risk:
        _render_risk_section(thesis)
