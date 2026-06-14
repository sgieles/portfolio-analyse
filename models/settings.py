"""AnalysisSettings dataclass — configurable parameters for analytics."""

from dataclasses import dataclass
from enum import Enum

from utils.constants import (
    DEFAULT_RISK_FREE_RATE,
    DEFAULT_MARKET_EXPECTED_RETURN,
    MONTE_CARLO_DEFAULT_SIMULATIONS,
    MONTE_CARLO_DEFAULT_HORIZON_YEARS,
)


class ExpectedReturnMethod(str, Enum):
    """Which return estimate to use as input for optimization."""
    HISTORICAL_AVG  = "historical_avg"   # daily mean × 252 (default)
    CAGR            = "cagr"             # compound annual growth rate
    CAPM            = "capm"             # risk-free + beta × (market − risk-free)


@dataclass
class AnalysisSettings:
    """User-configurable analysis parameters.

    Attributes:
        risk_free_rate:           Annualized risk-free rate (decimal).
        market_expected_return:   Annualized market return assumption for CAPM.
        expected_return_method:   Which return estimate drives optimization.
        monte_carlo_simulations:  Number of MC paths.
        monte_carlo_horizon_years: Simulation horizon in years.
    """

    risk_free_rate: float = DEFAULT_RISK_FREE_RATE
    market_expected_return: float = DEFAULT_MARKET_EXPECTED_RETURN
    expected_return_method: ExpectedReturnMethod = ExpectedReturnMethod.HISTORICAL_AVG
    monte_carlo_simulations: int = MONTE_CARLO_DEFAULT_SIMULATIONS
    monte_carlo_horizon_years: int = MONTE_CARLO_DEFAULT_HORIZON_YEARS

    def __post_init__(self) -> None:
        if not (0.0 <= self.risk_free_rate <= 1.0):
            raise ValueError(f"risk_free_rate must be in [0, 1], got {self.risk_free_rate}")
        if not (0.0 <= self.market_expected_return <= 1.0):
            raise ValueError(
                f"market_expected_return must be in [0, 1], got {self.market_expected_return}"
            )
        if self.monte_carlo_simulations < 1:
            raise ValueError("monte_carlo_simulations must be >= 1")
        if self.monte_carlo_horizon_years < 1:
            raise ValueError("monte_carlo_horizon_years must be >= 1")
        # Accept plain string values from JSON deserialization
        if isinstance(self.expected_return_method, str):
            self.expected_return_method = ExpectedReturnMethod(self.expected_return_method)
