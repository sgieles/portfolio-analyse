"""Rule-based investment thesis generator — pure analytics, no I/O.

Generates a structured investment thesis from the full set of analysis
results. No LLM is required: the text is data-driven via templates.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field


# ── Overall score & verdict ────────────────────────────────────────────────────

VERDICTS = [
    (75, "Strong Buy",  "The combination of strong fundamentals, attractive valuation "
                        "and positive momentum creates a compelling entry point."),
    (62, "Buy",         "The risk/reward profile is favourable. Quality is high and "
                        "the valuation leaves room for appreciation."),
    (48, "Hold",        "The investment case is mixed. Strengths are offset by risks "
                        "or the current valuation already reflects the upside."),
    (35, "Reduce",      "Several headwinds weigh on the near-term outlook. "
                        "Caution is warranted at current levels."),
    (0,  "Avoid",       "The combination of weak fundamentals, stretched valuation "
                        "or deteriorating trends does not support investment."),
]


def overall_score(
    fund_score: float,
    val_score:  float,
    tech_score: float,
    sector_score: float,
    insider_score: float,
) -> float:
    """Weighted overall score (0-100).

    Weights: Fundamentals 30%, Valuation 25%, Technical 20%, Sector 15%, Insider 10%.
    NaN inputs are excluded; remaining weights are renormalised.
    """
    pairs = [
        (fund_score,    0.30),
        (val_score,     0.25),
        (tech_score,    0.20),
        (sector_score,  0.15),
        (insider_score, 0.10),
    ]
    valid = [(s, w) for s, w in pairs if not math.isnan(s)]
    if not valid:
        return 50.0
    total_w = sum(w for _, w in valid)
    return sum(s * w for s, w in valid) / total_w


def verdict(score: float) -> tuple[str, str]:
    """Return (label, rationale) for the overall score."""
    for threshold, label, rationale in VERDICTS:
        if score >= threshold:
            return label, rationale
    return "Avoid", VERDICTS[-1][2]


# ── Section generators ─────────────────────────────────────────────────────────

def _quality_paragraph(company_name: str, sector: str, fund_score: float,
                        strengths: list[str], weaknesses: list[str]) -> str:
    if math.isnan(fund_score):
        return f"{company_name} operates in the {sector} sector."

    if fund_score >= 70:
        quality = "high-quality"
        quality_desc = (
            "The company demonstrates strong and consistent financial performance "
            "across growth, profitability and capital efficiency metrics."
        )
    elif fund_score >= 50:
        quality = "above-average"
        quality_desc = (
            "The company shows solid fundamentals with some areas of strength, "
            "though not uniformly exceptional across all metrics."
        )
    elif fund_score >= 35:
        quality = "mixed"
        quality_desc = (
            "The company shows an uneven fundamental profile with notable strengths "
            "alongside areas of concern."
        )
    else:
        quality = "below-average"
        quality_desc = (
            "The company faces fundamental challenges that weigh on the investment case, "
            "including weak profitability or deteriorating financial health."
        )

    top_strength = strengths[0] if strengths else None
    top_weakness = weaknesses[0] if weaknesses else None

    text = (
        f"{company_name} is a {quality}-quality business operating in the {sector} sector "
        f"(Fundamental Score: {fund_score:.0f}/100). {quality_desc}"
    )
    if top_strength:
        text += f" A key strength is: {top_strength.lower()}."
    if top_weakness and fund_score < 65:
        text += f" However, {top_weakness.lower()}."
    return text


def _valuation_paragraph(val_score: float, val_signal: str | None,
                          cheap_signals: list[str], expensive_signals: list[str]) -> str:
    if math.isnan(val_score):
        return "Valuation data is not available for this company."

    if val_score >= 65:
        outlook = (
            f"From a valuation perspective, the stock appears attractively priced "
            f"(Valuation Score: {val_score:.0f}/100)."
        )
    elif val_score >= 45:
        outlook = (
            f"The stock is trading at a roughly fair valuation "
            f"(Valuation Score: {val_score:.0f}/100)."
        )
    else:
        outlook = (
            f"The current valuation looks stretched relative to fundamentals "
            f"(Valuation Score: {val_score:.0f}/100)."
        )

    details = []
    if cheap_signals:
        details.append(f"Positive valuation signals include: {cheap_signals[0].lower()}")
    if expensive_signals:
        details.append(f"A valuation concern is: {expensive_signals[0].lower()}")

    return outlook + (" " + " ".join(details) if details else "")


def _insider_paragraph(insider_score: float, insider_signal: str,
                        n_buys: int, n_sells: int) -> str:
    if math.isnan(insider_score) or insider_signal == "Neutral" and n_buys == 0 and n_sells == 0:
        return (
            "Insider transaction data is limited or unavailable, providing no "
            "additional signal on management conviction."
        )
    if insider_signal == "Bullish":
        return (
            f"Insider activity is a positive signal: executives and directors have "
            f"recorded {n_buys} purchase(s) against {n_sells} sale(s) in the last "
            f"12 months (Insider Score: {insider_score:.0f}/100). Insider buying — "
            "particularly by senior management — historically precedes outperformance."
        )
    if insider_signal == "Bearish":
        return (
            f"Insiders have been net sellers over the past 12 months ({n_sells} sale(s) "
            f"vs {n_buys} purchase(s)), which tempers conviction (Insider Score: "
            f"{insider_score:.0f}/100). While selling often reflects personal "
            "diversification needs, sustained net selling warrants attention."
        )
    return (
        f"Insider activity over the past 12 months is balanced ({n_buys} purchase(s), "
        f"{n_sells} sale(s)), providing no clear directional signal "
        f"(Insider Score: {insider_score:.0f}/100)."
    )


def _sector_paragraph(sector: str, sector_score: float, sector_outlook: str,
                       sector_rs: float) -> str:
    if math.isnan(sector_score):
        return f"The {sector} sector context was not available at the time of this analysis."

    rs_text = ""
    if not math.isnan(sector_rs):
        if sector_rs > 0.05:
            rs_text = (
                f" The sector has outperformed the S&P 500 by {sector_rs*100:.0f}pp "
                "over the past 12 months, providing a supportive backdrop."
            )
        elif sector_rs < -0.05:
            rs_text = (
                f" The sector has underperformed the S&P 500 by {abs(sector_rs)*100:.0f}pp "
                "over the past 12 months, creating a headwind."
            )

    return (
        f"The {sector} sector carries a {sector_outlook.lower()} outlook "
        f"(Sector Score: {sector_score:.0f}/100).{rs_text}"
    )


def _technical_paragraph(tech_score: float, tech_signal: str, ta) -> str:
    if math.isnan(tech_score):
        return "Technical data is not available."

    if tech_signal in ("Strong", "Positive"):
        trend_text = (
            f"The technical picture supports the investment case (Technical Score: "
            f"{tech_score:.0f}/100). "
        )
    elif tech_signal == "Neutral":
        trend_text = (
            f"The technical setup is neutral (Technical Score: {tech_score:.0f}/100). "
        )
    else:
        trend_text = (
            f"The technical picture is a headwind (Technical Score: {tech_score:.0f}/100). "
        )

    details = []
    if ta.above_ma200 is not None:
        details.append(
            "trading above its 200-day moving average" if ta.above_ma200
            else "trading below its 200-day moving average"
        )
    if ta.golden_cross is not None:
        details.append(
            "with a golden cross (50d > 200d MA) in place" if ta.golden_cross
            else "with the 50-day MA below the 200-day MA (death cross)"
        )
    if not math.isnan(ta.rsi_14):
        rsi = ta.rsi_14
        if rsi > 70:
            details.append(f"RSI at {rsi:.0f} signals overbought conditions")
        elif rsi < 30:
            details.append(f"RSI at {rsi:.0f} signals oversold conditions — potential mean-reversion opportunity")
        else:
            details.append(f"RSI at {rsi:.0f} is in a healthy zone")
    if not math.isnan(ta.pct_from_52w_high):
        pct = ta.pct_from_52w_high * 100
        details.append(f"the stock is {abs(pct):.0f}% {'below' if pct < 0 else 'above'} its 52-week high")

    if details:
        trend_text += "The stock is " + ", ".join(details[:3]) + "."
    return trend_text


def _risk_bullets(
    weaknesses: list[str],
    expensive_signals: list[str],
    sector_threats: list[str],
    tech_signal: str,
    insider_signal: str,
) -> list[str]:
    risks: list[str] = []
    if weaknesses:
        risks.extend(weaknesses[:2])
    if expensive_signals:
        risks.append(expensive_signals[0])
    if sector_threats:
        risks.append(sector_threats[0])
    if tech_signal in ("Negative", "Weak"):
        risks.append("Negative price momentum — technical trend is broken or deteriorating")
    if insider_signal == "Bearish":
        risks.append("Net insider selling raises questions about near-term management outlook")
    # Always have at least two risks
    if len(risks) < 2:
        risks.extend([
            "Macro uncertainty and interest rate volatility remain key external risks",
            "Execution risk: guidance misses could lead to multiple compression",
        ])
    return risks[:5]  # cap at 5


# ── Main entry point ────────────────────────────────────────────────────────────

@dataclass
class InvestmentThesis:
    overall_score: float
    verdict_label: str
    verdict_rationale: str
    quality_paragraph:   str = ""
    valuation_paragraph: str = ""
    insider_paragraph:   str = ""
    sector_paragraph:    str = ""
    technical_paragraph: str = ""
    risk_bullets: list[str] = field(default_factory=list)
    macro_context: str = ""


def generate_thesis(
    company_name: str,
    sector: str,
    fund_score: float,
    val_score: float,
    tech_score: float,
    sector_score: float,
    insider_score: float,
    strengths: list[str] | None = None,
    weaknesses: list[str] | None = None,
    cheap_signals: list[str] | None = None,
    expensive_signals: list[str] | None = None,
    val_signal: str | None = None,
    sector_outlook: str = "Neutral",
    sector_rs: float = float("nan"),
    sector_threats: list[str] | None = None,
    insider_signal: str = "Neutral",
    n_buys: int = 0,
    n_sells: int = 0,
    tech_signal: str = "Neutral",
    ta=None,
    macro_context: str = "",
) -> InvestmentThesis:
    """Generate a full InvestmentThesis from all analysis inputs."""
    o_score = overall_score(fund_score, val_score, tech_score, sector_score, insider_score)
    v_label, v_rationale = verdict(o_score)

    thesis = InvestmentThesis(
        overall_score=o_score,
        verdict_label=v_label,
        verdict_rationale=v_rationale,
        macro_context=macro_context,
    )

    thesis.quality_paragraph = _quality_paragraph(
        company_name, sector, fund_score,
        strengths or [], weaknesses or [],
    )
    thesis.valuation_paragraph = _valuation_paragraph(
        val_score, val_signal,
        cheap_signals or [], expensive_signals or [],
    )
    thesis.insider_paragraph = _insider_paragraph(
        insider_score, insider_signal, n_buys, n_sells,
    )
    thesis.sector_paragraph = _sector_paragraph(
        sector, sector_score, sector_outlook, sector_rs,
    )
    thesis.technical_paragraph = _technical_paragraph(
        tech_score, tech_signal, ta,
    ) if ta is not None else (
        f"Technical score: {tech_score:.0f}/100 ({tech_signal})."
        if not math.isnan(tech_score) else ""
    )
    thesis.risk_bullets = _risk_bullets(
        weaknesses or [], expensive_signals or [],
        sector_threats or [], tech_signal, insider_signal,
    )
    return thesis
