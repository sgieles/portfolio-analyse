"""Typed exceptions for the data layer."""


class DataError(Exception):
    """Base class for all data-layer errors."""


class TickerNotFoundError(DataError):
    """Yahoo Finance returned no data for this ticker."""

    def __init__(self, ticker: str) -> None:
        self.ticker = ticker
        super().__init__(
            f"Ticker '{ticker}' was not found on Yahoo Finance. "
            "Check the symbol and try again."
        )


class InsufficientDataError(DataError):
    """Not enough price history for the requested analysis period."""

    def __init__(self, ticker: str, available: int, required: int) -> None:
        self.ticker = ticker
        self.available = available
        self.required = required
        super().__init__(
            f"Insufficient data for '{ticker}': "
            f"{available} trading days available, {required} required."
        )


class NetworkError(DataError):
    """A network request failed after all retries."""


class NoInternetError(NetworkError):
    """No internet connection could be established."""

    def __init__(self) -> None:
        super().__init__(
            "No internet connection. Check your network and try again."
        )


class CacheError(DataError):
    """Disk cache read/write failure (non-fatal — fall through to network)."""
