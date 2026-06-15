"""Parse SEC EDGAR companyfacts into AnnualFundamentals rows.

Falls back to yfinance for tickers not in EDGAR (EU stocks, ETFs).
"""

from __future__ import annotations

import logging
import math
from datetime import datetime, timezone
from typing import Any

from research.models.fundamentals import AnnualFundamentals, CompanyProfile, QuarterlyFundamentals
from research.cache import research_cache as _cache
from research.data import edgar_client

_log = logging.getLogger(__name__)

# us-gaap concept synonyms we accept (first match wins per company)
_REVENUE_TAGS   = ["Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax",
                   "SalesRevenueNet", "RevenueFromContractWithCustomerIncludingAssessedTax"]
_NETINCOME_TAGS = ["NetIncomeLoss", "NetIncome", "ProfitLoss"]
_EPS_TAGS       = ["EarningsPerShareDiluted", "EarningsPerShareBasic"]
_ASSETS_TAGS    = ["Assets"]
_EQUITY_TAGS    = ["StockholdersEquity", "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest"]
_DEBT_TAGS      = ["LongTermDebtAndCapitalLeaseObligations", "LongTermDebt",
                   "DebtAndCapitalLeaseObligations", "LongTermDebtNoncurrent"]
_CASH_TAGS      = ["CashAndCashEquivalentsAtCarryingValue", "CashCashEquivalentsAndShortTermInvestments"]
_OPCF_TAGS      = ["NetCashProvidedByUsedInOperatingActivities"]
_CAPEX_TAGS     = ["PaymentsToAcquirePropertyPlantAndEquipment",
                   "PaymentsForCapitalImprovements"]
_SHARES_TAGS    = ["CommonStockSharesOutstanding", "EntityCommonStockSharesOutstanding"]
_GROSS_TAGS     = ["GrossProfit"]
_OP_INC_TAGS    = ["OperatingIncomeLoss", "IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest"]
_BV_TAGS        = ["BookValuePerShareBasic", "CommonStockParOrStatedValuePerShare"]
_INT_EXP_TAGS   = ["InterestExpense", "InterestAndDebtExpense", "InterestExpenseBorrowings",
                   "InterestPaidNet"]
_CUR_ASSETS_TAGS = ["AssetsCurrent"]
_CUR_LIAB_TAGS   = ["LiabilitiesCurrent"]


def _extract_annual(facts: dict, tags: list[str]) -> dict[int, float]:
    """Return {fiscal_year: value} for the first matching tag with annual (FY) data."""
    us_gaap = facts.get("facts", {}).get("us-gaap", {})
    for tag in tags:
        concept = us_gaap.get(tag)
        if not concept:
            continue
        units = concept.get("units", {})
        # Prefer USD; fall back to first available unit
        data = units.get("USD") or units.get("shares") or next(iter(units.values()), [])
        by_year: dict[int, float] = {}
        for item in data:
            if item.get("form") not in ("10-K", "20-F", "40-F"):
                continue
            fy = item.get("fy")
            val = item.get("val")
            if fy and val is not None:
                by_year[int(fy)] = float(val)
        if by_year:
            return by_year
    return {}


def fetch_fundamentals(ticker: str, n_years: int = 5) -> list[AnnualFundamentals]:
    """Return up to n_years of annual fundamentals for ticker.

    Order: newest year first.
    Tries EDGAR first; falls back to yfinance for non-US or missing tickers.
    """
    # Check disk cache first
    cached_rows = _cache.get_fundamentals(ticker)
    if cached_rows:
        return [AnnualFundamentals(**r) for r in cached_rows]

    result = _fetch_from_edgar(ticker, n_years)
    if not result:
        result = _fetch_from_yfinance(ticker, n_years)

    if result:
        _cache.save_fundamentals(ticker, [_fund_to_dict(f) for f in result])
    return result


