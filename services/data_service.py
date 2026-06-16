"""Data service — fetches and aligns adjusted-close price history via yfinance.

Responsibilities:
  - Check cache first; fall through to yfinance on miss.
  - Retry transient network failures with exponential back-off.
  - Map yfinance errors to typed DataError subclasses.
  - Align multi-ticker data on a common date range (inner join, drop NaN rows).
  - Never crash the whole analysis because of one bad ticker.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

import pandas as pd
import requests

from services.cache import PriceCache
from services.exceptions import (
    DataError,
    InsufficientDataError,
    NetworkError,
    NoInternetError,
    TickerNotFoundError,
)
from utils.constants import TRADING_DAYS_PER_YEAR
from utils.logging import get_logger

log = get_logger(__name__)

# Minimum trading days required per period (below this → InsufficientDataError)
_MIN_DAYS: dict[str, int] = {
    "1y": 200,
    "3y": 580,
    "5y": 1_000,
    "10y": 2_000,
    "max": 20,
}
_RETRY_ATTEMPTS = 3
_RETRY_BASE_DELAY = 1.0  # seconds; doubles each attempt


@dataclass
class FetchResult:
    """Return value of :meth:`DataService.fetch_prices`."""

    prices: pd.DataFrame                  # aligned adj-close, columns = tickers
    failed_tickers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class DataService:
    """Fetch and cache adjusted-close price history for a list of tickers."""

    def __init__(self, cache: PriceCache | None = None) -> None:
        self._cache = cache or PriceCache()

    # ── Public API ───────────────────────────────────────────────────────────

    def fetch_prices(self, tickers: list[str], period: str) -> FetchResult:
        """Return a clean, aligned price frame for *tickers* over *period*.

        Tickers that cannot be fetched are collected in ``FetchResult.failed_tickers``
        and do **not** raise; network errors that affect all tickers do raise.

        Args:
            tickers: List of Yahoo Finance ticker symbols.
            period:  One of "1y", "3y", "5y", "10y", "max".

        Returns:
            FetchResult with aligned DataFrame (rows = trading days).
        """
        series_list: list[pd.Series] = []
        failed: list[str] = []
        warnings: list[str] = []

        for ticker in tickers:
            try:
                s = self._fetch_one(ticker, period)
                series_list.append(s)
                log.info("Loaded %d days for %s (%s)", len(s), ticker, period)
            except TickerNotFoundError as exc:
                log.warning(str(exc))
                failed.append(ticker)
                warnings.append(str(exc))
            except InsufficientDataError as exc:
                log.warning(str(exc))
                failed.append(ticker)
                warnings.append(str(exc))
            except NetworkError:
                raise  # network down → propagate immediately

        if not series_list:
            raise DataError(
                "No price data could be fetched for any ticker in the portfolio."
            )

        prices = pd.concat(series_list, axis=1)
        # Inner join: keep only trading days common to all tickers
        prices = prices.dropna()

        if prices.empty:
            raise DataError(
                "After aligning start dates there are no overlapping trading days. "
                "Try a shorter period or check the tickers."
            )

        log.info(
            "Aligned price frame: %d rows × %d tickers (%s to %s)",
            len(prices),
            len(prices.columns),
            prices.index[0].date(),
            prices.index[-1].date(),
        )
        return FetchResult(prices=prices, failed_tickers=failed, warnings=warnings)

    def fetch_single(self, ticker: str, period: str) -> pd.Series:
        """Fetch one ticker (used for benchmark series). Raises on failure."""
        return self._fetch_one(ticker, period)

    # ── Internals ────────────────────────────────────────────────────────────

    def _fetch_one(self, ticker: str, period: str) -> pd.Series:
        """Return adjusted-close series for one ticker, from cache or network."""
        cached = self._cache.get(ticker, period)
        if cached is not None:
            return cached

        series = self._download_with_retry(ticker, period)
        self._cache.put(ticker, period, series)
        return series

    def _download_with_retry(self, ticker: str, period: str) -> pd.Series:
        """Call yfinance download with exponential back-off on transient errors."""
        last_exc: Exception | None = None
        for attempt in range(_RETRY_ATTEMPTS):
            try:
                return self._download(ticker, period)
            except (TickerNotFoundError, InsufficientDataError):
                raise  # permanent errors — do not retry
            except (requests.exceptions.ConnectionError, OSError) as exc:
                last_exc = exc
                if attempt == 0:
                    # Check if we simply have no internet at all
                    try:
                        requests.get("https://finance.yahoo.com", timeout=3)
                    except (requests.exceptions.ConnectionError, OSError):
                        raise NoInternetError() from exc
                delay = _RETRY_BASE_DELAY * (2 ** attempt)
                log.warning(
                    "Network error for %s (attempt %d/%d), retrying in %.1fs: %s",
                    ticker, attempt + 1, _RETRY_ATTEMPTS, delay, exc,
                )
                time.sleep(delay)
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                delay = _RETRY_BASE_DELAY * (2 ** attempt)
                log.warning(
                    "Unexpected error for %s (attempt %d/%d), retrying in %.1fs: %s",
                    ticker, attempt + 1, _RETRY_ATTEMPTS, delay, exc,
                )
                time.sleep(delay)

        raise NetworkError(
            f"Failed to fetch '{ticker}' after {_RETRY_ATTEMPTS} attempts: {last_exc}"
        )

    @staticmethod
    def _download(ticker: str, period: str) -> pd.Series:
        """One yfinance download call — returns adj-close Series or raises."""
        import yfinance as yf  # deferred import so tests can mock easily

        raw = yf.download(
            ticker,
            period=period,
            auto_adjust=True,
            progress=False,
            threads=False,
        )

        if raw is None or raw.empty:
            raise TickerNotFoundError(ticker)

        # Extract Close column (= adjusted when auto_adjust=True)
        if isinstance(raw.columns, pd.MultiIndex):
            # yfinance >= 0.2.18 multi-ticker download returns MultiIndex even for one ticker
            close_col = ("Close", ticker)
            if close_col not in raw.columns:
                # Try the first available Close column
                close_cols = [c for c in raw.columns if c[0] == "Close"]
                if not close_cols:
                    raise TickerNotFoundError(ticker)
                close_col = close_cols[0]
            series = raw[close_col].dropna()
        else:
            if "Close" not in raw.columns:
                raise TickerNotFoundError(ticker)
            series = raw["Close"].dropna()

        series.name = ticker

        # Normalise index to timezone-naive dates so all series can be
        # concat'd / reindex'd together regardless of exchange timezone.
        if hasattr(series.index, "tz") and series.index.tz is not None:
            series.index = series.index.tz_convert("UTC").tz_localize(None)
        series.index = series.index.normalize()  # strip intraday time component

        # Check minimum data
        min_days = _MIN_DAYS.get(period, 20)
        if len(series) < min_days:
            raise InsufficientDataError(
                ticker=ticker,
                available=len(series),
                required=min_days,
            )

        return series
