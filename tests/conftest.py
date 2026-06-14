"""Shared pytest fixtures — synthetic price data, no network."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest


def _bday_index(n: int, start: str = "2020-01-02") -> pd.DatetimeIndex:
    return pd.bdate_range(start=start, periods=n)


@pytest.fixture
def flat_prices() -> pd.Series:
    """253 days of constant prices (no returns)."""
    idx = _bday_index(253)
    return pd.Series(100.0, index=idx, name="FLAT")


@pytest.fixture
def linear_prices() -> pd.Series:
    """253 business-day price series rising 0.1 per day (deterministic)."""
    idx = _bday_index(253)
    return pd.Series(100.0 + np.arange(253) * 0.1, index=idx, name="LINEAR")


@pytest.fixture
def compound_prices() -> pd.Series:
    """253 business-day price series with a constant 0.1 % daily return.

    This makes mathematical verification straightforward:
      CAGR = 1.001^252 - 1 ≈ 28.1 %
      daily return = 0.001 exactly
    """
    idx = _bday_index(253)
    prices = 100.0 * (1.001 ** np.arange(253))
    return pd.Series(prices, index=idx, name="COMPOUND")


@pytest.fixture
def two_asset_prices() -> pd.DataFrame:
    """Two uncorrelated assets — A trends up, B stays flat.

    A: constant 0.1 % daily return
    B: constant price (0 % return)
    """
    idx = _bday_index(253)
    a = pd.Series(100.0 * (1.001 ** np.arange(253)), index=idx, name="A")
    b = pd.Series(100.0, index=idx, name="B")
    return pd.DataFrame({"A": a, "B": b})


@pytest.fixture
def volatile_returns() -> pd.Series:
    """500 random daily returns with a known seed — repeatable."""
    rng = np.random.default_rng(42)
    values = rng.normal(loc=0.0005, scale=0.01, size=500)
    idx = _bday_index(500)
    return pd.Series(values, index=idx, name="VOLATILE")


@pytest.fixture
def benchmark_returns(volatile_returns: pd.Series) -> pd.Series:
    """Benchmark returns: volatile_returns scaled by 0.8 + small noise."""
    rng = np.random.default_rng(99)
    noise = rng.normal(0, 0.002, size=len(volatile_returns))
    bench = volatile_returns * 0.8 + noise
    bench.name = "BENCH"
    bench.index = volatile_returns.index
    return bench


@pytest.fixture
def multi_asset_returns() -> pd.DataFrame:
    """Three-asset daily return DataFrame — 500 rows, repeatable."""
    rng = np.random.default_rng(7)
    n = 500
    idx = _bday_index(n)
    data = {
        "X": rng.normal(0.0008, 0.012, n),
        "Y": rng.normal(0.0003, 0.008, n),
        "Z": rng.normal(0.0005, 0.015, n),
    }
    return pd.DataFrame(data, index=idx)


@pytest.fixture
def equal_weights_3() -> dict[str, float]:
    return {"X": 1 / 3, "Y": 1 / 3, "Z": 1 / 3}