def _fetch_from_edgar(ticker: str, n_years: int) -> list[AnnualFundamentals]:
    cik = edgar_client.ticker_to_cik(ticker)
    if not cik:
        return []
    facts = edgar_client.get_company_facts(cik)
    if not facts:
        return []

    revenue   = _extract_annual(facts, _REVENUE_TAGS)
    net_inc   = _extract_annual(facts, _NETINCOME_TAGS)
    eps       = _extract_annual(facts, _EPS_TAGS)
    assets    = _extract_annual(facts, _ASSETS_TAGS)
    equity    = _extract_annual(facts, _EQUITY_TAGS)
    debt      = _extract_annual(facts, _DEBT_TAGS)
    cash      = _extract_annual(facts, _CASH_TAGS)
    opcf      = _extract_annual(facts, _OPCF_TAGS)
    capex     = _extract_annual(facts, _CAPEX_TAGS)
    shares    = _extract_annual(facts, _SHARES_TAGS)
    gross     = _extract_annual(facts, _GROSS_TAGS)
    op_inc    = _extract_annual(facts, _OP_INC_TAGS)
    int_exp   = _extract_annual(facts, _INT_EXP_TAGS)
    cur_ast   = _extract_annual(facts, _CUR_ASSETS_TAGS)
    cur_lia   = _extract_annual(facts, _CUR_LIAB_TAGS)

    years = sorted(
        set(revenue) | set(net_inc) | set(assets),
        reverse=True,
    )[:n_years]

    result = []
    for fy in years:
        rev   = revenue.get(fy, float("nan"))
        ni    = net_inc.get(fy, float("nan"))
        gp    = gross.get(fy, float("nan"))
        oi    = op_inc.get(fy, float("nan"))
        eq    = equity.get(fy, float("nan"))
        ast   = assets.get(fy, float("nan"))
        cp    = capex.get(fy, float("nan"))
        cf    = opcf.get(fy, float("nan"))

        gm  = (gp / rev) if not (math.isnan(gp) or math.isnan(rev) or rev == 0) else float("nan")
        om  = (oi / rev) if not (math.isnan(oi) or math.isnan(rev) or rev == 0) else float("nan")
        nm  = (ni / rev) if not (math.isnan(ni) or math.isnan(rev) or rev == 0) else float("nan")
        roe = (ni / eq)  if not (math.isnan(ni) or math.isnan(eq) or eq == 0)   else float("nan")
        roa = (ni / ast) if not (math.isnan(ni) or math.isnan(ast) or ast == 0)  else float("nan")
        dt  = debt.get(fy, float("nan"))
        dte = (dt / eq)  if not (math.isnan(dt) or math.isnan(eq) or eq == 0)   else float("nan")
        fcf = (cf - abs(cp)) if not (math.isnan(cf) or math.isnan(cp)) else float("nan")

        result.append(AnnualFundamentals(
            ticker=ticker, cik=cik, fiscal_year=fy,
            revenue=rev, gross_profit=gp, operating_income=oi, net_income=ni,
            eps_diluted=eps.get(fy, float("nan")),
            interest_expense=int_exp.get(fy, float("nan")),
            gross_margin=gm, operating_margin=om, net_margin=nm,
            total_assets=ast, total_equity=eq,
            total_debt=dt, cash=cash.get(fy, float("nan")),
            current_assets=cur_ast.get(fy, float("nan")),
            current_liabilities=cur_lia.get(fy, float("nan")),
            operating_cash_flow=cf, free_cash_flow=fcf,
            capex=cp, shares_outstanding=shares.get(fy, float("nan")),
            return_on_equity=roe, return_on_assets=roa, debt_to_equity=dte,
            source="edgar",
            last_refreshed=datetime.now(timezone.utc).isoformat(),
        ))
    return result


def _fetch_from_yfinance(ticker: str, n_years: int) -> list[AnnualFundamentals]:
    """Fallback for EU/non-EDGAR tickers using yfinance financials DataFrames."""
    try:
        import yfinance as yf
        tk = yf.Ticker(ticker)
        fin = tk.financials          # income statement (annual, columns = dates)
        bs  = tk.balance_sheet
        cf  = tk.cashflow

        if fin is None or fin.empty:
            return []

        result = []
        for col in list(fin.columns)[:n_years]:
            fy = col.year

            def _get(df, *keys) -> float:
                for k in keys:
                    try:
                        v = df.loc[k, col]
                        if v is not None and not math.isnan(float(v)):
                            return float(v)
                    except (KeyError, TypeError, ValueError):
                        pass
                return float("nan")

            rev  = _get(fin, "Total Revenue")
            ni   = _get(fin, "Net Income")
            gp   = _get(fin, "Gross Profit")
            oi   = _get(fin, "Operating Income")
            ast  = _get(bs,  "Total Assets")
            eq   = _get(bs,  "Total Stockholder Equity", "Stockholders Equity",
                             "Stockholders' Equity")
            dt   = _get(bs,  "Long Term Debt", "Long-Term Debt")
            csh  = _get(bs,  "Cash", "Cash And Cash Equivalents")
            ocf  = _get(cf,  "Total Cash From Operating Activities",
                             "Operating Cash Flow")
            cap  = _get(cf,  "Capital Expenditures")
            inx  = _get(fin, "Interest Expense", "Interest Expense Non Operating")
            cast = _get(bs,  "Total Current Assets", "Current Assets")
            clia = _get(bs,  "Total Current Liabilities", "Current Liabilities")

            gm  = (gp / rev) if rev else float("nan")
            om  = (oi / rev) if rev else float("nan")
            nm  = (ni / rev) if rev else float("nan")
            roe = (ni / eq)  if eq  else float("nan")
            roa = (ni / ast) if ast else float("nan")
            dte = (dt / eq)  if eq  else float("nan")
            fcf = (ocf + cap) if not (math.isnan(ocf) or math.isnan(cap)) else float("nan")

            result.append(AnnualFundamentals(
                ticker=ticker, cik="", fiscal_year=fy,
                revenue=rev, gross_profit=gp, operating_income=oi, net_income=ni,
                interest_expense=abs(inx) if not math.isnan(inx) else float("nan"),
                gross_margin=gm, operating_margin=om, net_margin=nm,
                total_assets=ast, total_equity=eq, total_debt=dt, cash=csh,
                current_assets=cast, current_liabilities=clia,
                operating_cash_flow=ocf, free_cash_flow=fcf, capex=cap,
                return_on_equity=roe, return_on_assets=roa, debt_to_equity=dte,
                source="yfinance",
                last_refreshed=datetime.now(timezone.utc).isoformat(),
            ))
        return result
    except Exception as exc:
        _log.warning("yfinance fundamentals failed for %s: %s", ticker, exc)
        return []


