"""Valuation engine — relative multiples scoring and two-stage DCF.

All functions are pure: no network calls, no I/O.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Sequence

from research.models.fundamentals import AnnualFundamentals

_NAN = float("nan")


# ── Data models ───────────────────────────────────────────────────────────────

@dataclass
class ValuationMultiples:
    """Point-in-time valuation multiples for one company or peer group."""
    pe: float = _NAN
    forward_pe: float = _NAN
    ev_ebitda: float = _NAN
    ev_sales: float = _NAN
    ps_ratio: float = _NAN
    pb_ratio: float = _NAN
    fcf_yield: float = _NAN          # FCF / Market Cap (0–1)


@dataclass
class HistoricalMultiples:
    """5-year average multiples reconstructed from price history + AnnualFundamentals."""
    pe_avg: float = _NAN
    ps_avg: float = _NAN
    pb_avg: float = _NAN
    fcf_yield_avg: float = _NAN
    n_years: int = 0


@dataclass
class DcfResult:
    """Output of two-stage DCF model."""
    fair_value_per_share: float = _NAN
    current_price: float = _NAN
    margin_of_safety: float = _NAN    # (fair_value - current) / fair_value
    total_pv: float = _NAN            # absolute PV in USD
    # Assumptions used
    fcf_base: float = _NAN
    growth_rate_1: float = _NAN
    terminal_growth: float = _NAN
    discount_rate: float = _NAN
    years: int = 5


@dataclass
class ValuationAnalysis:
    """Complete valuation assessment for one company."""
    ticker: str

    valuation_score: float = _NAN    # 0-100 (higher = cheaper / more attractive)

    current: ValuationMultiples = field(default_factory=ValuationMultiples)
    historical: HistoricalMultiples = field(default_factory=HistoricalMultiples)
    sector_median: ValuationMultiples = field(default_factory=ValuationMultiples)
    market_pe: float = _NAN           # broad market trailing P/E (e.g. SPY)

    dcf: DcfResult = field(default_factory=DcfResult)

    vs_history: str = "unknown"       # "cheap" | "fair" | "expensive" | "unknown"
    vs_sector: str = "unknown"
    vs_market: str = "unknown"

    strengths: list[str] = field(default_factory=list)
    weaknesses: list[str] = field(default_factory=list)


# ── DCF engine ────────────────────────────────────────────────────────────────

def dcf_fair_value(
    fcf_base: float,
    shares: float,
    growth_rate: float = 0.08,
    terminal_growth: float = 0.025,
    discount_rate: float = 0.10,
    years: int = 5,
) -> DcfResult:
    """Two-stage discounted cash flow model.

    Stage 1: *years* years of FCF growing at *growth_rate*.
    Stage 2: terminal value via Gordon Growth Model at *terminal_growth*.

    Args:
        fcf_base:       most recent annual free cash flow (USD)
        shares:         diluted shares outstanding
        growth_rate:    near-term FCF growth rate (fraction, e.g. 0.10 = 10 %)
        terminal_growth: perpetuity growth rate (fraction, must be < discount_rate)
        discount_rate:  WACC / required return (fraction)
        years:          length of high-growth phase

    Returns:
        DcfResult with fair_value_per_share, margin_of_safety and assumptions.
    """
    result = DcfResult(
        fcf_base=fcf_base, growth_rate_1=growth_rate,
        terminal_growth=terminal_growth, discount_rate=discount_rate, years=years,
    )
    if not all(math.isfinite(v) for v in (fcf_base, shares, growth_rate,
                                           terminal_growth, discount_rate)):
        return result
    if shares <= 0 or discount_rate <= terminal_growth:
        return result
    if fcf_base <= 0:
        # Negative or zero FCF — DCF not meaningful
        return result

    pv_stage1 = 0.0
    for t in range(1, years + 1):
        fcf_t = fcf_base * (1.0 + growth_rate) ** t
        pv_stage1 += fcf_t / (1.0 + discount_rate) ** t

    fcf_terminal = fcf_base * (1.0 + growth_rate) ** years * (1.0 + terminal_growth)
    terminal_value = fcf_terminal / (discount_rate - terminal_growth)
    pv_terminal = terminal_value / (1.0 + discount_rate) ** years

    total_pv = pv_stage1 + pv_terminal
    fv_per_share = total_pv / shares

    result.total_pv = total_pv
    result.fair_value_per_share = fv_per_share
    return result


def fill_dcf_price(dcf: DcfResult, current_price: float) -> DcfResult:
    """Attach current_price and compute margin_of_safety in-place; returns dcf."""
    dcf.current_price = current_price
    fv = dcf.fair_value_per_share
    if math.isfinite(fv) and math.isfinite(current_price) and fv > 0:
        dcf.margin_of_safety = (fv - current_price) / fv
    return dcf


# ── Historical multiples ──────────────────────────────────────────────────────

def compute_historical_multiples(
    funds: list[AnnualFundamentals],
    year_prices: dict[int, float],      # {fiscal_year: year-end price}
    market_cap_history: dict[int, float] | None = None,
) -> HistoricalMultiples:
    """Reconstruct historical average P/E, P/S, P/B from price history + fundamentals.

    *year_prices* maps fiscal year → approximate year-end stock price.
    """
    pe_vals, ps_vals, pb_vals, fcf_y_vals = [], [], [], []

    for f in funds:
        price = year_prices.get(f.fiscal_year)
        if price is None or not math.isfinite(price) or price <= 0:
            continue

        if math.isfinite(f.eps_diluted) and f.eps_diluted > 0:
            pe_vals.append(price / f.eps_diluted)

        if math.isfinite(f.revenue) and f.revenue > 0 and math.isfinite(f.shares_outstanding) and f.shares_outstanding > 0:
            rev_per_share = f.revenue / f.shares_outstanding
            ps_vals.append(price / rev_per_share)

        if math.isfinite(f.book_value_per_share) and f.book_value_per_share > 0:
            pb_vals.append(price / f.book_value_per_share)

        if math.isfinite(f.free_cash_flow) and f.free_cash_flow > 0 and math.isfinite(f.shares_outstanding) and f.shares_outstanding > 0:
            mcap = price * f.shares_outstanding
            if mcap > 0:
                fcf_y_vals.append(f.free_cash_flow / mcap)

    def _avg(lst: list[float]) -> float:
        return float(sum(lst) / len(lst)) if lst else _NAN

    return HistoricalMultiples(
        pe_avg=_avg(pe_vals),
        ps_avg=_avg(ps_vals),
        pb_avg=_avg(pb_vals),
        fcf_yield_avg=_avg(fcf_y_vals),
        n_years=len(funds),
    )


# ── Sector median ─────────────────────────────────────────────────────────────

def compute_sector_median(peer_rows: Sequence[dict]) -> ValuationMultiples:
    """Compute median multiples from screener cache rows for the same sector."""
    def _median(vals: list[float]) -> float:
        clean = sorted(v for v in vals if math.isfinite(v) and v > 0)
        if not clean:
            return _NAN
        mid = len(clean) // 2
        return clean[mid] if len(clean) % 2 else (clean[mid - 1] + clean[mid]) / 2.0

    def _collect(key: str) -> list[float]:
        out = []
        for r in peer_rows:
            v = r.get(key)
            if v is not None:
                try:
                    f = float(v)
                    if math.isfinite(f):
                        out.append(f)
                except (TypeError, ValueError):
                    pass
        return out

    return ValuationMultiples(
        pe=_median(_collect("trailing_pe")),
        forward_pe=_median(_collect("forward_pe")),
        pb_ratio=_median(_collect("price_to_book")),
        fcf_yield=_median(_collect("dividend_yield")),   # approximation if FCF yield not stored
    )


# ── Valuation scoring ─────────────────────────────────────────────────────────

def _ok(v: float) -> bool:
    return math.isfinite(v)


def _clamp(v: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, v))


def _score_pe_relative(pe: float, benchmark: float) -> float:
    """Score 0-100 based on how cheap PE is vs benchmark."""
    if not (_ok(pe) and _ok(benchmark) and benchmark > 0 and pe > 0):
        return _NAN
    ratio = pe / benchmark   # < 1 = discount, > 1 = premium
    if ratio < 0.7:
        return 90.0
    if ratio < 0.9:
        return _clamp(75.0 + (0.9 - ratio) / 0.2 * 15.0)
    if ratio < 1.1:
        return _clamp(55.0 + (1.1 - ratio) / 0.2 * 20.0)
    if ratio < 1.3:
        return _clamp(35.0 + (1.3 - ratio) / 0.2 * 20.0)
    return _clamp(35.0 - (ratio - 1.3) * 50.0)


def _score_fcf_yield(y: float) -> float:
    """Score 0-100: higher yield = cheaper (FCF / Market Cap)."""
    if not _ok(y):
        return _NAN
    pct = y * 100.0
    if pct <= 0:
        return 5.0
    if pct < 2:
        return _clamp(pct * 20.0)          # 0 → 0, 2 % → 40
    if pct < 5:
        return _clamp(40.0 + (pct - 2) * 13.33)  # 2 → 40, 5 → 80
    return _clamp(80.0 + (pct - 5) * 4.0, hi=100.0)


def _score_dcf_mos(mos: float) -> float:
    """Score 0-100 from margin of safety; > 30 % = excellent."""
    if not _ok(mos):
        return _NAN
    pct = mos * 100.0
    if pct >= 40:
        return 95.0
    if pct >= 20:
        return _clamp(70.0 + (pct - 20) * 1.25)
    if pct >= 0:
        return _clamp(50.0 + pct * 1.0)
    if pct >= -20:
        return _clamp(50.0 + pct * 1.5)   # 0 → 50, -20 → 20
    return _clamp(20.0 + (pct + 20) * 0.5)


def _vs_label(ratio: float) -> str:
    """Map a current/benchmark ratio to a cheap/fair/expensive label."""
    if not _ok(ratio):
        return "unknown"
    if ratio < 0.80:
        return "cheap"
    if ratio < 1.15:
        return "fair"
    return "expensive"


def _explain_valuation(
    a: ValuationAnalysis,
) -> tuple[list[str], list[str]]:
    strengths, weaknesses = [], []

    cur = a.current
    hist = a.historical
    sec = a.sector_median

    def _pct(v: float, digits: int = 1) -> str:
        return f"{v * 100:.{digits}f}%"

    def _fmt(v: float, suffix: str = "×") -> str:
        return f"{v:.1f}{suffix}" if _ok(v) else "—"

    # FCF yield
    if _ok(cur.fcf_yield):
        if cur.fcf_yield >= 0.05:
            strengths.append(f"High FCF yield ({_pct(cur.fcf_yield)}) — cash-generative at this price")
        elif cur.fcf_yield < 0.01:
            weaknesses.append(f"Very low FCF yield ({_pct(cur.fcf_yield)}) — limited cash return")

    # P/E vs history
    if _ok(cur.pe) and _ok(hist.pe_avg):
        ratio = cur.pe / hist.pe_avg
        if ratio < 0.80:
            strengths.append(f"P/E {_fmt(cur.pe)} is {_pct(1-ratio)} below own 5-yr avg ({_fmt(hist.pe_avg)})")
        elif ratio > 1.30:
            weaknesses.append(f"P/E {_fmt(cur.pe)} is {_pct(ratio-1)} above own 5-yr avg ({_fmt(hist.pe_avg)})")

    # P/E vs sector
    if _ok(cur.pe) and _ok(sec.pe) and sec.pe > 0:
        ratio = cur.pe / sec.pe
        if ratio < 0.80:
            strengths.append(f"Trades at {_pct(1-ratio)} P/E discount to sector median ({_fmt(sec.pe)})")
        elif ratio > 1.25:
            weaknesses.append(f"Trades at {_pct(ratio-1)} P/E premium to sector median ({_fmt(sec.pe)})")

    # P/E vs market
    if _ok(cur.pe) and _ok(a.market_pe) and a.market_pe > 0:
        ratio = cur.pe / a.market_pe
        if ratio < 0.80:
            strengths.append(f"Cheaper than broad market (P/E {_fmt(cur.pe)} vs market {_fmt(a.market_pe)})")
        elif ratio > 1.40:
            weaknesses.append(f"Significant premium to market P/E ({_fmt(cur.pe)} vs {_fmt(a.market_pe)})")

    # Forward P/E
    if _ok(cur.forward_pe) and _ok(cur.pe):
        if cur.forward_pe < cur.pe * 0.85:
            strengths.append(f"Fwd P/E {_fmt(cur.forward_pe)} implies meaningful earnings growth expected")
        elif cur.forward_pe > cur.pe * 1.10:
            weaknesses.append(f"Fwd P/E {_fmt(cur.forward_pe)} above trailing — earnings expected to compress")

    # DCF
    if _ok(a.dcf.margin_of_safety) and _ok(a.dcf.fair_value_per_share):
        mos = a.dcf.margin_of_safety
        fv  = a.dcf.fair_value_per_share
        cp  = a.dcf.current_price
        if mos >= 0.20:
            strengths.append(f"DCF suggests {_pct(mos)} margin of safety (fair value ~${fv:.0f} vs price ~${cp:.0f})")
        elif mos <= -0.15:
            weaknesses.append(f"DCF suggests stock is {_pct(abs(mos))} above intrinsic value (${fv:.0f})")

    # P/B
    if _ok(cur.pb_ratio):
        if cur.pb_ratio < 1.5:
            strengths.append(f"Low Price/Book ratio ({_fmt(cur.pb_ratio)})")
        elif cur.pb_ratio > 10:
            weaknesses.append(f"Very high Price/Book ratio ({_fmt(cur.pb_ratio)}) — price far above book value")

    return strengths, weaknesses


# ── Main entry point ──────────────────────────────────────────────────────────

def score_valuation(
    ticker: str,
    current: ValuationMultiples,
    historical: HistoricalMultiples,
    sector_median: ValuationMultiples,
    dcf: DcfResult,
    market_pe: float = _NAN,
) -> ValuationAnalysis:
    """Compute a ValuationAnalysis from multiples and DCF.

    All inputs are pre-computed by the caller (fetcher + engine).
    This function is pure — no I/O.
    """
    scores: list[tuple[float, float]] = []  # (score, weight)

    # FCF yield: weight 25 %
    fcf_s = _score_fcf_yield(current.fcf_yield)
    if _ok(fcf_s):
        scores.append((fcf_s, 0.25))

    # P/E vs sector: weight 20 %
    pe_sec_s = _score_pe_relative(current.pe, sector_median.pe)
    if _ok(pe_sec_s):
        scores.append((pe_sec_s, 0.20))

    # P/E vs history: weight 20 %
    pe_hist_s = _score_pe_relative(current.pe, historical.pe_avg)
    if _ok(pe_hist_s):
        scores.append((pe_hist_s, 0.20))

    # P/E vs market: weight 10 %
    pe_mkt_s = _score_pe_relative(current.pe, market_pe)
    if _ok(pe_mkt_s):
        scores.append((pe_mkt_s, 0.10))

    # Forward P/E vs sector: weight 10 %
    fpe_sec_s = _score_pe_relative(current.forward_pe, sector_median.forward_pe)
    if _ok(fpe_sec_s):
        scores.append((fpe_sec_s, 0.10))

    # DCF margin of safety: weight 15 %
    dcf_s = _score_dcf_mos(dcf.margin_of_safety)
    if _ok(dcf_s):
        scores.append((dcf_s, 0.15))

    if scores:
        total_w = sum(w for _, w in scores)
        composite = sum(s * w for s, w in scores) / total_w
    else:
        composite = _NAN

    # vs history / sector / market labels
    hist_ratio = current.pe / historical.pe_avg if (_ok(current.pe) and _ok(historical.pe_avg) and historical.pe_avg > 0) else _NAN
    sec_ratio  = current.pe / sector_median.pe  if (_ok(current.pe) and _ok(sector_median.pe)  and sector_median.pe  > 0) else _NAN
    mkt_ratio  = current.pe / market_pe         if (_ok(current.pe) and _ok(market_pe)         and market_pe         > 0) else _NAN

    result = ValuationAnalysis(
        ticker=ticker,
        valuation_score=composite,
        current=current,
        historical=historical,
        sector_median=sector_median,
        market_pe=market_pe,
        dcf=dcf,
        vs_history=_vs_label(hist_ratio),
        vs_sector=_vs_label(sec_ratio),
        vs_market=_vs_label(mkt_ratio),
    )
    result.strengths, result.weaknesses = _explain_valuation(result)
    return result
