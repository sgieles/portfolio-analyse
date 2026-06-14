"""Input validators — pure functions, no Qt, no I/O."""

import re

from utils.constants import BENCHMARKS, ANALYSIS_PERIODS

# Yahoo Finance tickers: uppercase letters, digits, dots, hyphens, max 10 chars
_TICKER_RE = re.compile(r"^[A-Z0-9][A-Z0-9.\-]{0,9}$")

WEIGHT_TOLERANCE: float = 1e-6   # how far from 1.0 is still "sums to 1"


def validate_ticker(ticker: str) -> str:
    """Return the normalised ticker or raise ValueError.

    Normalises to uppercase and strips whitespace before checking.
    """
    normalised = ticker.strip().upper()
    if not _TICKER_RE.match(normalised):
        raise ValueError(
            f"Invalid ticker '{ticker}'. Must be 1–10 uppercase alphanumeric characters "
            "optionally containing dots or hyphens (e.g. 'AAPL', 'BRK-B', 'SPY')."
        )
    return normalised


def validate_weights_sum(weights: list[float], tolerance: float = WEIGHT_TOLERANCE) -> None:
    """Raise ValueError unless weights sum to 1.0 within *tolerance*."""
    total = sum(weights)
    if abs(total - 1.0) > tolerance:
        raise ValueError(
            f"Portfolio weights must sum to 1.0, got {total:.6f}. "
            "Use 'Normalize Weights' to fix this."
        )


def validate_weight_value(weight: float) -> None:
    """Raise ValueError if a single weight is outside [0, 1]."""
    if not (0.0 <= weight <= 1.0):
        raise ValueError(f"Weight must be between 0 and 1, got {weight}.")


def validate_benchmark(benchmark: str) -> None:
    """Raise ValueError if benchmark is not in the supported list."""
    if benchmark not in BENCHMARKS:
        raise ValueError(
            f"Benchmark '{benchmark}' is not supported. Choose from {BENCHMARKS}."
        )


def validate_period(period: str) -> None:
    """Raise ValueError if period is not in the supported list."""
    if period not in ANALYSIS_PERIODS:
        raise ValueError(
            f"Period '{period}' is not supported. Choose from {ANALYSIS_PERIODS}."
        )


def validate_portfolio_not_empty(tickers: list[str]) -> None:
    """Raise ValueError if the portfolio has no assets."""
    if not tickers:
        raise ValueError("Portfolio is empty. Add at least one asset before analysing.")
