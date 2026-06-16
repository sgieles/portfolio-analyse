"""Insider activity scorer — pure analytics, no I/O.

Weights CEO > CFO > Executive > Director.
Score 0-100: 50 = neutral, 100 = aggressive buying, 0 = aggressive selling.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import pandas as pd

# Role weight map (keywords, matched case-insensitively)
_ROLE_WEIGHTS: list[tuple[str, float]] = [
    ("chief executive", 1.0),
    ("ceo",             1.0),
    ("exec chair",      0.9),
    ("chief financial", 0.9),
    ("cfo",             0.9),
    ("president",       0.8),
    ("chief operating", 0.75),
    ("coo",             0.75),
    ("officer",         0.65),
    ("director",        0.50),
]

_BUY_KEYWORDS  = ("buy", "purchase")
_SELL_KEYWORDS = ("sale", "sell")


def _role_weight(position: str) -> float:
    pos = str(position).lower()
    for keyword, weight in _ROLE_WEIGHTS:
        if keyword in pos:
            return weight
    return 0.4  # unknown role


def _is_buy(transaction: str) -> bool | None:
    t = str(transaction).lower()
    if any(k in t for k in _BUY_KEYWORDS):
        return True
    if any(k in t for k in _SELL_KEYWORDS):
        return False
    return None  # gift, option exercise, etc. — exclude


@dataclass
class InsiderSummary:
    """Aggregated insider activity for one time horizon."""
    horizon_months: int
    n_buys: int = 0
    n_sells: int = 0
    shares_bought: float = 0.0
    shares_sold: float = 0.0
    value_bought: float = 0.0
    value_sold: float = 0.0
    weighted_buy_pressure: float = 0.0
    weighted_sell_pressure: float = 0.0

    @property
    def net_pressure(self) -> float:
        """Positive = net buying, negative = net selling."""
        return self.weighted_buy_pressure - self.weighted_sell_pressure

    @property
    def score(self) -> float:
        """0-100 where 50 = neutral, >60 = bullish, <40 = bearish."""
        total = self.weighted_buy_pressure + self.weighted_sell_pressure
        if total == 0:
            return 50.0
        return (self.weighted_buy_pressure / total) * 100

    @property
    def signal(self) -> str:
        s = self.score
        if s >= 65:
            return "Bullish"
        if s <= 35:
            return "Bearish"
        return "Neutral"


@dataclass
class InsiderAnalysis:
    ticker: str
    h3:  InsiderSummary = field(default_factory=lambda: InsiderSummary(3))
    h6:  InsiderSummary = field(default_factory=lambda: InsiderSummary(6))
    h12: InsiderSummary = field(default_factory=lambda: InsiderSummary(12))
    insider_score: float = 50.0  # 0-100, based on 12m horizon
    signal: str = "Neutral"
    transactions: list[dict] = field(default_factory=list)  # last 12m, pre-formatted


def _build_summary(df: pd.DataFrame, horizon_months: int) -> InsiderSummary:
    from research.data.insider_fetcher import filter_by_horizon
    sub = filter_by_horizon(df, horizon_months)
    s = InsiderSummary(horizon_months=horizon_months)
    if sub.empty:
        return s
    for _, row in sub.iterrows():
        is_buy = _is_buy(str(row.get("transaction", "")))
        if is_buy is None:
            continue
        weight = _role_weight(str(row.get("position", "")))
        shares = float(row.get("shares", 0) or 0)
        value  = float(row.get("value",  0) or 0)
        pressure = weight * (1.0 + min(value / 1e6, 5.0))  # scale by $M, capped
        if is_buy:
            s.n_buys             += 1
            s.shares_bought      += shares
            s.value_bought       += value
            s.weighted_buy_pressure += pressure
        else:
            s.n_sells            += 1
            s.shares_sold        += shares
            s.value_sold         += value
            s.weighted_sell_pressure += pressure
    return s


def score_insider_activity(ticker: str, df: pd.DataFrame) -> InsiderAnalysis:
    """Compute InsiderAnalysis from a raw transactions DataFrame.

    Args:
        ticker: The ticker symbol (for display).
        df: Raw DataFrame from insider_fetcher.fetch_insider_transactions().

    Returns:
        InsiderAnalysis with per-horizon summaries and an overall score.
    """
    analysis = InsiderAnalysis(ticker=ticker)
    if df.empty:
        return analysis

    analysis.h3  = _build_summary(df, 3)
    analysis.h6  = _build_summary(df, 6)
    analysis.h12 = _build_summary(df, 12)

    analysis.insider_score = analysis.h12.score
    analysis.signal        = analysis.h12.signal

    # Pre-format transactions for the UI (last 12m only)
    from research.data.insider_fetcher import filter_by_horizon
    sub12 = filter_by_horizon(df, 12)
    rows: list[dict] = []
    for _, row in sub12.iterrows():
        is_buy = _is_buy(str(row.get("transaction", "")))
        if is_buy is None:
            continue
        dt = row.get("date")
        rows.append({
            "Date":        str(dt.date()) if hasattr(dt, "date") else str(dt),
            "Insider":     str(row.get("insider", "—")),
            "Role":        str(row.get("position", "—")),
            "Type":        "Buy" if is_buy else "Sell",
            "Shares":      int(row.get("shares", 0) or 0),
            "Value ($)":   f"${float(row.get('value', 0) or 0):,.0f}",
        })
    analysis.transactions = rows
    return analysis
