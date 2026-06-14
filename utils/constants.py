"""Application-wide constants."""

TRADING_DAYS_PER_YEAR: int = 252

# Risk-free rate (annualized, configurable in UI)
DEFAULT_RISK_FREE_RATE: float = 0.04  # 4 %

# Market expected return assumption for CAPM
DEFAULT_MARKET_EXPECTED_RETURN: float = 0.10  # 10 %

# Benchmarks available for comparison
BENCHMARKS: list[str] = ["SPY", "VTI", "ACWI"]
DEFAULT_BENCHMARK: str = "SPY"

# Analysis periods shown in the UI
ANALYSIS_PERIODS: list[str] = ["1y", "3y", "5y", "10y", "max"]
DEFAULT_PERIOD: str = "5y"

# Portfolio growth start value (EUR)
GROWTH_START_VALUE: float = 10_000.0

# Monte Carlo defaults
MONTE_CARLO_DEFAULT_SIMULATIONS: int = 1_000
MONTE_CARLO_DEFAULT_HORIZON_YEARS: int = 5

# VaR confidence levels
VAR_CONFIDENCE_LEVELS: list[float] = [0.95, 0.99]

# Cache settings
CACHE_DIR: str = ".cache"
CACHE_EXPIRY_HOURS: int = 24
