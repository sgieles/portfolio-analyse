"""Stock Screener page — Phase 17.

Loads yfinance info + price momentum per ticker, scores each one, and presents
a filterable/sortable table.  Results are cached daily per universe so repeat
visits within the same day are instant.
"""

from __future__ import annotations

import math
import sys
from dataclasses import asdict
from pathlib import Path

_ROOT = str(Path(__file__).resolve().parent.parent.parent)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import pandas as pd
import streamlit as st
import yfinance as yf

from research.analytics.screener import ScreenerRow, score_from_info
from research.cache.screener_cache import load_screener_rows, save_screener_rows
from research.data.universe import UNIVERSE_NAMES, get_universe, universe_size_hint
from streamlit_app.styles.theme import (
    ACCENT, BG_SECONDARY, BORDER, DANGER, SUCCESS,
    TEXT_PRIMARY, TEXT_SECONDARY, WARNING,
)

import logging
_log = logging.getLogger(__name__)

_NAN = float("nan")


# ── Cached data fetchers (Streamlit layer — network I/O allowed) ──────────────

@st.cache_data(ttl=3600, show_spinner=False)
def _fetch_info(ticker: str) -> dict:
    """Fetch yfinance info dict for a single ticker; cached 1 hour."""
    try:
        return dict(yf.Ticker(ticker).info)
    except Exception as exc:
        _log.warning("yfinance info failed for %s: %s", ticker, exc)
        return {}


@st.cache_data(ttl=3600, show_spinner=False)
def _batch_momentum(tickers: tuple[str, ...]) -> dict[str, tuple[float, float, float]]:
    """Download 6 months of prices and return (mom_1m, mom_3m, mom_6m) per ticker.

    Uses yf.download for efficiency — one batch HTTP call for all tickers.
    """
    if not tickers:
        return {}
    try:
        raw = yf.download(list(tickers), period="6mo", auto_adjust=True,
                          progress=False, group_by="ticker")
    except Exception as exc:
        _log.warning("Batch price download failed: %s", exc)
        return {}

    result: dict[str, tuple[float, float, float]] = {}
    for ticker in tickers:
        try:
            if len(tickers) == 1:
                col = raw["Close"]
            else:
                col = raw[ticker]["Close"] if ticker in raw.columns.get_level_values(0) else None
            if col is None:
                continue
            col = col.dropna()
            if len(col) < 5:
                continue
            latest = float(col.iloc[-1])

            def _mom(days: int) -> float:
                idx = max(0, len(col) - days)
                past = float(col.iloc[idx])
                return (latest / past - 1.0) if past != 0 else _NAN

            result[ticker] = (_mom(21), _mom(63), _mom(126))
        except Exception:
            continue
    return result


# ── Screener orchestration ────────────────────────────────────────────────────

def _build_rows(universe: str, tickers: list[str]) -> list[ScreenerRow]:
    """Fetch info + momentum for each ticker; return scored ScreenerRows."""
    moms = _batch_momentum(tuple(tickers))

    progress = st.progress(0, text=f"Loading {len(tickers)} tickers…")
    rows: list[ScreenerRow] = []
    n = len(tickers)

    for i, ticker in enumerate(tickers):
        info = _fetch_info(ticker)
        m1, m3, m6 = moms.get(ticker, (_NAN, _NAN, _NAN))
        rows.append(score_from_info(ticker, info, m1, m3, m6))
        progress.progress((i + 1) / n, text=f"Scoring {ticker} ({i+1}/{n})…")

    progress.empty()
    save_screener_rows(universe, rows)
    return rows


def _load_or_build(universe: str) -> list[ScreenerRow]:
    """Return cached screener rows (today) or build them fresh."""
    cached = load_screener_rows(universe)
    if cached is not None:
        return [ScreenerRow(**r) for r in cached]
    tickers = get_universe(universe)
    if not tickers:
        st.error(f"Could not fetch ticker list for {universe}.")
        return []
    return _build_rows(universe, tickers)


# ── Display helpers ───────────────────────────────────────────────────────────

def _fmt_score(v: float) -> str:
    return "—" if math.isnan(v) else f"{v:.0f}"


def _fmt_pct(v: float) -> str:
    return "—" if math.isnan(v) else f"{v * 100:.1f}%"


def _fmt_pe(v: float) -> str:
    return "—" if math.isnan(v) else f"{v:.1f}×"


