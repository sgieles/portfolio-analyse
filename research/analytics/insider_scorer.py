"""Insider activity scorer — pure analytics, no I/O.

Weights CEO > CFO > Executive > Director.
Applies exponential time decay (half-life 45 days) so that trades from
last week count far more than trades from 9 months ago.
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

# Exponential decay half-life in days.
# 45 days → a trade from 45d ago is worth 50% of a fresh trade;
# 90d ago → 25%; 180d ago → ~6%.
_HALFLIFE_DAYS: float = 45.0


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


def _decay(days_ago: float) -> float:
    """Exponential decay weight: 1.0 for today, 0.5 after _HALFLIFE_DAYS."""
    return math.exp(-math.log(2) * max(days_ago, 0) / _HALFLIFE_DAYS)


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
    weighted_buy_pressure: float = 0.0    # time-decay × role × value-scaled
    weighted_sell_pressure: float = 0.0

    @property
    def net_pressure(self) -> float:
        """Positive = net buying, negative = net selling."""
        return self.weighted_buy_pressure - self.weighted_sell_pressure

    @property
    def score(self) -> float:
        """0-100 where 50 = neutral, >65 = bullish, <35 = bearish."""
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
    h1:  InsiderSummary = field(default_factory=lambda: InsiderSummary(1))   # 30 days
    h3:  InsiderSummary = field(default_factory=lambda: InsiderSummary(3))
    h6:  InsiderSummary = field(default_factory=lambda: InsiderSummary(6))
    h12: InsiderSummary = field(default_factory=lambda: InsiderSummary(12))
    insider_score: float = 50.0     # 0-100, decay-weighted 12m horizon
    signal: str = "Neutral"
    # Recency fields
    days_since_last_buy:  int = -1  # -1 = no buy found
    days_since_last_sell: int = -1  # -1 = no sell found
    transactions: list[dict] = field(default_factory=list)  # last 12m, pre-formatted


def _build_summary(df: pd.DataFrame, horizon_months: int) -> InsiderSummary:
    from research.data.insider_fetcher import filter_by_horizon
    sub = filter_by_horizon(df, horizon_months)
    s = InsiderSummary(horizon_months=horizon_months)
    if sub.empty:
        return s

    now = pd.Timestamp.now(tz="UTC")

    for _, row in sub.iterrows():
        is_buy = _is_buy(str(row.get("transaction", "")))
        if is_buy is None:
            continue

        # Age of this transaction in days
        dt = row.get("date")
        try:
            if dt is not None and not pd.isnull(dt):
                if getattr(dt, "tzinfo", None) is None:
                    dt = pd.Timestamp(dt).tz_localize("UTC")
                days_ago = max(0.0, (now - dt).total_seconds() / 86400)
            else:
                days_ago = horizon_months * 30.0  # fallback: assume oldest edge
        except Exception:
            days_ago = horizon_months * 30.0

        time_weight = _decay(days_ago)
        role_weight = _role_weight(str(row.get("position", "")))
        shares = float(row.get("shares", 0) or 0)
        value  = float(row.get("value",  0) or 0)

        # Pressure = time decay × role × (1 + value_in_$M, capped at 5)
        pressure = time_weight * role_weight * (1.0 + min(value / 1e6, 5.0))

        if is_buy:
            s.n_buys               += 1
            s.shares_bought        += shares
            s.value_bought         += value
            s.weighted_buy_pressure += pressure
        else:
            s.n_sells               += 1
            s.shares_sold          += shares
            s.value_sold           += value
            s.weighted_sell_pressure += pressure
    return s


def score_insider_activity(ticker: str, df: pd.DataFrame) -> InsiderAnalysis:
    """Compute InsiderAnalysis from a raw transactions DataFrame.

    Time decay (half-life 45 days) is applied to every transaction so that
    recent trades dominate the score; trades older than ~6 months contribute
    less than 10% of their face weight.

    Args:
        ticker: The ticker symbol (for display).
        df: Raw DataFrame from insider_fetcher.fetch_insider_transactions().

    Returns:
        InsiderAnalysis with per-horizon summaries and an overall score.
    """
    analysis = InsiderAnalysis(ticker=ticker)
    if df.empty:
        return analysis

    analysis.h1  = _build_summary(df, 1)    # ~30 days
    analysis.h3  = _build_summary(df, 3)
    analysis.h6  = _build_summary(df, 6)
    analysis.h12 = _build_summary(df, 12)

    analysis.insider_score = analysis.h12.score
    analysis.signal        = analysis.h12.signal

    # Recency: days since last buy / sell across all history
    now = pd.Timestamp.now(tz="UTC")
    last_buy_days  = -1
    last_sell_days = -1
    for _, row in df.iterrows():
        is_buy = _is_buy(str(row.get("transaction", "")))
        if is_buy is None:
            continue
        dt = row.get("date")
        try:
            if dt is not None and not pd.isnull(dt):
                if getattr(dt, "tzinfo", None) is None:
                    dt = pd.Timestamp(dt).tz_localize("UTC")
                days_ago = int((now - dt).total_seconds() / 86400)
                if is_buy:
                    last_buy_days  = days_ago if last_buy_days  < 0 else min(last_buy_days,  days_ago)
                else:
                    last_sell_days = days_ago if last_sell_days < 0 else min(last_sell_days, days_ago)
        except Exception:
            pass

    analysis.days_since_last_buy  = last_buy_days
    analysis.days_since_last_sell = last_sell_days

    # Pre-format transactions for the UI (last 12m only, with days-ago)
    from research.data.insider_fetcher import filter_by_horizon
    sub12 = filter_by_horizon(df, 12)
    rows: list[dict] = []
    for _, row in sub12.iterrows():
        is_buy = _is_buy(str(row.get("transaction", "")))
        if is_buy is None:
            continue
        dt = row.get("date")
        days_ago = -1
        try:
            if dt is not None and not pd.isnull(dt):
                if getattr(dt, "tzinfo", None) is None:
                    dt = pd.Timestamp(dt).tz_localize("UTC")
                days_ago = int((now - dt).total_seconds() / 86400)
        except Exception:
            pass

        recency = (
            "🔴 Today"         if days_ago == 0  else
            f"🔴 {days_ago}d"  if 0 < days_ago <= 14 else
            f"🟡 {days_ago}d"  if days_ago <= 30 else
            f"{days_ago}d"
        )

        rows.append({
            "Recency":     recency,
            "Date":        str(dt.date()) if hasattr(dt, "date") else str(dt),
            "Insider":     str(row.get("insider", "—")),
            "Role":        str(row.get("position", "—")),
            "Type":        "Buy" if is_buy else "Sell",
            "Shares":      int(row.get("shares", 0) or 0),
            "Value ($)":   f"${float(row.get('value', 0) or 0):,.0f}",
        })
    analysis.transactions = rows
    return analysis