def fetch_profile(ticker: str) -> CompanyProfile:
    """Return a CompanyProfile, from cache if fresh, else yfinance."""
    cached = _cache.get_profile(ticker)
    if cached:
        cached.pop("_cached_at", None)
        return CompanyProfile(**{k: v for k, v in cached.items()
                                  if k in CompanyProfile.__dataclass_fields__})

    profile = _fetch_profile_yfinance(ticker)
    # Overlay CIK from EDGAR map
    cik = edgar_client.ticker_to_cik(ticker) or ""
    profile.cik = cik

    _cache.save_profile(ticker, _profile_to_dict(profile))
    return profile


def _fetch_profile_yfinance(ticker: str) -> CompanyProfile:
    try:
        import yfinance as yf
        info = yf.Ticker(ticker).info or {}
        return CompanyProfile(
            ticker=ticker,
            name=info.get("longName") or info.get("shortName") or ticker,
            sector=info.get("sector") or "",
            industry=info.get("industry") or "",
            country=info.get("country") or "",
            exchange=info.get("exchange") or "",
            currency=info.get("currency") or "",
            market_cap=float(info.get("marketCap") or float("nan")),
            employees=int(info.get("fullTimeEmployees") or 0),
            description=info.get("longBusinessSummary") or "",
            website=info.get("website") or "",
            last_refreshed=datetime.now(timezone.utc).isoformat(),
        )
    except Exception as exc:
        _log.warning("yfinance profile failed for %s: %s", ticker, exc)
        return CompanyProfile(ticker=ticker)


def fetch_quarterly(ticker: str, n_quarters: int = 8) -> list[QuarterlyFundamentals]:
    """Return up to n_quarters of quarterly fundamentals via yfinance.

    Order: newest quarter first.  No disk cache — callers should cache the result.
    """
    try:
        import yfinance as yf
        tk = yf.Ticker(ticker)
        fin = tk.quarterly_financials
        cf  = tk.quarterly_cashflow

        if fin is None or fin.empty:
            return []

        result: list[QuarterlyFundamentals] = []
        for col in list(fin.columns)[:n_quarters]:
            fy = col.year
            fq = (col.month - 1) // 3 + 1

            def _g(df, *keys) -> float:
                for k in keys:
                    try:
                        v = df.loc[k, col]
                        if v is not None and not math.isnan(float(v)):
                            return float(v)
                    except (KeyError, TypeError, ValueError):
                        pass
                return float("nan")

            rev = _g(fin, "Total Revenue")
            gp  = _g(fin, "Gross Profit")
            oi  = _g(fin, "Operating Income")
            ni  = _g(fin, "Net Income")
            ocf = _g(cf,  "Total Cash From Operating Activities", "Operating Cash Flow")
            cap = _g(cf,  "Capital Expenditures")

            gm  = (gp / rev) if rev else float("nan")
            om  = (oi / rev) if rev else float("nan")
            nm  = (ni / rev) if rev else float("nan")
            fcf = (ocf + cap) if not (math.isnan(ocf) or math.isnan(cap)) else float("nan")

            result.append(QuarterlyFundamentals(
                ticker=ticker,
                fiscal_year=fy,
                fiscal_quarter=fq,
                period_end=col.date().isoformat(),
                revenue=rev, gross_profit=gp, operating_income=oi, net_income=ni,
                gross_margin=gm, operating_margin=om, net_margin=nm,
                operating_cash_flow=ocf, free_cash_flow=fcf,
                source="yfinance",
            ))
        return result
    except Exception as exc:
        _log.warning("Quarterly fetch failed for %s: %s", ticker, exc)
        return []


def _fund_to_dict(f: AnnualFundamentals) -> dict:
    import dataclasses
    return dataclasses.asdict(f)


def _profile_to_dict(p: CompanyProfile) -> dict:
    import dataclasses
    return dataclasses.asdict(p)