def _fmt_cap(v: float) -> str:
    if math.isnan(v):
        return "—"
    if v >= 1e12:
        return f"${v/1e12:.1f}T"
    if v >= 1e9:
        return f"${v/1e9:.1f}B"
    return f"${v/1e6:.0f}M"


def _score_color(v: float) -> str:
    if math.isnan(v):
        return TEXT_SECONDARY
    if v >= 65:
        return SUCCESS
    if v >= 40:
        return WARNING
    return DANGER


def _score_badge(v: float) -> str:
    color = _score_color(v)
    label = _fmt_score(v)
    return (
        f"<span style='background:{color}22; color:{color}; "
        f"border-radius:4px; padding:2px 6px; font-size:13px; "
        f"font-weight:700;'>{label}</span>"
    )


def _rows_to_df(rows: list[ScreenerRow]) -> pd.DataFrame:
    records = []
    for r in rows:
        records.append({
            "Ticker":        r.ticker,
            "Company":       (r.name[:28] + "…") if len(r.name) > 28 else r.name,
            "Sector":        r.sector or "—",
            "Country":       r.country or "—",
            "Market Cap":    r.market_cap,
            "Overall":       r.overall_score,
            "Fundamentals":  r.fundamental_score,
            "Valuation":     r.valuation_score,
            "Trend":         r.trend_score,
            "P/E":           r.trailing_pe,
            "Fwd P/E":       r.forward_pe,
            "P/B":           r.price_to_book,
            "Div Yield":     r.dividend_yield,
            "Rev Growth":    r.revenue_growth,
            "ROE":           r.return_on_equity,
        })
    return pd.DataFrame(records)


# ── Filter controls ───────────────────────────────────────────────────────────

def _apply_filters(df: pd.DataFrame) -> pd.DataFrame:
    sectors = sorted(s for s in df["Sector"].unique() if s and s != "—")
    countries = sorted(c for c in df["Country"].unique() if c and c != "—")

    fc1, fc2, fc3 = st.columns(3)
    with fc1:
        sel_sector = st.multiselect("Sector", sectors, key="scr_sector")
    with fc2:
        sel_country = st.multiselect("Country", countries, key="scr_country")
    with fc3:
        min_score = st.slider("Min Overall Score", 0, 100, 0, key="scr_min_score")

    if sel_sector:
        df = df[df["Sector"].isin(sel_sector)]
    if sel_country:
        df = df[df["Country"].isin(sel_country)]
    df = df[df["Overall"].isna() | (df["Overall"] >= min_score)]
    return df


# ── Main render ───────────────────────────────────────────────────────────────

