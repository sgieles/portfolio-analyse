"""Info Hub — app documentation page."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dash import html

from dash_app.components.theme import (
    ACCENT, BLUE, BORDER, CARD, DANGER, MUTED, SUCCESS, TEXT, WARNING,
)


# ── Building blocks ────────────────────────────────────────────────────────────

def _section(title: str, color: str = ACCENT) -> html.Div:
    return html.Div([
        html.Div(className="section-bar", style={"background": color}),
        html.Span(title, style={"fontSize": "11px", "fontWeight": "700",
                                "color": color, "textTransform": "uppercase",
                                "letterSpacing": "0.08em"}),
    ], style={"display": "flex", "alignItems": "center", "gap": "8px",
              "marginBottom": "14px", "marginTop": "28px"})


def _card(children, cols: int = 1) -> html.Div:
    return html.Div(children, style={
        "background": CARD,
        "border": f"1px solid {BORDER}",
        "borderRadius": "8px",
        "padding": "16px 20px",
    })


def _grid(*children, cols: int = 2) -> html.Div:
    return html.Div(list(children), style={
        "display": "grid",
        "gridTemplateColumns": f"repeat({cols}, 1fr)",
        "gap": "12px",
    })


def _row(label: str, body: str, color: str = TEXT) -> html.Div:
    return html.Div([
        html.Span(label, style={"fontSize": "11px", "fontWeight": "700",
                                "color": MUTED, "textTransform": "uppercase",
                                "letterSpacing": "0.07em", "display": "block",
                                "marginBottom": "3px"}),
        html.Span(body, style={"fontSize": "13px", "color": color,
                               "lineHeight": "1.55"}),
    ], style={"marginBottom": "12px"})


def _badge(label: str, color: str) -> html.Span:
    return html.Span(label, style={
        "background": color, "color": "#0d1117",
        "borderRadius": "4px", "padding": "2px 7px",
        "fontSize": "10px", "fontWeight": "700",
        "marginRight": "6px",
    })


def _score_bar(label: str, pct: int, color: str) -> html.Div:
    return html.Div([
        html.Div([
            html.Span(label, style={"fontSize": "12px", "color": TEXT}),
            html.Span(f"{pct}%", style={"fontSize": "12px", "color": MUTED,
                                        "fontWeight": "600"}),
        ], style={"display": "flex", "justifyContent": "space-between",
                  "marginBottom": "4px"}),
        html.Div(html.Div(style={
            "width": f"{pct}%", "height": "100%",
            "background": color, "borderRadius": "3px",
        }), style={"height": "6px", "background": BORDER,
                   "borderRadius": "3px", "marginBottom": "10px"}),
    ])


# ── Page ──────────────────────────────────────────────────────────────────────

def info_hub_layout() -> html.Div:
    return html.Div([
        html.Div([
            html.Span("Info", className="page-title"),
            html.Span("How the app works", className="page-meta"),
        ], className="page-header"),

        html.Div([

            # ── Data ──────────────────────────────────────────────────────────
            _section("Data & Sources", ACCENT),
            _grid(
                _card([
                    _row("Market data", "Yahoo Finance (yfinance) — Adjusted Close prices. "
                         "Adjustments correct for dividends and stock splits, ensuring returns "
                         "reflect the real economic gain of holding the asset."),
                    _row("Insider trades", "SEC EDGAR Form 4 filings (US stocks only). "
                         "Covers purchases, sales, and awards by directors, officers, and >10% shareholders."),
                    _row("Fundamentals", "Yahoo Finance info API for non-US stocks; "
                         "SEC EDGAR XBRL for detailed US income statement / balance sheet data."),
                    _row("Caching", "Price history is cached locally per ticker + period. "
                         "Screener results are cached daily per universe (cache invalidates when ticker list changes)."),
                ]),
                _card([
                    _row("Periods supported", "1Y · 3Y · 5Y · 10Y · Max"),
                    _row("Benchmarks", "SPY (S&P 500) · VTI (Total US Market) · ACWI (Global)"),
                    _row("Universes", "AEX (25) · Nasdaq 100 · S&P 500 · STOXX 600"),
                    _row("Asset types", "Stocks and ETFs are auto-detected via yfinance quoteType. "
                         "Commodity futures (e.g. GC=F) are detected by the =F suffix and routed to the commodity page."),
                    _row("Currency", "All portfolio growth charts denominated in €. "
                         "Prices from yfinance are in the native currency of each exchange."),
                ]),
            ),

            # ── Portfolio metrics ──────────────────────────────────────────────
            _section("Portfolio Metrics", BLUE),
            _grid(
                _card([
                    _row("CAGR", "Compound Annual Growth Rate — the constant annual rate that "
                         "would grow the start value to the end value over the period. "
                         "Formula: (end/start)^(1/years) − 1."),
                    _row("Ann. Return", "Mean of daily returns × 252 trading days. "
                         "Simpler than CAGR; useful for comparing expected future return."),
                    _row("CAPM Return", "Risk-free rate + Beta × (market return − risk-free rate). "
                         "Represents the theoretically fair return for the portfolio's level of market risk."),
                    _row("Volatility", "Standard deviation of daily returns × √252. "
                         "Annualised measure of how much the portfolio fluctuates."),
                    _row("Sharpe Ratio", "(Ann. Return − Risk-free Rate) / Ann. Volatility. "
                         "Return per unit of total risk. >1 is good, >2 is excellent."),
                    _row("Sortino Ratio", "Same as Sharpe but the denominator uses downside deviation only "
                         "(days where return < 0). Penalises bad volatility, not good volatility."),
                ]),
                _card([
                    _row("Beta", "Covariance(portfolio, benchmark) / Variance(benchmark). "
                         "Beta = 1 means the portfolio moves in line with the market. "
                         ">1 amplifies moves; <1 dampens them."),
                    _row("Max Drawdown", "Largest peak-to-trough decline over the full period. "
                         "Measures the worst loss an investor who bought at the top would have suffered."),
                    _row("VaR 95%", "Value at Risk — the daily loss exceeded only 5% of the time, "
                         "using the historical distribution of returns. Not a worst-case guarantee."),
                    _row("CVaR / ES", "Conditional VaR (Expected Shortfall) — the average loss "
                         "on the worst 5% of days. More conservative than VaR; used in risk management."),
                    _row("Health Score", "Composite 0–100 score combining CAGR, Sharpe, max drawdown, "
                         "volatility, and diversification with fixed weights. ≥60 = healthy, 35–59 = moderate, <35 = weak."),
                    _row("Diversification Score", "Ratio of the weighted-average individual volatility "
                         "to the portfolio volatility. Higher = assets are less correlated = better diversified."),
                ]),
            ),

            # ── Optimisation ──────────────────────────────────────────────────
            _section("Portfolio Optimisation", SUCCESS),
            _card([
                html.Div("Optimisation uses PyPortfolioOpt with the efficient frontier framework. "
                         "All strategies use historical mean returns and the sample covariance matrix "
                         "of daily returns. Weights are constrained to [0%, 100%] per asset (long-only).",
                         style={"fontSize": "13px", "color": MUTED, "marginBottom": "14px",
                                "lineHeight": "1.6"}),
                _grid(
                    html.Div([
                        html.Div([_badge("Max Sharpe", ACCENT)],
                                 style={"marginBottom": "8px"}),
                        html.Div("Finds the portfolio on the efficient frontier with the highest "
                                 "Sharpe ratio (tangency portfolio). Best choice when maximising "
                                 "risk-adjusted return.",
                                 style={"fontSize": "13px", "color": TEXT, "lineHeight": "1.55"}),
                    ]),
                    html.Div([
                        html.Div([_badge("Min Variance", BLUE)],
                                 style={"marginBottom": "8px"}),
                        html.Div("Minimises total portfolio variance regardless of return. "
                                 "Useful when capital preservation matters more than return maximisation.",
                                 style={"fontSize": "13px", "color": TEXT, "lineHeight": "1.55"}),
                    ]),
                    html.Div([
                        html.Div([_badge("Black-Litterman", SUCCESS)],
                                 style={"marginBottom": "8px"}),
                        html.Div("Blends CAPM market equilibrium weights (π = δΣw) with the "
                                 "historical return signal as an investor view. Produces more "
                                 "stable, diversified weights than pure Max Sharpe.",
                                 style={"fontSize": "13px", "color": TEXT, "lineHeight": "1.55"}),
                    ]),
                    cols=3,
                ),
            ]),

            # ── Stock scoring ──────────────────────────────────────────────────
            _section("Research Hub — Stock Scoring", WARNING),
            _grid(
                _card([
                    html.Div("Investment Thesis Score (0–100)",
                             style={"fontSize": "13px", "fontWeight": "700",
                                    "color": TEXT, "marginBottom": "12px"}),
                    _score_bar("Fundamentals",  30, ACCENT),
                    _score_bar("Valuation",     25, BLUE),
                    _score_bar("Technical",     20, SUCCESS),
                    _score_bar("Sector",        15, WARNING),
                    _score_bar("Insider",       10, DANGER),
                    html.Div("Signal: ≥75 Strong Buy · ≥60 Buy · ≥45 Hold · ≥30 Underperform · <30 Avoid",
                             style={"fontSize": "11px", "color": MUTED,
                                    "marginTop": "4px", "lineHeight": "1.6"}),
                ]),
                _card([
                    _row("Fundamental Score", "Covers profitability (ROE, ROA, margins), "
                         "growth (revenue/earnings YoY), and balance sheet health "
                         "(debt/equity, current ratio, interest coverage). Each sub-score "
                         "is 0–100; combined with equal weights."),
                    _row("Valuation Score", "Compares P/E, P/B, EV/EBITDA, and P/FCF to "
                         "sector medians. A DCF model (5-year projection, terminal growth 2.5%) "
                         "provides an intrinsic value estimate. Undervalued relative to peers = high score."),
                    _row("Technical Score", "RSI-14 (momentum), MA50/MA200 cross (trend), "
                         "MACD signal, 52-week range position, and 1/3/6-month momentum. "
                         "Each indicator scored 0–100 and averaged."),
                    _row("Insider Score", "Net buy/sell pressure from SEC Form 4 trades "
                         "in the last 180 days, weighted by role (CEO > Director > Officer) "
                         "and decayed exponentially with a 45-day half-life: "
                         "decay = e^(−ln2 × days / 45)."),
                ]),
            ),

            # ── ETF & Commodity ───────────────────────────────────────────────
            _section("ETF & Commodity Scoring", DANGER),
            _grid(
                _card([
                    html.Div("ETF Score (0–100)",
                             style={"fontSize": "13px", "fontWeight": "700",
                                    "color": TEXT, "marginBottom": "12px"}),
                    _score_bar("Cost efficiency",   30, ACCENT),
                    _score_bar("Diversification",   30, BLUE),
                    _score_bar("Performance",       25, SUCCESS),
                    _score_bar("Risk",              15, WARNING),
                    html.Div("Cost: expense ratio vs category average. "
                             "Diversification: number of holdings + concentration of top 10. "
                             "Performance: 1Y/3Y/5Y return vs benchmark. "
                             "Risk: volatility + max drawdown.",
                             style={"fontSize": "11px", "color": MUTED,
                                    "marginTop": "8px", "lineHeight": "1.6"}),
                ]),
                _card([
                    html.Div("Commodity Score (0–100)",
                             style={"fontSize": "13px", "fontWeight": "700",
                                    "color": TEXT, "marginBottom": "12px"}),
                    _score_bar("Momentum",  40, ACCENT),
                    _score_bar("Trend",     35, BLUE),
                    _score_bar("Volatility", 25, SUCCESS),
                    html.Div("Momentum: weighted 1M/3M/6M/1Y returns. "
                             "Trend: position vs MA50 / MA200 and golden cross (MA50 > MA200). "
                             "Volatility: annualised vol vs historical range — lower vol scores higher. "
                             "Seasonality chart shows average monthly return by calendar month.",
                             style={"fontSize": "11px", "color": MUTED,
                                    "marginTop": "8px", "lineHeight": "1.6"}),
                ]),
            ),

            html.Div(style={"height": "40px"}),  # bottom padding

        ], style={"maxWidth": "1000px"}),
    ], className="main", style={"padding": "24px 32px"})
