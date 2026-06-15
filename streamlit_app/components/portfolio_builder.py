"""Sidebar portfolio builder — add/remove tickers, edit weights."""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = str(Path(__file__).resolve().parent.parent.parent)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import streamlit as st

from models.asset import Asset
from models.portfolio import Portfolio
from services.portfolio_io import load_portfolio, save_portfolio
from streamlit_app.state import session
from streamlit_app.styles.theme import ACCENT, BG_TERTIARY, BG_SECONDARY, BORDER, TEXT_PRIMARY, TEXT_SECONDARY
from utils.constants import ANALYSIS_PERIODS, BENCHMARKS, DEFAULT_BENCHMARK, DEFAULT_PERIOD
from utils.validators import validate_ticker
from utils.ticker_suggestions import ticker_options, extract_ticker

import tempfile


def render() -> bool:
    """Render the sidebar portfolio builder.

    Returns True if the portfolio changed and a re-analysis is needed.
    """
    pf = session.get_portfolio()
    changed = False

    st.sidebar.markdown(
        f"""
        <div style="padding:4px 0 2px 0">
            <div style="font-size:17px; font-weight:800; color:{ACCENT}; letter-spacing:-0.01em;">
                Portfolio Analyser
            </div>
            <div style="font-size:11px; color:{TEXT_SECONDARY}; margin-top:2px;">
                Professional portfolio analytics
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.sidebar.divider()

    # ── Add ticker ─────────────────────────────────────────────────────────────
    st.sidebar.markdown("**Portfolio Builder**")

    selected_suggestion = st.sidebar.selectbox(
        "Ticker",
        options=ticker_options(),
        index=None,
        placeholder="Search ticker or company name…",
        key="ticker_selectbox",
        label_visibility="collapsed",
    )

    add_clicked = st.sidebar.button("Add", use_container_width=True, key="btn_add_ticker")

    if add_clicked and selected_suggestion:
        raw = extract_ticker(selected_suggestion)
        try:
            validate_ticker(raw)
            if raw not in pf.tickers:
                pf.assets.append(Asset(ticker=raw, weight=0.0))
                _rebalance_equal(pf)
                _sync_slider_states(pf)
                session.set_portfolio(pf)
                session.clear_result()
                # Reset selectbox to placeholder (del is allowed after render; = is not)
                st.session_state.pop("ticker_selectbox", None)
                changed = True
            else:
                st.sidebar.warning(f"{raw} already in portfolio.")
        except ValueError as e:
            st.sidebar.error(str(e))

    # ── Weight sliders ─────────────────────────────────────────────────────────
    if pf.assets:
        st.sidebar.markdown("**Weights**")
        new_weights: dict[str, float] = {}
        for asset in pf.assets:
            new_weights[asset.ticker] = st.sidebar.slider(
                asset.ticker,
                min_value=0.0, max_value=1.0,
                value=float(round(asset.weight, 4)),
                step=0.01,
                key=f"slider_{asset.ticker}",
            )

        # Normalise and push back to portfolio
        total = sum(new_weights.values())
        for asset in pf.assets:
            asset.weight = new_weights[asset.ticker] / total if total > 0 else 1.0 / len(pf.assets)

        # Total weight indicator
        total_pct = sum(a.weight for a in pf.assets) * 100
        st.sidebar.caption(f"Total: {total_pct:.1f} %")

        # Remove button
        to_remove = st.sidebar.selectbox(
            "Remove ticker", options=["—"] + pf.tickers, key="remove_select"
        )
        if to_remove != "—":
            if st.sidebar.button(f"Remove {to_remove}", key="btn_remove"):
                pf.assets = [a for a in pf.assets if a.ticker != to_remove]
                if pf.assets:
                    _rebalance_equal(pf)
                    _sync_slider_states(pf)
                session.set_portfolio(pf)
                session.clear_result()
                changed = True

        # Quick weight actions
        c1, c2 = st.sidebar.columns(2)
        with c1:
            if st.button("Equal Weight", use_container_width=True, key="btn_eq"):
                _rebalance_equal(pf)
                _sync_slider_states(pf)
                session.set_portfolio(pf)
                session.clear_result()
                changed = True
        with c2:
            if st.button("Normalize", use_container_width=True, key="btn_norm"):
                try:
                    pf.normalize_weights()
                    _sync_slider_states(pf)
                    session.set_portfolio(pf)
                    session.clear_result()
                    changed = True
                except ValueError:
                    pass

    st.sidebar.divider()

    # ── Benchmark & period ─────────────────────────────────────────────────────
    st.sidebar.markdown("**Settings**")
    benchmark = st.sidebar.selectbox(
        "Benchmark", BENCHMARKS,
        index=BENCHMARKS.index(pf.benchmark) if pf.benchmark in BENCHMARKS else 0,
        key="benchmark_sel",
    )
    period = st.sidebar.selectbox(
        "Period", ANALYSIS_PERIODS,
        index=ANALYSIS_PERIODS.index(pf.period) if pf.period in ANALYSIS_PERIODS else 2,
        key="period_sel",
    )
    if benchmark != pf.benchmark or period != pf.period:
        pf.benchmark = benchmark
        pf.period    = period
        session.set_portfolio(pf)
        session.clear_result()
        changed = True

    st.sidebar.divider()

    # ── Load portfolio JSON ────────────────────────────────────────────────────
    st.sidebar.markdown("**Load Portfolio**")
    uploaded = st.sidebar.file_uploader("Load portfolio JSON", type="json", key="pf_upload")
    if uploaded is not None:
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
            tmp.write(uploaded.read())
            tmp_path = Path(tmp.name)
        try:
            loaded_pf, loaded_settings = load_portfolio(tmp_path)
            session.set_portfolio(loaded_pf)
            session.clear_result()
            st.sidebar.success("Portfolio loaded.")
            changed = True
        except Exception as exc:
            st.sidebar.error(f"Load failed: {exc}")
        finally:
            tmp_path.unlink(missing_ok=True)

    return changed


def _rebalance_equal(pf: Portfolio) -> None:
    n = len(pf.assets)
    if n:
        w = round(1.0 / n, 6)
        for a in pf.assets:
            a.weight = w


def _sync_slider_states(pf: Portfolio) -> None:
    """Write portfolio weights into the slider session-state keys.

    Streamlit sliders store their value in st.session_state[key]. If we
    update portfolio weights without also updating the session-state key,
    the slider re-renders with the old value on the next run and overwrites
    the new weight.
    """
    for a in pf.assets:
        st.session_state[f"slider_{a.ticker}"] = round(a.weight, 4)