def render() -> None:
    _section = (
        f"<h3 style='color:{TEXT_PRIMARY}; margin:0 0 4px 0; font-size:17px;'>"
        "Stock Screener</h3>"
        f"<p style='color:{TEXT_SECONDARY}; font-size:13px; margin:0 0 16px 0;'>"
        "Scores are computed from yfinance fundamentals and price momentum. "
        "Data is cached for the day — click <b>Refresh</b> to reload.</p>"
    )
    st.markdown(_section, unsafe_allow_html=True)

    # ── Universe selector ────────────────────────────────────────────────────
    u_cols = st.columns(len(UNIVERSE_NAMES) + 2)
    universe = u_cols[0].selectbox(
        "Universe", UNIVERSE_NAMES, index=0, key="scr_universe",
        label_visibility="collapsed",
    )
    hint = universe_size_hint(universe)

    run_btn = u_cols[1].button("▶ Run Screener", type="primary", key="scr_run")
    refresh_btn = u_cols[2].button("↺ Refresh", key="scr_refresh")

    # Check for cached today's data
    cached_rows = load_screener_rows(universe)
    has_cache = cached_rows is not None

    if has_cache and not refresh_btn:
        # Use cached data
        st.caption(
            f"Showing today's cached results for **{universe}** ({len(cached_rows)} tickers). "
            "Click **↺ Refresh** to reload from yfinance."
        )
        rows = [ScreenerRow(**r) for r in cached_rows]
    elif run_btn or refresh_btn:
        if hint > 100:
            st.info(
                f"Loading **{hint} tickers** from yfinance. "
                f"First run takes ~{hint // 10} min; results are cached for the day."
            )
        tickers = get_universe(universe)
        if not tickers:
            st.error("Could not retrieve ticker list. Check your internet connection.")
            return
        rows = _build_rows(universe, tickers)
    else:
        # Nothing cached, nothing triggered — show prompt
        st.info(
            f"**{universe}** has ~{hint} tickers. "
            "Click **▶ Run Screener** to load and score them."
        )
        return

    if not rows:
        st.warning("No screener data available.")
        return

    df = _rows_to_df(rows)

    st.markdown(
        f"<hr style='border:none; border-top:1px solid {BORDER}; margin:10px 0 16px 0;'>",
        unsafe_allow_html=True,
    )

    # ── Filters ──────────────────────────────────────────────────────────────
    df = _apply_filters(df)

    if df.empty:
        st.warning("No tickers match the current filters.")
        return

    st.caption(f"Showing **{len(df)}** tickers")

    # ── Score summary strip ──────────────────────────────────────────────────
    valid_overall = df["Overall"].dropna()
    if not valid_overall.empty:
        s1, s2, s3, s4, s5 = st.columns(5)
        def _kpi(col, label: str, value: str, color: str = TEXT_PRIMARY) -> None:
            col.markdown(
                f"""<div style="background:{BG_SECONDARY}; border:1px solid {BORDER};
                            border-radius:8px; padding:10px 12px; text-align:center;">
                    <div style="font-size:9px; color:{TEXT_SECONDARY}; text-transform:uppercase;
                                letter-spacing:.07em; margin-bottom:4px;">{label}</div>
                    <div style="font-size:18px; font-weight:700; color:{color};">{value}</div>
                </div>""",
                unsafe_allow_html=True,
            )
        _kpi(s1, "Median Score", f"{valid_overall.median():.0f}")
        _kpi(s2, "Avg Score",    f"{valid_overall.mean():.0f}")
        top_row = df.nlargest(1, "Overall").iloc[0]
        _kpi(s3, "Top Pick",     top_row["Ticker"], ACCENT)
        high_q  = (valid_overall >= 65).sum()
        _kpi(s4, "Score ≥ 65",  str(high_q), SUCCESS)
        low_q   = (valid_overall < 40).sum()
        _kpi(s5, "Score < 40",  str(low_q), DANGER)
        st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

    # ── Sortable table ───────────────────────────────────────────────────────
    display_df = df.copy()

    # Format display columns
    display_df["Market Cap"]   = display_df["Market Cap"].map(_fmt_cap)
    display_df["Overall"]      = display_df["Overall"].map(_fmt_score)
    display_df["Fundamentals"] = display_df["Fundamentals"].map(_fmt_score)
    display_df["Valuation"]    = display_df["Valuation"].map(_fmt_score)
    display_df["Trend"]        = display_df["Trend"].map(_fmt_score)
    display_df["P/E"]          = display_df["P/E"].map(_fmt_pe)
    display_df["Fwd P/E"]      = display_df["Fwd P/E"].map(_fmt_pe)
    display_df["P/B"]          = display_df["P/B"].map(lambda v: "—" if math.isnan(v) else f"{v:.1f}×")
    display_df["Div Yield"]    = display_df["Div Yield"].map(_fmt_pct)
    display_df["Rev Growth"]   = display_df["Rev Growth"].map(_fmt_pct)
    display_df["ROE"]          = display_df["ROE"].map(_fmt_pct)

    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Ticker":        st.column_config.TextColumn("Ticker", width=80),
            "Company":       st.column_config.TextColumn("Company", width=180),
            "Sector":        st.column_config.TextColumn("Sector", width=120),
            "Country":       st.column_config.TextColumn("Country", width=80),
            "Market Cap":    st.column_config.TextColumn("Mkt Cap", width=80),
            "Overall":       st.column_config.TextColumn("Overall", width=70),
            "Fundamentals":  st.column_config.TextColumn("Fund.", width=60),
            "Valuation":     st.column_config.TextColumn("Val.", width=60),
            "Trend":         st.column_config.TextColumn("Trend", width=60),
            "P/E":           st.column_config.TextColumn("P/E", width=70),
            "Fwd P/E":       st.column_config.TextColumn("Fwd P/E", width=70),
            "P/B":           st.column_config.TextColumn("P/B", width=60),
            "Div Yield":     st.column_config.TextColumn("Div Yld", width=70),
            "Rev Growth":    st.column_config.TextColumn("Rev Grw", width=70),
            "ROE":           st.column_config.TextColumn("ROE", width=60),
        },
    )

    # ── Asset detail expander ────────────────────────────────────────────────
    _render_detail_picker(rows)


