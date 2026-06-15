"""Dataclasses for company fundamental data."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class AnnualFundamentals:
    """Key financial metrics for one fiscal year."""

    ticker: str
    cik: str
    fiscal_year: int                    # e.g. 2023

    # Income statement
    revenue: float = float("nan")       # USD
    gross_profit: float = float("nan")
    operating_income: float = float("nan")
    net_income: float = float("nan")
    eps_diluted: float = float("nan")
    interest_expense: float = float("nan")  # Phase 18: interest coverage

    # Margins (0–1)
    gross_margin: float = float("nan")
    operating_margin: float = float("nan")
    net_margin: float = float("nan")

    # Balance sheet
    total_assets: float = float("nan")
    total_equity: float = float("nan")
    total_debt: float = float("nan")
    cash: float = float("nan")
    current_assets: float = float("nan")        # Phase 18: current ratio
    current_liabilities: float = float("nan")   # Phase 18: current ratio

    # Cash flow
    operating_cash_flow: float = float("nan")
    free_cash_flow: float = float("nan")
    capex: float = float("nan")

    # Per-share / ratios
    shares_outstanding: float = float("nan")
    book_value_per_share: float = float("nan")
    return_on_equity: float = float("nan")   # net_income / equity
    return_on_assets: float = float("nan")   # net_income / assets
    debt_to_equity: float = float("nan")

    # Source metadata
    source: str = "edgar"               # "edgar" | "yfinance"
    last_refreshed: str = ""            # ISO-8601 timestamp


@dataclass
class QuarterlyFundamentals:
    """Key financial metrics for one fiscal quarter."""

    ticker: str
    fiscal_year: int
    fiscal_quarter: int             # 1–4
    period_end: str                 # ISO date, e.g. "2024-03-31"

    revenue: float = float("nan")
    gross_profit: float = float("nan")
    operating_income: float = float("nan")
    net_income: float = float("nan")
    eps_diluted: float = float("nan")
    gross_margin: float = float("nan")
    operating_margin: float = float("nan")
    net_margin: float = float("nan")
    operating_cash_flow: float = float("nan")
    free_cash_flow: float = float("nan")

    source: str = "yfinance"


@dataclass
class CompanyProfile:
    """Static descriptive data for one company."""

    ticker: str
    cik: str = ""
    name: str = ""
    sector: str = ""
    industry: str = ""
    country: str = ""
    exchange: str = ""
    currency: str = ""
    market_cap: float = float("nan")
    employees: int = 0
    description: str = ""
    website: str = ""
    last_refreshed: str = ""


@dataclass
class WatchlistEntry:
    """One asset on a user watchlist."""

    ticker: str
    note: str = ""
    added_at: str = ""                  # ISO-8601 date
    score: float = float("nan")         # populated by screener in Phase 17


@dataclass
class Watchlist:
    """A named collection of tickers."""

    name: str
    entries: list[WatchlistEntry] = field(default_factory=list)
    created_at: str = ""

    @property
    def tickers(self) -> list[str]:
        return [e.ticker for e in self.entries]

    def add(self, ticker: str, note: str = "") -> None:
        from datetime import date
        if ticker not in self.tickers:
            self.entries.append(WatchlistEntry(
                ticker=ticker, note=note, added_at=date.today().isoformat()
            ))

    def remove(self, ticker: str) -> None:
        self.entries = [e for e in self.entries if e.ticker != ticker]
