"""Sector intelligence engine — pure analytics, no I/O.

Computes momentum, relative strength, sector score, SWOT and PESTLE
from ETF price data and screener cache fundamentals.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import pandas as pd

from research.data.sector_data import (
    SECTOR_ETF_MAP, momentum, relative_strength,
)


# ── PESTLE templates (static, per sector) ─────────────────────────────────────
# Each entry is a list of bullet strings per category.

_PESTLE: dict[str, dict[str, list[str]]] = {
    "Technology": {
        "Political":     ["Data privacy regulation (GDPR, AI Act, CCPA)", "Export controls on semiconductors and AI chips"],
        "Economic":      ["Interest rate sensitivity: high-multiple stocks hit hardest in rate rises", "Enterprise IT budgets tied to corporate profitability cycles"],
        "Social":        ["Digital transformation and cloud adoption accelerating across all industries", "AI and automation reshaping knowledge work"],
        "Technological": ["Generative AI creating both disruption and new revenue streams", "Semiconductor supply chain complexity and capacity constraints"],
        "Legal":         ["Antitrust scrutiny of large platform companies (EU, US)", "IP and patent disputes across hardware and software"],
        "Environmental": ["Data center energy and water consumption under regulatory pressure", "E-waste and device lifecycle regulations tightening"],
    },
    "Healthcare": {
        "Political":     ["Drug pricing legislation risk in the US (IRA, Medicare negotiation)", "Regulatory pathway changes at FDA / EMA"],
        "Economic":      ["Defensive spending: healthcare demand relatively inelastic to recessions", "Reimbursement pressure from payers and government programs"],
        "Social":        ["Ageing demographics in developed markets driving long-term demand", "GLP-1 drug revolution reshaping obesity and metabolic care"],
        "Technological": ["AI-accelerated drug discovery and clinical trials", "Precision medicine and gene therapy entering mainstream"],
        "Legal":         ["Patent cliff exposure for many large pharma companies", "Liability exposure in medical devices and diagnostics"],
        "Environmental": ["Pharmaceutical manufacturing pollution regulations tightening", "Single-use plastics in medical devices under scrutiny"],
    },
    "Financial Services": {
        "Political":     ["Basel IV capital requirements increasing compliance costs", "Political pressure on bank profits and fee structures"],
        "Economic":      ["Net interest margin expansion in high-rate environments", "Credit quality deterioration risk in economic slowdowns"],
        "Social":        ["Fintech disruption eroding retail banking market share", "Growing demand for ESG-aligned investment products"],
        "Technological": ["Core banking modernisation — costly, multi-year transformation programmes", "Cybersecurity and fraud prevention: rising cost of breaches"],
        "Legal":         ["AML/KYC compliance costs rising globally", "Consumer protection rules limiting cross-sell revenue"],
        "Environmental": ["Climate risk integration into loan books required by regulators", "Pressure to exit fossil fuel financing"],
    },
    "Energy": {
        "Political":     ["OPEC+ production decisions heavily influencing oil prices", "Energy security and domestic production incentives in US/Europe"],
        "Economic":      ["Oil and gas prices tied to global growth and demand cycles", "Capital discipline improving FCF generation vs prior cycles"],
        "Social":        ["Energy transition public sentiment accelerating divestment pressure", "Energy affordability concerns driving political backlash on transition"],
        "Technological": ["Shale and LNG technology maintaining US cost competitiveness", "Carbon capture and hydrogen still pre-commercial at scale"],
        "Legal":         ["Windfall profit taxes in multiple jurisdictions after 2022 price spike", "Stricter methane emissions regulations"],
        "Environmental": ["Physical climate risk to infrastructure (storms, flooding, drought)", "Stranded asset risk as energy transition accelerates"],
    },
    "Consumer Cyclical": {
        "Political":     ["Trade tariffs and import duties affecting supply chain costs", "Consumer protection regulations on advertising and data use"],
        "Economic":      ["High correlation to consumer confidence and discretionary income", "Interest rates affect big-ticket spending (autos, home goods)"],
        "Social":        ["E-commerce structural shift reshaping retail formats", "Younger consumers prioritising experiences over goods"],
        "Technological": ["Supply chain digitalisation reducing inventory risk", "Personalisation and AI driving conversion in e-commerce"],
        "Legal":         ["Product liability and consumer safety standards increasing", "Gig economy classification disputes in delivery and retail"],
        "Environmental": ["Sustainable packaging mandates adding cost", "Fast fashion under regulatory and reputational pressure"],
    },
    "Consumer Defensive": {
        "Political":     ["Food safety regulations and labelling requirements tightening", "Agricultural subsidies and trade policy affect input costs"],
        "Economic":      ["Inflation pass-through ability differentiates strong vs weak brands", "Volume elasticity: consumers trade down in severe recessions"],
        "Social":        ["Health and wellness trends shifting demand toward functional foods", "Private label growth in grocery squeezing branded players"],
        "Technological": ["Direct-to-consumer channels reducing retailer dependence", "Cold chain and logistics technology improving margins"],
        "Legal":         ["Advertising restrictions on unhealthy food products (sugar, salt)", "Packaging and single-use plastic legislation"],
        "Environmental": ["Agricultural water use and soil depletion scrutiny", "Scope 3 emissions (agriculture) difficult to reduce quickly"],
    },
    "Industrials": {
        "Political":     ["Defence spending increases following geopolitical tensions", "Infrastructure bills (US IRA, EU Green Deal) creating multi-year order backlogs"],
        "Economic":      ["Capital goods spending tied to corporate capex and GDP growth", "Long project cycles provide revenue visibility but lag the cycle"],
        "Social":        ["Reshoring and near-shoring trends creating domestic manufacturing demand", "Labour shortages in skilled trades pressuring margins"],
        "Technological": ["Industrial IoT and robotics driving productivity gains", "Electrification of transport and infrastructure drives new equipment demand"],
        "Legal":         ["Environmental permitting delays affecting large infrastructure projects", "Export controls on advanced manufacturing equipment"],
        "Environmental": ["Industrial decarbonisation: energy-intensive players face transition capex", "Circular economy regulations affect product design and end-of-life"],
    },
    "Basic Materials": {
        "Political":     ["Critical minerals supply chains and geopolitical risk (lithium, rare earths)", "Export bans by producing countries create supply shocks"],
        "Economic":      ["Commodity prices highly cyclical and driven by China demand", "Energy input costs major operating margin lever"],
        "Social":        ["Community and indigenous land rights affecting mining permits", "ESG scrutiny of mining practices increasing"],
        "Technological": ["Electric vehicle battery demand driving structural growth in lithium, nickel, cobalt", "Green steel and green aluminium technologies emerging"],
        "Legal":         ["Environmental impact assessments creating long permit timelines", "Mine closure and rehabilitation liabilities growing"],
        "Environmental": ["Water usage and tailings management under stricter regulation", "Carbon border adjustment mechanism (CBAM) in EU affects imports"],
    },
    "Real Estate": {
        "Political":     ["Rent control and zoning regulations affecting residential property economics", "Tax treatment of REITs varies by jurisdiction"],
        "Economic":      ["High sensitivity to interest rates: rising rates compress cap rates and valuations", "Commercial real estate (office) facing structural demand shifts post-COVID"],
        "Social":        ["Remote work reducing office demand; data centres and logistics growing", "Urbanisation trends supporting residential in gateway cities"],
        "Technological": ["Proptech and smart building technology improving operating efficiency", "Data centres and logistics REITs benefiting from digital economy growth"],
        "Legal":         ["ESG disclosure on building energy ratings increasingly mandatory", "Tenant protection laws limiting evictions and rent increases"],
        "Environmental": ["Building retrofitting required to meet net-zero targets", "Flood and climate risk increasingly priced into property valuations"],
    },
    "Utilities": {
        "Political":     ["Regulated returns set by national/regional regulators (ofgem, FERC)", "Energy transition policy creates significant capex requirements"],
        "Economic":      ["Defensive sector: stable cash flows but rate-sensitive valuations", "Inflation pass-through depends on regulatory regime and contract structure"],
        "Social":        ["Energy poverty concerns create political limits on price increases", "Public support for renewable energy transition"],
        "Technological": ["Renewables capex driving fleet transformation: solar, wind, storage", "Grid modernisation and smart meters require significant investment"],
        "Legal":         ["Environmental permits for new plant construction increasingly contested", "Liability exposure from wildfires (California model)"],
        "Environmental": ["Physical climate risk: extreme weather events affecting grid reliability", "Water scarcity affecting thermal power plant cooling requirements"],
    },
    "Communication Services": {
        "Political":     ["Content moderation regulation (DSA in EU, Section 230 debate in US)", "Spectrum auctions and telecom licensing create periodic large capex needs"],
        "Economic":      ["Advertising revenue highly cyclical: falls sharply in recessions", "Subscription models provide more stable revenue than pure advertising"],
        "Social":        ["Streaming and social media competing for finite attention", "Mental health concerns around social media creating regulatory pressure"],
        "Technological": ["Generative AI threatening search advertising and content creation economics", "5G and fibre rollout as long-term growth capex"],
        "Legal":         ["Privacy litigation and data handling class actions increasing", "Antitrust cases against large platform companies (Google, Meta)"],
        "Environmental": ["Video streaming and gaming driving significant data centre energy use", "E-waste from consumer devices"],
    },
}

_DEFAULT_PESTLE: dict[str, list[str]] = {
    "Political":     ["Regulatory environment creating both risk and opportunity"],
    "Economic":      ["Sector performance influenced by macroeconomic cycle"],
    "Social":        ["Demographic and consumer behaviour trends shaping demand"],
    "Technological": ["Digital transformation and automation reshaping competitive dynamics"],
    "Legal":         ["Compliance requirements increasing operating costs"],
    "Environmental": ["ESG pressure and climate risk integration growing in importance"],
}


# ── Dataclasses ────────────────────────────────────────────────────────────────

@dataclass
class SectorIntelligence:
    sector: str
    etf: str                          # representative ETF ticker
    momentum_1m: float = float("nan")
    momentum_3m: float = float("nan")
    momentum_6m: float = float("nan")
    momentum_12m: float = float("nan")
    relative_strength_spy: float = float("nan")   # excess return vs SPY (12m)
    relative_strength_world: float = float("nan") # excess return vs ACWI (12m)
    # Sector fundamentals aggregated from screener cache
    n_peers: int = 0
    avg_pe: float = float("nan")
    avg_fwd_pe: float = float("nan")
    avg_rev_growth: float = float("nan")
    avg_roe: float = float("nan")
    avg_div_yield: float = float("nan")
    avg_overall_score: float = float("nan")
    avg_fund_score: float = float("nan")
    avg_val_score: float = float("nan")
    avg_trend_score: float = float("nan")
    # Derived
    sector_score: float = 50.0        # 0-100
    outlook: str = "Neutral"          # "Bullish" / "Neutral" / "Bearish"
    swot: dict[str, list[str]] = field(default_factory=dict)
    pestle: dict[str, list[str]] = field(default_factory=dict)


# ── Engine ────────────────────────────────────────────────────────────────────

def analyze_sector(
    sector: str,
    sector_prices: dict[str, pd.Series],
    screener_rows: list[dict] | None = None,
) -> SectorIntelligence:
    """Compute SectorIntelligence for *sector*.

    Args:
        sector: Sector name matching SECTOR_ETF_MAP keys (e.g. "Technology").
        sector_prices: {etf_ticker: adj-close Series} from sector_data.fetch_sector_prices().
        screener_rows: Optional list of raw screener row dicts (from screener_cache).

    Returns:
        SectorIntelligence dataclass.
    """
    from research.data.sector_data import aggregate_sector_fundamentals

    etf = SECTOR_ETF_MAP.get(sector, "SPY")
    intel = SectorIntelligence(sector=sector, etf=etf)

    # ── Momentum ────────────────────────────────────────────────────────────────
    series = sector_prices.get(etf)
    spy    = sector_prices.get("SPY")
    world  = sector_prices.get("ACWI")

    if series is not None and not series.empty:
        intel.momentum_1m  = momentum(series, 1)
        intel.momentum_3m  = momentum(series, 3)
        intel.momentum_6m  = momentum(series, 6)
        intel.momentum_12m = momentum(series, 12)

    if series is not None and spy is not None:
        intel.relative_strength_spy = relative_strength(series, spy, 12)

    if series is not None and world is not None:
        intel.relative_strength_world = relative_strength(series, world, 12)

    # ── Sector fundamentals ────────────────────────────────────────────────────
    if screener_rows:
        kpis = aggregate_sector_fundamentals(screener_rows, sector)
        intel.n_peers           = int(kpis.get("n_peers", 0))
        intel.avg_pe            = kpis.get("avg_pe", float("nan"))
        intel.avg_fwd_pe        = kpis.get("avg_fwd_pe", float("nan"))
        intel.avg_rev_growth    = kpis.get("avg_rev_growth", float("nan"))
        intel.avg_roe           = kpis.get("avg_roe", float("nan"))
        intel.avg_div_yield     = kpis.get("avg_div_yield", float("nan"))
        intel.avg_overall_score = kpis.get("avg_overall_score", float("nan"))
        intel.avg_fund_score    = kpis.get("avg_fund_score", float("nan"))
        intel.avg_val_score     = kpis.get("avg_val_score", float("nan"))
        intel.avg_trend_score   = kpis.get("avg_trend_score", float("nan"))

    # ── Sector score (0-100) ───────────────────────────────────────────────────
    intel.sector_score = _compute_sector_score(intel)

    # ── Outlook ───────────────────────────────────────────────────────────────
    intel.outlook = _determine_outlook(intel)

    # ── SWOT ──────────────────────────────────────────────────────────────────
    intel.swot = _build_swot(intel)

    # ── PESTLE ────────────────────────────────────────────────────────────────
    intel.pestle = _PESTLE.get(sector, _DEFAULT_PESTLE)

    return intel


def _safe(v: float, default: float = 50.0) -> float:
    return default if math.isnan(v) else v


def _compute_sector_score(i: SectorIntelligence) -> float:
    """Weighted composite sector score (0-100).

    Components:
    - Momentum (12m vs SPY): 35%
    - Trend score (from screener): 25%
    - Fundamental score (from screener): 25%
    - Valuation score (from screener): 15%
    """
    scores: list[tuple[float, float]] = []

    # Momentum component
    rs = i.relative_strength_spy
    if not math.isnan(rs):
        # Map [-0.30, +0.30] → [0, 100]
        mom_score = 50 + (rs / 0.30) * 50
        mom_score = max(0.0, min(100.0, mom_score))
        scores.append((mom_score, 0.35))

    if not math.isnan(i.avg_trend_score):
        scores.append((_safe(i.avg_trend_score), 0.25))

    if not math.isnan(i.avg_fund_score):
        scores.append((_safe(i.avg_fund_score), 0.25))

    if not math.isnan(i.avg_val_score):
        scores.append((_safe(i.avg_val_score), 0.15))

    if not scores:
        return 50.0

    total_weight = sum(w for _, w in scores)
    weighted_sum = sum(s * w for s, w in scores)
    return weighted_sum / total_weight


def _determine_outlook(i: SectorIntelligence) -> str:
    score = i.sector_score
    rs    = i.relative_strength_spy

    # Require strong momentum alignment for conviction
    if score >= 62:
        if not math.isnan(rs) and rs < -0.05:
            return "Neutral"   # good score but underperforming market
        return "Bullish"
    if score <= 38:
        if not math.isnan(rs) and rs > 0.05:
            return "Neutral"   # low score but outperforming market
        return "Bearish"
    return "Neutral"


def _build_swot(i: SectorIntelligence) -> dict[str, list[str]]:
    strengths, weaknesses, opportunities, threats = [], [], [], []

    # Momentum signals
    mom_12 = i.momentum_12m
    if not math.isnan(mom_12):
        if mom_12 > 0.15:
            strengths.append(f"Strong 12-month price momentum (+{mom_12*100:.0f}%)")
        elif mom_12 < -0.10:
            weaknesses.append(f"Negative 12-month price performance ({mom_12*100:.0f}%)")

    rs = i.relative_strength_spy
    if not math.isnan(rs):
        if rs > 0.05:
            strengths.append(f"Outperforming the broad market by {rs*100:.0f}pp (12m)")
        elif rs < -0.05:
            weaknesses.append(f"Underperforming S&P 500 by {abs(rs)*100:.0f}pp (12m)")

    # Fundamental signals
    rg = i.avg_rev_growth
    if not math.isnan(rg):
        if rg > 0.10:
            strengths.append(f"Median revenue growth of {rg*100:.0f}% signals strong sector demand")
        elif rg < 0.02:
            weaknesses.append(f"Low median revenue growth ({rg*100:.0f}%) reflects slowing demand")

    roe = i.avg_roe
    if not math.isnan(roe):
        if roe > 0.20:
            strengths.append(f"High median ROE ({roe*100:.0f}%) reflects capital-efficient businesses")
        elif roe < 0.05:
            weaknesses.append(f"Low median ROE ({roe*100:.0f}%) suggests poor capital efficiency")

    # Valuation signals
    pe = i.avg_pe
    if not math.isnan(pe) and pe > 0:
        if pe < 15:
            opportunities.append(f"Sector trades at a low median P/E of {pe:.0f}×, historically attractive")
        elif pe > 35:
            threats.append(f"Elevated median P/E of {pe:.0f}× leaves little room for disappointment")

    vs = i.avg_val_score
    if not math.isnan(vs):
        if vs > 65:
            opportunities.append("Valuation scores above sector average — potential for re-rating")
        elif vs < 35:
            threats.append("Stretched valuations relative to fundamentals increase downside risk")

    # Score-based
    if i.avg_fund_score > 65 and not math.isnan(i.avg_fund_score):
        strengths.append("Sector peers score strongly on fundamentals (growth + profitability + balance sheet)")
    if i.avg_fund_score < 35 and not math.isnan(i.avg_fund_score):
        weaknesses.append("Sector peers score poorly on fundamentals on average")

    # Generic fallbacks so each SWOT quadrant always has at least one item
    if not strengths:
        strengths.append("Established sector with resilient long-term demand drivers")
    if not weaknesses:
        weaknesses.append("Performance may be constrained by macroeconomic cycle sensitivity")
    if not opportunities:
        opportunities.append("Secular trends and structural tailwinds may reward patient investors")
    if not threats:
        threats.append("Global macro uncertainty and interest rate volatility remain key risks")

    return {
        "Strengths":     strengths,
        "Weaknesses":    weaknesses,
        "Opportunities": opportunities,
        "Threats":       threats,
    }
