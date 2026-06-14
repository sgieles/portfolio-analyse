"""Tests for services.data_service and services.cache — no live network calls."""

from __future__ import annotations

import pickle
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from services.cache import PriceCache
from services.data_service import DataService, FetchResult
from services.exceptions import (
    DataError,
    InsufficientDataError,
    NetworkError,
    TickerNotFoundError,
)


# ── Helpers ──────────────────────────────────────────────────────────────────

def _make_series(ticker: str, n: int = 300, start: str = "2022-01-01") -> pd.Series:
    """Synthetic daily price series (random walk starting at 100)."""
    import numpy as np
    rng = pd.date_range(start, periods=n, freq="B")
    prices = 100 * (1 + pd.Series(
        [0.001] * n, index=rng
    ).cumsum())
    prices.name = ticker
    return prices


def _make_raw_df(ticker: str, n: int = 300) -> pd.DataFrame:
    """Fake yfinance download() return value (flat columns, auto_adjust=True)."""
    s = _make_series(ticker, n)
    return pd.DataFrame({"Close": s.values, "Open": s.values}, index=s.index)


# ── PriceCache ────────────────────────────────────────────────────────────────

class TestPriceCache:
    def test_miss_on_empty_cache(self, tmp_path: Path):
        cache = PriceCache(tmp_path)
        assert cache.get("AAPL", "5y") is None

    def test_put_and_get(self, tmp_path: Path):
        cache = PriceCache(tmp_path)
        s = _make_series("AAPL")
        cache.put("AAPL", "5y", s)
        retrieved = cache.get("AAPL", "5y")
        assert retrieved is not None
        pd.testing.assert_series_equal(s, retrieved)

    def test_get_returns_none_after_clear(self, tmp_path: Path):
        cache = PriceCache(tmp_path)
        cache.put("SPY", "1y", _make_series("SPY"))
        cache.clear()
        assert cache.get("SPY", "1y") is None

    def test_expired_entry_returns_none(self, tmp_path: Path):
        cache = PriceCache(tmp_path)
        s = _make_series("MSFT")
        cache.put("MSFT", "3y", s)
        # Back-date the file's mtime to force expiry
        cache_path = cache._path("MSFT", "3y")
        past = time.time() - (25 * 3600)  # 25 hours ago
        import os
        os.utime(cache_path, (past, past))
        assert cache.get("MSFT", "3y") is None

    def test_invalidate_removes_entry(self, tmp_path: Path):
        cache = PriceCache(tmp_path)
        cache.put("VOO", "5y", _make_series("VOO"))
        cache.invalidate("VOO", "5y")
        assert cache.get("VOO", "5y") is None

    def test_corrupt_file_returns_none(self, tmp_path: Path):
        cache = PriceCache(tmp_path)
        path = cache._path("BAD", "1y")
        path.write_bytes(b"not-a-pickle")
        assert cache.get("BAD", "1y") is None

    def test_ticker_with_special_chars(self, tmp_path: Path):
        cache = PriceCache(tmp_path)
        s = _make_series("BRK-B")
        cache.put("BRK-B", "5y", s)
        assert cache.get("BRK-B", "5y") is not None


# ── DataService ───────────────────────────────────────────────────────────────

