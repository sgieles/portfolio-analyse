"""Portfolio dataclass — the user's collection of assets and analysis settings."""

from dataclasses import dataclass, field

from models.asset import Asset
from utils.constants import BENCHMARKS, DEFAULT_BENCHMARK, ANALYSIS_PERIODS, DEFAULT_PERIOD


@dataclass
class Portfolio:
    """A named collection of assets with a benchmark and analysis period.

    Attributes:
        assets:     Ordered list of Asset positions.
        benchmark:  Ticker used for beta / CAPM / comparison charts.
        period:     Look-back window for price history ("1y", "3y", "5y", "10y", "max").
        name:       Optional user-defined portfolio name.
    """

    assets: list[Asset] = field(default_factory=list)
    benchmark: str = DEFAULT_BENCHMARK
    period: str = DEFAULT_PERIOD
    name: str = "My Portfolio"

    def __post_init__(self) -> None:
        if self.benchmark not in BENCHMARKS:
            raise ValueError(
                f"Benchmark '{self.benchmark}' not supported. Choose from {BENCHMARKS}."
            )
        if self.period not in ANALYSIS_PERIODS:
            raise ValueError(
                f"Period '{self.period}' not supported. Choose from {ANALYSIS_PERIODS}."
            )

    # ── Convenience helpers ──────────────────────────────────────────────────

    @property
    def tickers(self) -> list[str]:
        return [a.ticker for a in self.assets]

    @property
    def weights(self) -> list[float]:
        return [a.weight for a in self.assets]

    @property
    def total_weight(self) -> float:
        return sum(a.weight for a in self.assets)

    def weight_of(self, ticker: str) -> float:
        for asset in self.assets:
            if asset.ticker == ticker:
                return asset.weight
        raise KeyError(f"Ticker '{ticker}' not in portfolio.")

    def apply_equal_weight(self) -> None:
        """Set every asset to 1/N weight in-place."""
        n = len(self.assets)
        if n == 0:
            return
        w = round(1.0 / n, 10)
        for asset in self.assets:
            asset.weight = w

    def normalize_weights(self) -> None:
        """Scale weights so they sum to exactly 1.0 in-place."""
        total = self.total_weight
        if total == 0:
            raise ValueError("Cannot normalize: all weights are zero.")
        for asset in self.assets:
            asset.weight = asset.weight / total
