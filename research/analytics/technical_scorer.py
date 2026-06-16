"""Technical analysis scorer — pure analytics, no I/O.

Scores price behaviour on a 0-100 scale where:
  >65 = Strong technical setup
  55-65 = Positive
  45-55 = Neutral
  35-45 = Negative
  <35 = Weak / broken trend
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import pandas as pd
import numpy as np


@dataclass
class TechnicalAnalysis:
    ticker: str
    # Price context
    current_price: float = float("nan")
    ma_50:         float = float("nan")
    ma_200:        float = float("nan")
    # Signals (True = bullish, False = bearish, None = unknown)
    above_ma50:         bool | None = None
    above_ma200:        bool | None = None
    golden_cross:       bool | None = None   # 50d MA > 200d MA
    # Momentum
    rsi_14: float = float("nan")   # 0-100
    momentum_1m:  float = float("nan")  # 1-month return
    momentum_3m:  float = float("nan")  # 3-month return
    momentum_6m:  float = float("nan")
    # 52-week range
    high_52w: float = float("nan")
    low_52w:  float = float("nan")
    pct_from_52w_high: float = float("nan")  # negative: -10% = 10% below high
    range_position:    float = float("nan")  # 0-1: 1=at 52w high
    # MACD
    macd_line:   float = float("nan")
    macd_signal: float = float("nan")
    macd_above_signal: bool | None = None
    # Derived
    technical_score:  float = 50.0
    signal: str = "Neutral"  # "Strong" / "Positive" / "Neutral" / "Negative" / "Weak"
    components: dict[str, float] = field(default_factory=dict)


def _rsi(close: pd.Series, period: int = 14) -> float:
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss.replace(0, float("nan"))
    rsi = 100 - 100 / (1 + rs)
    v = rsi.iloc[-1]
    return float(v) if not (math.isnan(v) or np.isnan(v)) else float("nan")


def _momentum(close: pd.Series, trading_days: int) -> float:
    if len(close) < trading_days + 1:
        return float("nan")
    past = float(close.iloc[-(trading_days + 1)])
    curr = float(close.iloc[-1])
    return (curr / past - 1.0) if past > 0 else float("nan")


def _macd(close: pd.Series) -> tuple[float, float]:
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    line   = ema12 - ema26
    signal = line.ewm(span=9, adjust=False).mean()
    return float(line.iloc[-1]), float(signal.iloc[-1])


def score_technical(ticker: str, price_history: pd.DataFrame) -> TechnicalAnalysis:
    """Compute TechnicalAnalysis from a price history DataFrame.

    Args:
        ticker: Ticker symbol.
        price_history: DataFrame with a 'Close' column and DatetimeIndex
                       (e.g. from yf.Ticker().history(period='1y')).

    Returns:
        TechnicalAnalysis dataclass.
    """
    ta = TechnicalAnalysis(ticker=ticker)
    if price_history.empty or "Close" not in price_history.columns:
        return ta

    close = price_history["Close"].dropna()
    if len(close) < 20:
        return ta

    curr = float(close.iloc[-1])
    ta.current_price = curr

    # Moving averages
    if len(close) >= 50:
        ta.ma_50 = float(close.rolling(50).mean().iloc[-1])
        ta.above_ma50 = curr > ta.ma_50
    if len(close) >= 200:
        ta.ma_200 = float(close.rolling(200).mean().iloc[-1])
        ta.above_ma200 = curr > ta.ma_200
    if not math.isnan(ta.ma_50) and not math.isnan(ta.ma_200):
        ta.golden_cross = ta.ma_50 > ta.ma_200

    # RSI
    ta.rsi_14 = _rsi(close, 14)

    # Momentum (approx trading days)
    ta.momentum_1m = _momentum(close, 21)
    ta.momentum_3m = _momentum(close, 63)
    ta.momentum_6m = _momentum(close, 126)

    # 52-week range
    high52 = float(close.rolling(252).max().iloc[-1])
    low52  = float(close.rolling(252).min().iloc[-1])
    ta.high_52w = high52
    ta.low_52w  = low52
    if high52 > 0:
        ta.pct_from_52w_high = (curr / high52) - 1.0
    if (high52 - low52) > 0:
        ta.range_position = (curr - low52) / (high52 - low52)

    # MACD
    if len(close) >= 35:
        ta.macd_line, ta.macd_signal = _macd(close)
        ta.macd_above_signal = ta.macd_line > ta.macd_signal

    # ── Score components (each 0-100) ─────────────────────────────────────────
    components: dict[str, float] = {}

    # 1. Trend (50% weight)
    trend_score = 50.0
    if ta.above_ma200 is not None:
        trend_score += 25.0 if ta.above_ma200 else -25.0
    if ta.above_ma50 is not None:
        trend_score += 15.0 if ta.above_ma50 else -15.0
    if ta.golden_cross is not None:
        trend_score += 10.0 if ta.golden_cross else -10.0
    components["Trend"] = max(0.0, min(100.0, trend_score))

    # 2. RSI (20% weight) — optimal zone 45-65; penalise extreme readings
    rsi = ta.rsi_14
    if not math.isnan(rsi):
        if 45 <= rsi <= 65:
            rsi_score = 70.0 + (rsi - 55) * 1.0   # peak at 60
        elif rsi < 30:
            rsi_score = 55.0  # oversold = opportunity for long-term investor
        elif rsi > 75:
            rsi_score = 30.0  # overbought
        elif rsi < 45:
            rsi_score = 40.0 + (rsi - 30) * 1.0
        else:  # 65-75
            rsi_score = 70.0 - (rsi - 65) * 4.0
        components["RSI"] = max(0.0, min(100.0, rsi_score))

    # 3. 52-week position (15% weight) — sweet spot 0.55-0.80
    rp = ta.range_position
    if not math.isnan(rp):
        if 0.55 <= rp <= 0.80:
            rp_score = 75.0
        elif rp > 0.95:
            rp_score = 55.0   # very extended
        elif rp > 0.80:
            rp_score = 65.0
        elif rp > 0.40:
            rp_score = 55.0
        elif rp > 0.20:
            rp_score = 35.0
        else:
            rp_score = 20.0   # near 52w low
        components["52w Position"] = rp_score

    # 4. MACD (10% weight)
    if ta.macd_above_signal is not None:
        components["MACD"] = 70.0 if ta.macd_above_signal else 35.0

    # 5. 3-month momentum (5% weight)
    m3 = ta.momentum_3m
    if not math.isnan(m3):
        mom_score = 50.0 + m3 * 200  # +20% return → 90 score
        components["Momentum 3M"] = max(0.0, min(100.0, mom_score))

    # ── Weighted composite ─────────────────────────────────────────────────────
    weights = {"Trend": 0.50, "RSI": 0.20, "52w Position": 0.15,
               "MACD": 0.10, "Momentum 3M": 0.05}
    total_w = sum(weights[k] for k in components)
    if total_w > 0:
        ta.technical_score = sum(
            components[k] * weights[k] for k in components
        ) / total_w
    else:
        ta.technical_score = 50.0

    ta.technical_score = max(0.0, min(100.0, ta.technical_score))
    ta.components = components

    # Signal
    s = ta.technical_score
    if s >= 68:
        ta.signal = "Strong"
    elif s >= 57:
        ta.signal = "Positive"
    elif s >= 43:
        ta.signal = "Neutral"
    elif s >= 32:
        ta.signal = "Negative"
    else:
        ta.signal = "Weak"

    return ta