def _render_detail_picker(rows: list[ScreenerRow]) -> None:
    """Show a selectbox to drill into one ticker's scores."""
    st.markdown(
        f"<hr style='border:none; border-top:1px solid {BORDER}; margin:18px 0 14px 0;'>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"<h4 style='color:{TEXT_PRIMARY}; margin:0 0 10px 0; font-size:15px;'>"
        "Ticker Detail</h4>",
        unsafe_allow_html=True,
    )

    tickers_sorted = sorted((r.ticker for r in rows), key=lambda t: t)
    sel = st.selectbox("Select ticker", tickers_sorted, key="scr_detail_ticker")
    if not sel:
        return

    row = next((r for r in rows if r.ticker == sel), None)
    if row is None:
        return

    if row.error:
        st.warning(f"No data available for {sel}: {row.error}")
        return

    # Company header
    st.markdown(
        f"""<div style="background:{BG_SECONDARY}; border:1px solid {BORDER};
                    border-radius:8px; padding:14px 18px; margin-bottom:12px;">
            <div style="font-size:17px; font-weight:700; color:{TEXT_PRIMARY};">
                {row.name or sel}
                <span style="font-size:12px; font-weight:400; color:{TEXT_SECONDARY};
                             margin-left:10px;">{sel}</span>
            </div>
            <div style="font-size:12px; color:{TEXT_SECONDARY}; margin-top:4px;">
                {row.sector or "—"} · {row.industry or "—"} ·
                {row.country or "—"} · {_fmt_cap(row.market_cap)}
            </div>
        </div>""",
        unsafe_allow_html=True,
    )

    # Score cards
    def _score_card(col, label: str, v: float) -> None:
        color = _score_color(v)
        col.markdown(
            f"""<div style="background:{color}11; border:1px solid {color}44;
                        border-radius:8px; padding:10px 12px; text-align:center;">
                <div style="font-size:9px; color:{TEXT_SECONDARY}; text-transform:uppercase;
                            letter-spacing:.07em; margin-bottom:4px;">{label}</div>
                <div style="font-size:22px; font-weight:800; color:{color};">{_fmt_score(v)}</div>
            </div>""",
            unsafe_allow_html=True,
        )

    c1, c2, c3, c4 = st.columns(4)
    _score_card(c1, "Overall", row.overall_score)
    _score_card(c2, "Fundamentals", row.fundamental_score)
    _score_card(c3, "Valuation", row.valuation_score)
    _score_card(c4, "Trend", row.trend_score)

    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

    # Key metrics grid
    metrics = [
        ("Trailing P/E",  _fmt_pe(row.trailing_pe)),
        ("Forward P/E",   _fmt_pe(row.forward_pe)),
        ("Price/Book",    f"{row.price_to_book:.1f}×" if not math.isnan(row.price_to_book) else "—"),
        ("Dividend Yield", _fmt_pct(row.dividend_yield)),
        ("Revenue Growth", _fmt_pct(row.revenue_growth)),
        ("EPS Growth",    _fmt_pct(row.earnings_growth)),
        ("Gross Margin",  _fmt_pct(row.gross_margin)),
        ("Op. Margin",    _fmt_pct(row.operating_margin)),
        ("ROE",           _fmt_pct(row.return_on_equity)),
        ("D/E Ratio",     f"{row.debt_to_equity/100:.2f}×" if not math.isnan(row.debt_to_equity) else "—"),
        ("Mom 1M",        _fmt_pct(row.mom_1m)),
        ("Mom 3M",        _fmt_pct(row.mom_3m)),
    ]
    cols = st.columns(6)
    kpi_style = (
        f"background:{BG_SECONDARY}; border:1px solid {BORDER}; border-radius:6px;"
        " padding:8px 10px; text-align:center; margin-bottom:8px;"
    )
    for idx, (label, value) in enumerate(metrics):
        cols[idx % 6].markdown(
            f"""<div style="{kpi_style}">
                <div style="font-size:9px; color:{TEXT_SECONDARY}; text-transform:uppercase;
                            letter-spacing:.07em; margin-bottom:3px;">{label}</div>
                <div style="font-size:14px; font-weight:600; color:{TEXT_PRIMARY};">{value}</div>
            </div>""",
            unsafe_allow_html=True,
        )
