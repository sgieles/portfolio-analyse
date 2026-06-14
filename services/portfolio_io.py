"""Portfolio JSON save/load.

Schema version 1:
{
  "version": 1,
  "name": "My Portfolio",
  "assets": [{"ticker": "AAPL", "weight": 0.5, "name": "Apple Inc."}],
  "benchmark": "SPY",
  "period": "5y",
  "settings": {
    "risk_free_rate": 0.04,
    "market_expected_return": 0.10,
    "expected_return_method": "historical_avg",
    "monte_carlo_simulations": 1000,
    "monte_carlo_horizon_years": 5
  }
}
"""

from __future__ import annotations

import json
from pathlib import Path

from models.asset import Asset
from models.portfolio import Portfolio
from models.settings import AnalysisSettings, ExpectedReturnMethod
from utils.logging import get_logger

log = get_logger(__name__)

_CURRENT_VERSION = 1


def save_portfolio(
    portfolio: Portfolio,
    settings: AnalysisSettings,
    path: str | Path,
) -> None:
    """Serialise *portfolio* and *settings* to a JSON file at *path*.

    Args:
        portfolio: Portfolio to save.
        settings:  AnalysisSettings to save alongside.
        path:      Destination file path (created or overwritten).
    """
    path = Path(path)
    data = {
        "version": _CURRENT_VERSION,
        "name": portfolio.name,
        "assets": [
            {"ticker": a.ticker, "weight": a.weight, "name": a.name}
            for a in portfolio.assets
        ],
        "benchmark": portfolio.benchmark,
        "period": portfolio.period,
        "settings": {
            "risk_free_rate": settings.risk_free_rate,
            "market_expected_return": settings.market_expected_return,
            "expected_return_method": settings.expected_return_method.value,
            "monte_carlo_simulations": settings.monte_carlo_simulations,
            "monte_carlo_horizon_years": settings.monte_carlo_horizon_years,
        },
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)
    log.info("Portfolio saved to '%s'.", path)


def load_portfolio(path: str | Path) -> tuple[Portfolio, AnalysisSettings]:
    """Load a portfolio + settings from a JSON file.

    Args:
        path: Path to a JSON file previously written by :func:`save_portfolio`.

    Returns:
        Tuple of (Portfolio, AnalysisSettings).

    Raises:
        FileNotFoundError: If *path* does not exist.
        ValueError:        If the file is malformed or from an unsupported version.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Portfolio file not found: '{path}'")

    with path.open("r", encoding="utf-8") as fh:
        data: dict = json.load(fh)

    version = data.get("version", 1)
    if version != _CURRENT_VERSION:
        raise ValueError(
            f"Unsupported portfolio file version {version}. "
            f"Expected version {_CURRENT_VERSION}."
        )

    assets = [
        Asset(
            ticker=a["ticker"],
            weight=float(a["weight"]),
            name=a.get("name", ""),
        )
        for a in data.get("assets", [])
    ]

    portfolio = Portfolio(
        assets=assets,
        benchmark=data.get("benchmark", "SPY"),
        period=data.get("period", "5y"),
        name=data.get("name", "My Portfolio"),
    )

    raw_settings = data.get("settings", {})
    settings = AnalysisSettings(
        risk_free_rate=float(raw_settings.get("risk_free_rate", 0.04)),
        market_expected_return=float(raw_settings.get("market_expected_return", 0.10)),
        expected_return_method=ExpectedReturnMethod(
            raw_settings.get("expected_return_method", "historical_avg")
        ),
        monte_carlo_simulations=int(raw_settings.get("monte_carlo_simulations", 1_000)),
        monte_carlo_horizon_years=int(raw_settings.get("monte_carlo_horizon_years", 5)),
    )

    log.info("Portfolio '%s' loaded from '%s' (%d assets).", portfolio.name, path, len(assets))
    return portfolio, settings
