"""Insider transaction fetcher — yfinance source.

Returns raw transaction DataFrames (buy/sell/gift) for a ticker.
All network I/O is isolated here; the scorer is pure.
"""

from __future__ import annotations

import logging
from datetime import date, timedelta

import pandas as pd

_log = logging.getLogger(__name__)

# yfinance `Position` strings that map to CEO role
_CEO_ROLES = {"ceo", "chief executive officer", "chief executive", "exec chairman"}
_CFO_ROLES = {"cfo", "chief financial officer", "chief financial"}
_BUY_TRANSACTIONS = {"buy", "purchase"}
_SELL_TRANSACTIONS = {"sale", "sell"}


def fetch_insider_transactions(ticker: str) -> pd.DataFrame:
    """Return insider transactions DataFrame from yfinance.

    Columns preserved: Insider, Position, Transaction, Start Date, Shares, Value.
    Returns empty DataFrame if unavailable.
    """
    try:
        import yfinance as yf
        df = yf.Ticker(ticker).insider_transactions
        if df is None or df.empty:
            return pd.DataFrame()

        # Normalize column names
        df = df.rename(columns={"Start Date": "date"})
        df.columns = [c.lower().replace(" ", "_") for c in df.columns]

        # Keep only relevant columns that exist
        want = [c for c in ("date", "insider", "position", "transaction",
                             "shares", "value") if c in df.columns]
        df = df[want].copy()

        # Parse dates
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"], errors="coerce")
            df = df.dropna(subset=["date"])
            df = df.sort_values("date", ascending=False)

        # Numeric coercion
        for col in ("shares", "value"):
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

        return df.reset_index(drop=True)
    except Exception as exc:
        _log.warning("insider_transactions failed for %s: %s", ticker, exc)
        return pd.DataFrame()


def filter_by_horizon(df: pd.DataFrame, months: int) -> pd.DataFrame:
    """Return rows within the last *months* months."""
    if df.empty or "date" not in df.columns:
        return df
    cutoff = pd.Timestamp(date.today() - timedelta(days=months * 30))
    return df[df["date"] >= cutoff].copy()
