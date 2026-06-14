"""Asset Analysis page — per-asset sortable metrics table."""

from __future__ import annotations

import math

import streamlit as st

from streamlit_app.state import session


def _pct(v: float) -> str:
    return "—" if math.isnan(v) else f"{v * 100:.2f} %"


def _num(v: float) -> str:
    return "—" if math.isnan(v) else f"{v:.2f}"


def _eur(v: float) -> str:
    return "—" if math.isnan(v) else f"€ {v:,.2f}"


def render() -> None:
    result = session.get_result()
    if result is None:
        st.info("Run an analysis on the Dashboard first.")
        return

    st.markdown("### Asset Analysis")
    st.caption(f"Period: {result.portfolio.period}  ·  Benchmark: {result.portfolio.benchmark}")

    rows = []
    for m in result.asset_metrics.values():
        rows.append({
            "Ticker":           m.ticker,
            "Weight":           _pct(m.weight),
            "Latest Price":     _eur(m.latest_price),
            "CAGR":             _pct(m.cagr),
            "Return (ann.)":    _pct(m.annualized_return),
            "Volatility":       _pct(m.volatility),
            "Sharpe":           _num(m.sharpe),
            "Sortino":          _num(m.sortino),
            "Beta":             _num(m.beta),
            "Max Drawdown":     _pct(m.max_drawdown),
            "VaR 95 %":         _pct(m.var_95),
            "VaR 99 %":         _pct(m.var_99),
            "CVaR":             _pct(m.cvar),
            "Risk Contrib.":    _pct(m.risk_contribution),
            "Return Contrib.":  _pct(m.return_contribution),
        })

    st.dataframe(rows, use_container_width=True, hide_index=True)
