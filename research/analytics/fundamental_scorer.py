"""Fundamental scoring engine — computes component scores and explainability.

All functions are pure: no network calls, no Qt, no I/O.
Input:  list[AnnualFundamentals]  (newest year first)
Output: FundamentalAnalysis dataclass
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Sequence

from research.models.fundamentals import AnnualFundamentals


# ── Result dataclass ──────────────────────────────────────────────────────────

@dataclass
class FundamentalAnalysis:
    """Full fundamental assessment for one company.

    Sub-scores are 0–100.  NaN means insufficient data for that component.
    """
    ticker: str
    n_years: int                            # number of annual periods used

    # ── Sub-scores ────────────────────────────────────────────────────────────
    growth_score: float = float("nan")              # Rev / EPS / FCF growth
    profitability_score: float = float("nan")       # Gross / Op / Net margins + FCF margin
    capital_efficiency_score: float = float("nan")  # ROIC / ROE / ROA
    balance_sheet_score: float = float("nan")       # D/E / Interest cov. / Current ratio
    fundamental_score: float = float("nan")         # 30/30/25/15 weighted composite

    # ── Key metrics (most recent year) ───────────────────────────────────────
    revenue_cagr_3y: float = float("nan")
    eps_cagr_3y: float = float("nan")
    fcf_cagr_3y: float = float("nan")
    roic: float = float("nan")             # NOPAT / Invested Capital (25 % tax assumed)
    interest_coverage: float = float("nan")
    current_ratio: float = float("nan")
    fcf_margin: float = float("nan")

    # ── Trend indicators ─────────────────────────────────────────────────────
    margin_trend: str = "stable"           # "expanding" | "stable" | "compressing"
    revenue_trend: str = "stable"          # "accelerating" | "stable" | "decelerating"

    # ── Peer comparison ───────────────────────────────────────────────────────
    sector_percentile: float = float("nan")  # % of sector peers with lower fund score
    sector_avg_score: float = float("nan")

    # ── Explainability ────────────────────────────────────────────────────────
    strengths: list[str] = field(default_factory=list)
    weaknesses: list[str] = field(default_factory=list)


# ── Helpers ───────────────────────────────────────────────────────────────────

_NAN = float("nan")


def _ok(v: float) -> bool:
    return not math.isnan(v)


def _clamp(v: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, v))


def _cagr(v_new: float, v_old: float, n: int) -> float:
    """Compound annual growth rate over *n* years."""
    if n <= 0 or not (_ok(v_new) and _ok(v_old)):
        return _NAN
    if v_old <= 0:
        return _NAN
    try:
        return (v_new / v_old) ** (1.0 / n) - 1.0
    except (ZeroDivisionError, ValueError):
        return _NAN


def _growth_score_from_cagr(cagr: float) -> float:
    """Map a CAGR (fraction) to a 0–100 sub-score.

    Anchors: -10 % → 0, 0 % → 30, 10 % → 65, 20 % → 90, ≥ 30 % → 100
    """
    if not _ok(cagr):
        return _NAN
    pct = cagr * 100.0
    if pct <= -10:
        return 0.0
    if pct <= 0:
        return _clamp(30.0 + pct * 3.0)        # -10 % → 0, 0 % → 30
    if pct <= 10:
        return _clamp(30.0 + pct * 3.5)        # 0 % → 30, 10 % → 65
    if pct <= 20:
        return _clamp(65.0 + (pct - 10) * 2.5) # 10 % → 65, 20 % → 90
    return _clamp(90.0 + (pct - 20) * 0.5, hi=100.0)  # 20 % → 90, 40 % → 100


# ── Sub-scorers ───────────────────────────────────────────────────────────────

def _score_growth(funds: list[AnnualFundamentals]) -> tuple[float, float, float, float]:
    """Returns (growth_score, rev_cagr_3y, eps_cagr_3y, fcf_cagr_3y)."""
    if len(funds) < 2:
        return _NAN, _NAN, _NAN, _NAN

    n = min(3, len(funds) - 1)
    f0, fn = funds[0], funds[n]     # newest, n years ago

    rev_cagr = _cagr(f0.revenue, fn.revenue, n)
    eps_cagr = _cagr(f0.eps_diluted, fn.eps_diluted, n)
    fcf_cagr = _cagr(f0.free_cash_flow, fn.free_cash_flow, n)

    scores = [_growth_score_from_cagr(c) for c in (rev_cagr, eps_cagr, fcf_cagr)
              if _ok(c)]
    composite = float(sum(scores) / len(scores)) if scores else _NAN
    return composite, rev_cagr, eps_cagr, fcf_cagr


def _score_profitability(f: AnnualFundamentals) -> float:
    """Score 0–100 from current-year gross/op/net margins and FCF margin.

    Anchors for gross margin:   0 % → 0, 25 % → 40, 50 % → 70, 80 % → 100
    Anchors for op/net margin:  0 % → 0, 10 % → 50, 20 % → 75, 40 % → 100
    FCF margin:                 negative → 20, 0-10 % → 40-70, > 20 % → 90-100
    """
    scores: list[float] = []

    if _ok(f.gross_margin):
        gm = f.gross_margin * 100.0
        scores.append(_clamp(gm * 1.25))           # 80 % → 100

    if _ok(f.operating_margin):
        om = f.operating_margin * 100.0
        scores.append(_clamp(50.0 + om * 2.5))     # 0 % → 50, 20 % → 100

    if _ok(f.net_margin):
        nm = f.net_margin * 100.0
        scores.append(_clamp(50.0 + nm * 2.5))

    if _ok(f.free_cash_flow) and _ok(f.revenue) and f.revenue > 0:
        fcf_m = (f.free_cash_flow / f.revenue) * 100.0
        scores.append(_clamp(50.0 + fcf_m * 2.0))

    return float(sum(scores) / len(scores)) if scores else _NAN


def _compute_roic(f: AnnualFundamentals) -> float:
    """ROIC = NOPAT / Invested Capital.  Assumes 25 % effective tax rate."""
    if not (_ok(f.operating_income) and _ok(f.total_equity)):
        return _NAN
    nopat = f.operating_income * 0.75
    # Invested Capital = Total Equity + Total Debt − Cash
    debt  = f.total_debt if _ok(f.total_debt) else 0.0
    cash  = f.cash       if _ok(f.cash)       else 0.0
    ic = f.total_equity + debt - cash
    if ic <= 0:
        return _NAN
    return nopat / ic


def _score_capital_efficiency(f: AnnualFundamentals) -> tuple[float, float]:
    """Returns (score, roic).

    ROIC thresholds: < 5 % → 20, 5-15 % → 40-75, 15-30 % → 75-95, > 30 % → 95-100
    ROE  thresholds: < 5 % → 20, 5-20 % → 40-80, > 20 % → 80-100
    ROA  thresholds: < 2 % → 20, 2-10 % → 40-80, > 10 % → 80-100
    """
    roic = _compute_roic(f)
    scores: list[float] = []

    if _ok(roic):
        r = roic * 100.0
        if r < 5:
            scores.append(_clamp(r * 4.0))          # 0 → 0, 5 → 20
        elif r < 15:
            scores.append(_clamp(20.0 + (r - 5) * 5.5))  # 5 → 20, 15 → 75
        elif r < 30:
            scores.append(_clamp(75.0 + (r - 15) * 1.33)) # 15 → 75, 30 → 95
        else:
            scores.append(_clamp(95.0 + (r - 30) * 0.2))

    if _ok(f.return_on_equity):
        r = f.return_on_equity * 100.0
        scores.append(_clamp(50.0 + r * 2.0))       # 0 % → 50, 25 % → 100

    if _ok(f.return_on_assets):
        r = f.return_on_assets * 100.0
        scores.append(_clamp(50.0 + r * 5.0))       # 0 % → 50, 10 % → 100

    s = float(sum(scores) / len(scores)) if scores else _NAN
    return s, roic


def _compute_interest_coverage(f: AnnualFundamentals) -> float:
    """EBIT / Interest Expense.  Uses operating_income as EBIT proxy."""
    if _ok(f.interest_expense) and f.interest_expense > 0 and _ok(f.operating_income):
        return f.operating_income / f.interest_expense
    return _NAN


def _compute_current_ratio(f: AnnualFundamentals) -> float:
    if _ok(f.current_assets) and _ok(f.current_liabilities) and f.current_liabilities > 0:
        return f.current_assets / f.current_liabilities
    return _NAN


def _score_balance_sheet(f: AnnualFundamentals) -> tuple[float, float, float]:
    """Returns (score, interest_coverage, current_ratio).

    D/E:  > 4 → 5, 2-4 → 30-55, 1-2 → 55-75, < 1 → 75-100
    IC:   < 1.5 → 5, 1.5-3 → 30-55, 3-10 → 55-85, > 10 → 85-100
    CR:   < 0.8 → 5, 0.8-1.2 → 30-55, 1.2-2 → 55-80, > 2 → 80-100
    """
    scores: list[float] = []

    de = f.debt_to_equity if _ok(f.debt_to_equity) else _NAN
    if _ok(de):
        if de > 4:
            scores.append(5.0)
        elif de > 2:
            scores.append(_clamp(55.0 - (de - 2) * 12.5))  # 2 → 55, 4 → 30
        elif de > 1:
            scores.append(_clamp(75.0 - (de - 1) * 20.0))  # 1 → 75, 2 → 55
        else:
            scores.append(_clamp(100.0 - de * 25.0))        # 0 → 100, 1 → 75

    ic = _compute_interest_coverage(f)
    if _ok(ic):
        if ic < 1.5:
            scores.append(_clamp(ic * 20.0))
        elif ic < 3:
            scores.append(_clamp(30.0 + (ic - 1.5) * 16.67))  # 1.5 → 30, 3 → 55
        elif ic < 10:
            scores.append(_clamp(55.0 + (ic - 3) * 4.28))     # 3 → 55, 10 → 85
        else:
            scores.append(_clamp(85.0 + (ic - 10) * 0.5, hi=100.0))

    cr = _compute_current_ratio(f)
    if _ok(cr):
        if cr < 0.8:
            scores.append(_clamp(cr * 37.5))
        elif cr < 1.2:
            scores.append(_clamp(30.0 + (cr - 0.8) * 62.5))  # 0.8 → 30, 1.2 → 55
        elif cr < 2:
            scores.append(_clamp(55.0 + (cr - 1.2) * 31.25)) # 1.2 → 55, 2 → 80
        else:
            scores.append(_clamp(80.0 + (cr - 2) * 5.0, hi=100.0))

    s = float(sum(scores) / len(scores)) if scores else _NAN
    return s, ic, cr


# ── Trend analysis ────────────────────────────────────────────────────────────

def _margin_trend(funds: list[AnnualFundamentals]) -> str:
    """Compare net margin of most recent year vs 3 years ago."""
    if len(funds) < 4:
        return "stable"
    f0, f3 = funds[0], funds[3]
    if not (_ok(f0.net_margin) and _ok(f3.net_margin)):
        return "stable"
    delta_pp = (f0.net_margin - f3.net_margin) * 100.0
    if delta_pp > 2.0:
        return "expanding"
    if delta_pp < -2.0:
        return "compressing"
    return "stable"


def _revenue_trend(funds: list[AnnualFundamentals]) -> str:
    """Compare revenue growth last 2 years vs prior 2 years."""
    if len(funds) < 5:
        return "stable"
    recent_cagr = _cagr(funds[0].revenue, funds[2].revenue, 2)
    prior_cagr  = _cagr(funds[2].revenue, funds[4].revenue, 2)
    if not (_ok(recent_cagr) and _ok(prior_cagr)):
        return "stable"
    diff = (recent_cagr - prior_cagr) * 100.0
    if diff > 3.0:
        return "accelerating"
    if diff < -3.0:
        return "decelerating"
    return "stable"


# ── Strengths & Weaknesses ────────────────────────────────────────────────────

def _explain(analysis: FundamentalAnalysis, f: AnnualFundamentals) -> tuple[list[str], list[str]]:
    strengths: list[str] = []
    weaknesses: list[str] = []

    def _pct(v: float) -> str:
        return f"{v * 100:.1f}%"

    def _bn(v: float) -> str:
        if abs(v) >= 1e9:
            return f"${v/1e9:.1f}B"
        return f"${v/1e6:.0f}M"

    # Growth
    if _ok(analysis.revenue_cagr_3y):
        if analysis.revenue_cagr_3y > 0.10:
            strengths.append(f"Strong revenue growth ({_pct(analysis.revenue_cagr_3y)}/yr, 3-yr CAGR)")
        elif analysis.revenue_cagr_3y < -0.02:
            weaknesses.append(f"Revenue declining ({_pct(analysis.revenue_cagr_3y)}/yr, 3-yr CAGR)")

    if _ok(analysis.eps_cagr_3y):
        if analysis.eps_cagr_3y > 0.12:
            strengths.append(f"Accelerating EPS growth ({_pct(analysis.eps_cagr_3y)}/yr)")
        elif analysis.eps_cagr_3y < -0.05:
            weaknesses.append(f"EPS declining ({_pct(analysis.eps_cagr_3y)}/yr)")

    if _ok(analysis.fcf_cagr_3y) and analysis.fcf_cagr_3y > 0.10:
        strengths.append(f"Free cash flow growing at {_pct(analysis.fcf_cagr_3y)}/yr")

    # Profitability
    if _ok(f.net_margin):
        if f.net_margin > 0.20:
            strengths.append(f"High net margin ({_pct(f.net_margin)})")
        elif f.net_margin < 0:
            weaknesses.append(f"Unprofitable (net margin {_pct(f.net_margin)})")
        elif f.net_margin < 0.03:
            weaknesses.append(f"Thin net margin ({_pct(f.net_margin)})")

    if _ok(f.gross_margin) and f.gross_margin > 0.60:
        strengths.append(f"Premium gross margins ({_pct(f.gross_margin)})")

    if _ok(f.free_cash_flow):
        if f.free_cash_flow > 0:
            strengths.append(f"Positive free cash flow ({_bn(f.free_cash_flow)})")
        else:
            weaknesses.append(f"Negative free cash flow ({_bn(f.free_cash_flow)})")

    # Capital efficiency
    if _ok(analysis.roic):
        if analysis.roic > 0.20:
            strengths.append(f"Excellent capital returns (ROIC {_pct(analysis.roic)})")
        elif analysis.roic < 0.05:
            weaknesses.append(f"Low capital returns (ROIC {_pct(analysis.roic)})")

    if _ok(f.return_on_equity):
        if f.return_on_equity > 0.25:
            strengths.append(f"High ROE ({_pct(f.return_on_equity)})")
        elif f.return_on_equity < 0:
            weaknesses.append(f"Negative ROE ({_pct(f.return_on_equity)})")

    # Balance sheet
    if _ok(analysis.interest_coverage):
        if analysis.interest_coverage > 10:
            strengths.append(f"Very comfortable debt service (interest coverage {analysis.interest_coverage:.1f}×)")
        elif analysis.interest_coverage < 2.5:
            weaknesses.append(f"Tight interest coverage ({analysis.interest_coverage:.1f}×)")

    if _ok(f.debt_to_equity):
        if f.debt_to_equity < 0.3:
            strengths.append(f"Very low leverage (D/E {f.debt_to_equity:.2f}×)")
        elif f.debt_to_equity > 3.0:
            weaknesses.append(f"High leverage (D/E {f.debt_to_equity:.2f}×)")

    if _ok(analysis.current_ratio):
        if analysis.current_ratio < 1.0:
            weaknesses.append(f"Tight liquidity (current ratio {analysis.current_ratio:.2f}×)")
        elif analysis.current_ratio > 2.5:
            strengths.append(f"Strong liquidity (current ratio {analysis.current_ratio:.2f}×)")

    # Trend
    if analysis.margin_trend == "expanding":
        strengths.append("Margins expanding over the past 3 years")
    elif analysis.margin_trend == "compressing":
        weaknesses.append("Margin compression over the past 3 years")

    if analysis.revenue_trend == "accelerating":
        strengths.append("Revenue growth accelerating vs prior period")
    elif analysis.revenue_trend == "decelerating":
        weaknesses.append("Revenue growth decelerating vs prior period")

    # Peer comparison
    if _ok(analysis.sector_percentile):
        if analysis.sector_percentile >= 75:
            strengths.append(f"Top-quartile fundamentals in sector ({analysis.sector_percentile:.0f}th percentile)")
        elif analysis.sector_percentile < 25:
            weaknesses.append(f"Below-average fundamentals in sector ({analysis.sector_percentile:.0f}th percentile)")

    return strengths, weaknesses


# ── Main entry point ──────────────────────────────────────────────────────────

def score_fundamentals(
    ticker: str,
    funds: list[AnnualFundamentals],
    sector_scores: Sequence[float] | None = None,
) -> FundamentalAnalysis:
    """Compute a FundamentalAnalysis from annual fundamental history.

    Args:
        ticker:        company ticker
        funds:         annual fundamentals, newest first
        sector_scores: optional list of fund scores for sector peers (for percentile)

    Returns:
        FundamentalAnalysis with all sub-scores, trend indicators, and explainability.
    """
    if not funds:
        return FundamentalAnalysis(ticker=ticker, n_years=0)

    f0 = funds[0]  # most recent year
    n  = len(funds)

    # Sub-scores
    growth_score, rev_cagr, eps_cagr, fcf_cagr = _score_growth(funds)
    prof_score  = _score_profitability(f0)
    cap_score, roic = _score_capital_efficiency(f0)
    bs_score, ic, cr = _score_balance_sheet(f0)

    # FCF margin
    fcf_margin = (f0.free_cash_flow / f0.revenue) if (
        _ok(f0.free_cash_flow) and _ok(f0.revenue) and f0.revenue > 0
    ) else _NAN

    # Weighted composite: 30 / 30 / 25 / 15
    parts = [(growth_score, 0.30), (prof_score, 0.30), (cap_score, 0.25), (bs_score, 0.15)]
    valid = [(s, w) for s, w in parts if _ok(s)]
    composite = sum(s * w for s, w in valid) / sum(w for _, w in valid) if valid else _NAN

    # Trend
    m_trend = _margin_trend(funds)
    r_trend = _revenue_trend(funds)

    # Peer comparison
    sector_pct = _NAN
    sector_avg = _NAN
    if sector_scores and _ok(composite):
        valid_peers = [s for s in sector_scores if _ok(s)]
        if valid_peers:
            sector_avg = sum(valid_peers) / len(valid_peers)
            sector_pct = float(sum(1 for s in valid_peers if s < composite) / len(valid_peers) * 100.0)

    result = FundamentalAnalysis(
        ticker=ticker, n_years=n,
        growth_score=growth_score,
        profitability_score=prof_score,
        capital_efficiency_score=cap_score,
        balance_sheet_score=bs_score,
        fundamental_score=composite,
        revenue_cagr_3y=rev_cagr,
        eps_cagr_3y=eps_cagr,
        fcf_cagr_3y=fcf_cagr,
        roic=roic,
        interest_coverage=ic,
        current_ratio=cr,
        fcf_margin=fcf_margin,
        margin_trend=m_trend,
        revenue_trend=r_trend,
        sector_percentile=sector_pct,
        sector_avg_score=sector_avg,
    )
    result.strengths, result.weaknesses = _explain(result, f0)
    return result
