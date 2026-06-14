"""Streamlit session-state management.

All mutable app state lives in st.session_state under these keys so it
survives widget interactions and page re-runs.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import streamlit as st

if TYPE_CHECKING:
    from models.portfolio import Portfolio
    from models.results import AnalysisResult
    from models.settings import AnalysisSettings


# ── Key constants ──────────────────────────────────────────────────────────────
_PORTFOLIO    = "portfolio"
_SETTINGS     = "settings"
_RESULT       = "analysis_result"
_TICKERS_INPUT = "tickers_input"


def init() -> None:
    """Initialise all session-state keys that haven't been set yet."""
    from models.asset import Asset
    from models.portfolio import Portfolio
    from models.settings import AnalysisSettings

    if _PORTFOLIO not in st.session_state:
        st.session_state[_PORTFOLIO] = Portfolio()
    if _SETTINGS not in st.session_state:
        st.session_state[_SETTINGS] = AnalysisSettings()
    if _RESULT not in st.session_state:
        st.session_state[_RESULT] = None
    if _TICKERS_INPUT not in st.session_state:
        st.session_state[_TICKERS_INPUT] = ""


# ── Accessors ──────────────────────────────────────────────────────────────────

def get_portfolio() -> "Portfolio":
    return st.session_state[_PORTFOLIO]


def set_portfolio(pf: "Portfolio") -> None:
    st.session_state[_PORTFOLIO] = pf


def get_settings() -> "AnalysisSettings":
    return st.session_state[_SETTINGS]


def get_result() -> "AnalysisResult | None":
    return st.session_state[_RESULT]


def set_result(result: "AnalysisResult") -> None:
    st.session_state[_RESULT] = result


def clear_result() -> None:
    st.session_state[_RESULT] = None