class TestDataService:
    """All yfinance.download calls are mocked — no network required."""

    def _service(self, tmp_path: Path) -> DataService:
        return DataService(cache=PriceCache(tmp_path))

    # ── Happy path ────────────────────────────────────────────────────────────

    def test_fetch_prices_single_ticker(self, tmp_path: Path):
        svc = self._service(tmp_path)
        with patch("services.data_service.DataService._download") as mock_dl:
            mock_dl.return_value = _make_series("AAPL", 300)
            result = svc.fetch_prices(["AAPL"], "5y")

        assert isinstance(result, FetchResult)
        assert "AAPL" in result.prices.columns
        assert len(result.prices) == 300
        assert result.failed_tickers == []

    def test_fetch_prices_multiple_tickers_aligned(self, tmp_path: Path):
        svc = self._service(tmp_path)
        # AAPL has 300 rows, MSFT has 280 — aligned should be 280
        s_aapl = _make_series("AAPL", 300, start="2022-01-01")
        s_msft = _make_series("MSFT", 280, start="2022-02-01")  # starts later

        def fake_download(ticker, period):
            return s_aapl if ticker == "AAPL" else s_msft

        with patch("services.data_service.DataService._download", side_effect=fake_download):
            result = svc.fetch_prices(["AAPL", "MSFT"], "5y")

        # Only overlapping dates survive
        assert len(result.prices) <= min(len(s_aapl), len(s_msft))
        assert set(result.prices.columns) == {"AAPL", "MSFT"}

    def test_cache_hit_skips_download(self, tmp_path: Path):
        cache = PriceCache(tmp_path)
        s = _make_series("SPY", 300)
        cache.put("SPY", "5y", s)
        svc = DataService(cache=cache)

        with patch("services.data_service.DataService._download") as mock_dl:
            result = svc.fetch_prices(["SPY"], "5y")
            mock_dl.assert_not_called()

        assert "SPY" in result.prices.columns

    # ── Bad ticker ────────────────────────────────────────────────────────────

    def test_bad_ticker_goes_to_failed_list(self, tmp_path: Path):
        svc = self._service(tmp_path)
        s_good = _make_series("AAPL", 300)

        def fake_download(ticker, period):
            if ticker == "BADTICKER":
                raise TickerNotFoundError("BADTICKER")
            return s_good

        with patch("services.data_service.DataService._download", side_effect=fake_download):
            result = svc.fetch_prices(["AAPL", "BADTICKER"], "5y")

        assert "BADTICKER" in result.failed_tickers
        assert "AAPL" in result.prices.columns
        assert len(result.warnings) == 1

    def test_all_tickers_fail_raises_data_error(self, tmp_path: Path):
        svc = self._service(tmp_path)

        def fake_download(ticker, period):
            raise TickerNotFoundError(ticker)

        with patch("services.data_service.DataService._download", side_effect=fake_download):
            with pytest.raises(DataError, match="No price data"):
                svc.fetch_prices(["BAD1", "BAD2"], "5y")

    # ── Insufficient data ─────────────────────────────────────────────────────

    def test_insufficient_data_goes_to_failed_list(self, tmp_path: Path):
        svc = self._service(tmp_path)
        s_short = _make_series("TINY", n=10)   # way below minimum
        s_good  = _make_series("AAPL", n=300)

        def fake_download(ticker, period):
            if ticker == "TINY":
                raise InsufficientDataError("TINY", available=10, required=1000)
            return s_good

        with patch("services.data_service.DataService._download", side_effect=fake_download):
            result = svc.fetch_prices(["AAPL", "TINY"], "5y")

        assert "TINY" in result.failed_tickers
        assert "AAPL" in result.prices.columns

    # ── Network errors ────────────────────────────────────────────────────────

    def test_network_error_propagates(self, tmp_path: Path):
        svc = self._service(tmp_path)

        with patch("services.data_service.DataService._download_with_retry",
                   side_effect=NetworkError("connection refused")):
            with pytest.raises(NetworkError):
                svc.fetch_prices(["AAPL"], "5y")

    # ── fetch_single ──────────────────────────────────────────────────────────

    def test_fetch_single_returns_series(self, tmp_path: Path):
        svc = self._service(tmp_path)
        s = _make_series("SPY", 300)
        with patch("services.data_service.DataService._download", return_value=s):
            result = svc.fetch_single("SPY", "5y")
        assert isinstance(result, pd.Series)
        assert result.name == "SPY"

    # ── _download (static) ────────────────────────────────────────────────────

    def test_download_extracts_close_flat_columns(self):
        """_download should handle flat column structure (auto_adjust=True, single ticker)."""
        raw_df = _make_raw_df("AAPL", 1100)   # >= 1 000-day minimum for 5y
        with patch("yfinance.download", return_value=raw_df):
            series = DataService._download("AAPL", "5y")
        assert series.name == "AAPL"
        assert len(series) == 1100

    def test_download_raises_on_empty_dataframe(self):
        with patch("yfinance.download", return_value=pd.DataFrame()):
            with pytest.raises(TickerNotFoundError, match="INVALID"):
                DataService._download("INVALID", "5y")

    def test_download_raises_insufficient_for_short_series(self):
        """Only 5 rows — well below the 1 000-day minimum for 5y."""
        raw_df = _make_raw_df("AAPL", 5)
        with patch("yfinance.download", return_value=raw_df):
            with pytest.raises(InsufficientDataError):
                DataService._download("AAPL", "5y")
