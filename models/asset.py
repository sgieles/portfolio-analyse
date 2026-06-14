"""Asset dataclass — one holding in a portfolio."""

from dataclasses import dataclass, field


@dataclass
class Asset:
    """A single stock or ETF position.

    Attributes:
        ticker:  Yahoo Finance ticker symbol (e.g. "AAPL", "SPY").
        weight:  Portfolio weight as a fraction in [0, 1].
        name:    Human-readable name; populated by the data service after fetching.
    """

    ticker: str
    weight: float
    name: str = ""

    def __post_init__(self) -> None:
        self.ticker = self.ticker.strip().upper()
        if not (0.0 <= self.weight <= 1.0):
            raise ValueError(f"Weight must be in [0, 1], got {self.weight} for '{self.ticker}'")
