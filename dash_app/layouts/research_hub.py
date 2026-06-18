"""Research Hub layout + callbacks."""

from __future__ import annotations

import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import plotly.graph_objects as go
from dash import Input, Output, State, callback, dcc, html, no_update

from dash_app.components.theme import (
    ACCENT, BLUE, BORDER, CARD, DANGER, DIM, MUTED,
    PLOTLY, GRID, SUCCESS, TEXT, WARNING,
)

# ── Formatting ─────────────────────────────────────────────────────────────────

def _p(v):
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return "—"
    return f"{v * 100:.1f}%"


def _bn(v):
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return "—"
    if abs(v) >= 1e9:
        return f"${v / 1e9:.1f}B"
    if abs(v) >= 1e6:
        return f"${v / 1e6:.1f}M"
    return f"${v:,.0f}"


def _n(v, d=2):
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return "—"
    return f"{v:.{d}f}"


def _score_badge(score) -> html.Span:
    if score is None:
        return html.Span("—")
    score = float(score)
    cls   = "score-high" if score >= 65 else "score-mid" if score >= 40 else "score-low"
    return html.Span(f"{score:.0f}", className=f"score-badge {cls}")


# ── Research Hub main layout ───────────────────────────────────────────────────

def research_hub_layout() -> html.Div:
    return html.Div([
        html.Div([
            html.Div([
                html.Span("Research Hub", className="page-title"),
                html.Span("SEC EDGAR · yfinance", className="page-meta"),
            ], className="page-header"),
            dcc.Tabs(id="research-tabs", value="tab-screener", className="main-tabs", children=[
                dcc.Tab(label="Screener",        value="tab-screener",  className="tab"),
                dcc.Tab(label="Watchlists",      value="tab-watchlists",className="tab"),
                dcc.Tab(label="Company Look-up", value="tab-company",   className="tab"),
                dcc.Tab(label="Sector Intel",    value="tab-sector",    className="tab"),
            ]),
            html.Div(id="research-tab-content"),
        ], className="main"),
    ], className="app-body")


# ── Screener tab ───────────────────────────────────────────────────────────────

def build_screener_tab() -> html.Div:
    from research.data.universe import UNIVERSES
    universes = list(UNIVERSES.keys()) if hasattr(UNIVERSES, "keys") else ["S&P 500", "Nasdaq 100", "STOXX 600", "AEX"]
    return html.Div([
        html.Div([
            dcc.Dropdown(
                id="rh-universe-select",
                options=[{"label": u, "value": u} for u in universes],
                value=universes[0] if universes else "S&P 500",
                clearable=False, className="dash-dropdown",
                style={"width": "200px"},
            ),
            html.Button("▶ Run Screener", id="rh-screen-btn", className="sb-btn primary",
                        n_clicks=0, style={"width": "auto", "padding": "8px 18px"}),
            html.Span(id="rh-screener-status", style={"fontSize": "11px", "color": MUTED, "marginLeft": "10px"}),
        ], className="screener-controls"),
        dcc.Loading(
            html.Div(id="rh-screener-results"),
            type="circle", color=ACCENT,
        ),
    ])


# ── Watchlists tab ─────────────────────────────────────────────────────────────

def build_watchlists_tab() -> html.Div:
    from research.data.watchlist_store import list_watchlists
    existing = list_watchlists()

    select_opts = [{"label": w, "value": w} for w in existing]

    return html.Div([
        html.Div([
            html.Div("Watchlists", style={"fontSize": "17px", "fontWeight": 800, "color": TEXT, "marginBottom": "14px"}),
            html.Div([
                dcc.Input(id="wl-new-name", type="text", placeholder="My Watchlist",
                          style={"flex": 1, "background": "#1c2128", "border": f"1px solid {BORDER}",
                                 "borderRadius": "6px", "color": TEXT, "padding": "7px 10px",
                                 "fontSize": "12px", "fontFamily": "inherit", "outline": "none"}),
                html.Button("Create", id="wl-create-btn", className="sb-btn primary",
                            n_clicks=0, style={"width": "auto", "padding": "7px 16px"}),
            ], style={"display": "flex", "gap": "8px", "marginBottom": "14px"}),

            dcc.Dropdown(id="wl-select", options=select_opts,
                         value=existing[0] if existing else None,
                         placeholder="Open watchlist…",
                         clearable=False, className="dash-dropdown",
                         style={"marginBottom": "12px"}),

            html.Div(id="wl-content"),
        ]),
    ], style={"padding": "4px 0"})


# ── Company Look-up tab ────────────────────────────────────────────────────────

def build_company_tab() -> html.Div:
    from utils.ticker_suggestions import ticker_options
    return html.Div([
        html.Div([
            dcc.Dropdown(
                id="rh-company-ticker",
                options=ticker_options(),
                placeholder="Search ticker or company…",
                className="dash-dropdown",
                clearable=True, searchable=True,
                style={"flex": "1", "maxWidth": "360px"},
            ),
            html.Button("Look up", id="rh-company-btn", className="sb-btn primary",
                        n_clicks=0, style={"width": "auto", "padding": "8px 20px"}),
        ], style={"display": "flex", "gap": "8px", "marginBottom": "16px", "alignItems": "center"}),
        dcc.Loading(
            html.Div(id="rh-company-content"),
            type="circle", color=ACCENT,
        ),
    ])


# ── Sector Intelligence tab ────────────────────────────────────────────────────

_SECTORS = [
    "Technology", "Financial Services", "Healthcare", "Consumer Cyclical",
    "Consumer Defensive", "Industrials", "Energy", "Basic Materials",
    "Communication Services", "Real Estate", "Utilities",
]


def build_sector_tab() -> html.Div:
    return html.Div([
        html.Div([
            dcc.Dropdown(id="rh-sector-select",
                         options=[{"label": s, "value": s} for s in _SECTORS],
                         value="Technology",
                         clearable=False, className="dash-dropdown",
                         style={"width": "220px"}),
            html.Button("Analyse", id="rh-sector-btn", className="sb-btn primary",
                        n_clicks=0, style={"width": "auto", "padding": "8px 18px"}),
        ], style={"display": "flex", "gap": "8px", "marginBottom": "16px", "alignItems": "flex-end"}),
        dcc.Loading(html.Div(id="rh-sector-content"), type="circle", color=ACCENT),
    ])


# ── Company detail renderer ────────────────────────────────────────────────────

def _render_company(ticker: str) -> html.Div:
    from research.data.fundamentals_fetcher import fetch_fundamentals, fetch_profile, fetch_quarterly
    from research.analytics.fundamental_scorer import score_fundamentals
    from research.cache.screener_cache import load_screener_rows
    from research.data.etf_fetcher import is_etf
    from research.data.commodity_fetcher import is_commodity
    import yfinance as yf

    # Commodity detection (=F suffix) — no yfinance info needed
    if is_commodity(ticker):
        from dash_app.layouts.commodity_analysis import render_commodity
        return render_commodity(ticker)

    info = yf.Ticker(ticker).info or {}

    profile  = fetch_profile(ticker)
    funds    = fetch_fundamentals(ticker, n_years=10)
    quarters = fetch_quarterly(ticker, n_quarters=8)

    if is_etf(info):
        return _render_etf(ticker, info, profile)

    # Company header
    header = html.Div([
        html.Div([
            html.Span(profile.name or ticker, className="company-name"),
            html.Span(ticker, className="company-ticker"),
        ]),
        html.Div(f"{profile.sector or '—'} · {profile.industry or '—'} · {profile.country or '—'} · {profile.exchange or '—'}",
                 className="company-meta"),
    ], className="company-header")

    if not funds:
        return html.Div([header, html.Div(f"No fundamental data for {ticker}.", className="pf-empty")])

    # Collect sector peers
    sector_scores: list[float] = []
    if profile.sector:
        for u in ("S&P 500", "Nasdaq 100", "STOXX 600", "AEX"):
            for row in (load_screener_rows(u) or []):
                if row.get("sector") == profile.sector:
                    v = row.get("fundamental_score")
                    if v is not None and not math.isnan(float(v)):
                        sector_scores.append(float(v))

    analysis = score_fundamentals(ticker, funds, sector_scores or None)

    # Annual financials table
    fin_rows = []
    for f in funds[:6]:
        fin_rows.append(html.Tr([
            html.Td(f.fiscal_year, className="ticker-cell"),
            html.Td(_bn(f.revenue),           className="num"),
            html.Td(_bn(f.gross_profit),      className="num"),
            html.Td(_bn(f.net_income),        className="num"),
            html.Td(f"${f.eps_diluted:.2f}" if not math.isnan(f.eps_diluted) else "—", className="num"),
            html.Td(_p(f.gross_margin),       className="num"),
            html.Td(_p(f.operating_margin),   className="num"),
            html.Td(_p(f.net_margin),         className="num"),
            html.Td(_p(f.return_on_equity),   className="num"),
            html.Td(f"{f.debt_to_equity:.2f}" if not math.isnan(f.debt_to_equity) else "—", className="num"),
        ]))

    fin_table = html.Div([
        html.Div([html.Span("Annual Financials", className="chart-title")], className="chart-header"),
        html.Div(html.Table([
            html.Thead(html.Tr([
                html.Th("FY"), html.Th("Revenue"), html.Th("Gross Profit"),
                html.Th("Net Income"), html.Th("EPS"), html.Th("Gross Margin"),
                html.Th("Op. Margin"), html.Th("Net Margin"), html.Th("ROE"), html.Th("D/E"),
            ])),
            html.Tbody(fin_rows),
        ], className="data-table"), style={"overflowX": "auto"}),
    ], className="chart-panel")

    # Score breakdown
    score_cards = html.Div([
        _score_card("Fundamental Score", analysis.fundamental_score if analysis else None, "composite quality score"),
        _score_card("Profitability",     analysis.profitability_score if analysis else None),
        _score_card("Growth",            analysis.growth_score if analysis else None),
        _score_card("Balance Sheet",     analysis.balance_sheet_score if analysis else None),
    ], style={"display": "grid", "gridTemplateColumns": "repeat(4,1fr)", "gap": "10px", "marginBottom": "14px"})

    # Company tabs
    company_tabs = dcc.Tabs(id="company-tabs", value="tab-fund", className="inner-tabs", children=[
        dcc.Tab(label="Fundamentals",     value="tab-fund",  className="tab"),
        dcc.Tab(label="Valuation",        value="tab-val",   className="tab"),
        dcc.Tab(label="Insider Activity", value="tab-ins",   className="tab"),
        dcc.Tab(label="Research Report",  value="tab-rep",   className="tab"),
    ])

    company_content = dcc.Loading(
        html.Div(id="company-tab-content"),
        type="circle", color=BLUE,
    )

    return html.Div([
        header,
        score_cards,
        fin_table,
        html.Hr(style={"border": "none", "borderTop": f"1px solid {BORDER}", "margin": "14px 0"}),
        html.Div([
            html.Div(ticker, id="company-ticker-store", style={"display": "none"}),
        ]),
        company_tabs,
        company_content,
    ])


def _render_etf(ticker: str, info: dict, profile) -> html.Div:
    from research.data.etf_fetcher import fetch_etf_profile, fetch_etf_price_history
    from research.analytics.etf_scorer import score_etf

    etf_profile   = fetch_etf_profile(ticker)
    price_hist    = fetch_etf_price_history(ticker, "5y")
    bench_hist    = fetch_etf_price_history("SPY",  "5y")
    analysis      = score_etf(ticker, etf_profile, price_hist, bench_hist)

    fund_family = etf_profile.fund_family or info.get("fundFamily", "—")
    er_str = f"TER {etf_profile.expense_ratio*100:.2f}%" if math.isfinite(etf_profile.expense_ratio) else ""

    def _sig_color(s: str) -> str:
        return {
            "Excellent": SUCCESS, "Good": BLUE, "Neutral": MUTED,
            "Weak": WARNING, "Poor": DANGER,
        }.get(s, TEXT)

    score_row = html.Div([
        _score_card("ETF Score",    analysis.etf_score,            analysis.signal),
        _score_card("Cost",         analysis.cost_score,           er_str),
        _score_card("Diversif.",    analysis.diversification_score, f"{etf_profile.n_holdings} holdings"),
        _score_card("Performance",  analysis.performance_score,    f"1Y {_p(analysis.return_1y)}"),
        _score_card("Risk",         analysis.risk_score,           f"DD {_p(analysis.max_drawdown)}"),
    ], style={"display": "grid", "gridTemplateColumns": "repeat(5,1fr)",
              "gap": "10px", "marginBottom": "14px"})

    # Return strip
    ret_row = html.Div([
        html.Div([
            html.Div(lbl, className="kpi-label"),
            html.Div(_p(val), className="kpi-value",
                     style={"color": SUCCESS if val and val > 0 else DANGER}),
        ], className="kpi-card")
        for lbl, val in [
            ("1Y Return", analysis.return_1y),
            ("3Y Ann.",   analysis.return_3y_ann),
            ("5Y Ann.",   analysis.return_5y_ann),
            ("Volatility", analysis.volatility_1y),
            ("Sharpe",    analysis.sharpe_1y),
            ("Max DD",    analysis.max_drawdown),
        ]
    ], style={"display": "grid", "gridTemplateColumns": "repeat(6,1fr)",
              "gap": "10px", "marginBottom": "14px"})

    # Signals
    def _bullets(items: list[str]) -> html.Ul | html.Div:
        if not items:
            return html.Div("—", style={"color": MUTED})
        return html.Ul([
            html.Li(i, style={"color": TEXT, "fontSize": "13px", "marginBottom": "5px"})
            for i in items
        ], style={"paddingLeft": "18px", "margin": "0"})

    sw_panel = html.Div([
        html.Div([html.Span("Signals", className="chart-title")], className="chart-header"),
        html.Div([
            html.Div([
                html.Div("Strengths", style={"color": SUCCESS, "fontWeight": "600",
                                             "fontSize": "12px", "marginBottom": "6px"}),
                _bullets(analysis.strengths),
            ], style={"flex": "1"}),
            html.Div([
                html.Div("Weaknesses", style={"color": DANGER, "fontWeight": "600",
                                              "fontSize": "12px", "marginBottom": "6px"}),
                _bullets(analysis.weaknesses),
            ], style={"flex": "1"}),
        ], style={"display": "flex", "gap": "24px", "padding": "12px"}),
    ], className="chart-panel")

    # Top holdings table
    holdings_rows = []
    for h in etf_profile.top_holdings[:10]:
        wt = h.get("weight", float("nan"))
        wt_str = f"{wt*100:.1f}%" if math.isfinite(float(wt)) else "—"
        holdings_rows.append(html.Tr([
            html.Td(h.get("symbol", "—"), className="ticker-cell"),
            html.Td(h.get("name", "—")),
            html.Td(wt_str, className="num"),
        ]))

    holdings_panel = html.Div([
        html.Div([html.Span("Top Holdings", className="chart-title")], className="chart-header"),
        html.Table([
            html.Thead(html.Tr([html.Th("Symbol"), html.Th("Name"), html.Th("Weight")])),
            html.Tbody(holdings_rows),
        ], className="data-table"),
    ], className="chart-panel") if holdings_rows else html.Div()

    return html.Div([
        html.Div([
            html.Div([
                html.Span(etf_profile.name or ticker, className="company-name"),
                html.Span(ticker, className="company-ticker"),
                html.Span(analysis.signal, style={
                    "color": _sig_color(analysis.signal), "fontSize": "13px",
                    "fontWeight": "600", "marginLeft": "10px",
                }),
            ]),
            html.Div(f"{fund_family} · ETF · {etf_profile.category or '—'} · "
                     f"AUM {_bn(etf_profile.aum)}", className="company-meta"),
        ], className="company-header"),
        score_row,
        ret_row,
        holdings_panel,
        sw_panel,
    ])


def _score_card(label, value, sub="", fmt="score"):
    if fmt == "aum":
        disp = _bn(value) if value else "—"
        color = TEXT
    elif fmt == "pct":
        disp = _p(value) if value else "—"
        color = TEXT
    elif fmt == "score" and value is not None:
        v = float(value)
        disp = f"{v:.0f}"
        color = SUCCESS if v >= 65 else WARNING if v >= 40 else DANGER
    else:
        disp = str(value) if value is not None else "—"
        color = TEXT

    return html.Div([
        html.Div(label, className="kpi-label"),
        html.Div(disp, className="kpi-value", style={"color": color}),
        html.Div(sub, className="kpi-sub") if sub else None,
    ], className="kpi-card")


def _render_fundamentals_tab(ticker: str) -> html.Div:
    from research.data.fundamentals_fetcher import fetch_fundamentals, fetch_quarterly
    from research.analytics.fundamental_scorer import score_fundamentals
    import plotly.graph_objects as go

    funds    = fetch_fundamentals(ticker, n_years=10)
    quarters = fetch_quarterly(ticker, n_quarters=8)
    if not funds:
        return html.Div("No data.", className="pf-empty")
    analysis = score_fundamentals(ticker, funds)

    years    = [f.fiscal_year for f in funds]
    revenues = [f.revenue for f in funds]
    margins  = [f.net_margin for f in funds]

    fig_rev = go.Figure()
    fig_rev.add_trace(go.Bar(x=years, y=revenues, name="Revenue", marker_color=ACCENT))
    fig_rev.update_layout(**PLOTLY, height=220, xaxis=dict(**GRID), yaxis=dict(**GRID))

    fig_mg = go.Figure()
    fig_mg.add_trace(go.Scatter(x=years, y=[m * 100 if m else None for m in margins],
                                name="Net Margin %", line=dict(color=SUCCESS, width=2)))
    fig_mg.update_layout(**PLOTLY, height=200, xaxis=dict(**GRID),
                         yaxis=dict(**GRID, ticksuffix="%"))

    return html.Div([
        html.Div([
            html.Div([
                html.Div([html.Span("Revenue", className="chart-title")], className="chart-header"),
                dcc.Graph(figure=fig_rev, config={"displayModeBar": False}),
            ], className="chart-panel"),
            html.Div([
                html.Div([html.Span("Net Margin %", className="chart-title")], className="chart-header"),
                dcc.Graph(figure=fig_mg, config={"displayModeBar": False}),
            ], className="chart-panel"),
        ], className="chart-row"),
    ])


def _render_valuation_tab(ticker: str) -> html.Div:
    from research.data.fundamentals_fetcher import fetch_fundamentals, fetch_profile
    from research.analytics.valuation_engine import (
        ValuationMultiples, dcf_fair_value, fill_dcf_price,
        compute_historical_multiples, compute_sector_median, score_valuation,
    )
    from research.cache.screener_cache import load_screener_rows
    import yfinance as yf

    funds   = fetch_fundamentals(ticker, n_years=5)
    profile = fetch_profile(ticker)
    if not funds:
        return html.Div("No fundamental data.", className="pf-empty")

    info = yf.Ticker(ticker).info or {}

    def _fi(key): return float(info.get(key) or float("nan"))
    current_price = _fi("currentPrice") if math.isfinite(_fi("currentPrice")) else _fi("regularMarketPrice")

    # Current multiples from yfinance
    current = ValuationMultiples(
        pe=_fi("trailingPE"), forward_pe=_fi("forwardPE"),
        ev_ebitda=_fi("enterpriseToEbitda"),
        ps_ratio=_fi("priceToSalesTrailing12Months"),
        pb_ratio=_fi("priceToBook"),
    )

    # Historical year-end prices → historical multiples
    try:
        hist_raw = yf.Ticker(ticker).history(period="10y", interval="3mo")
        year_prices = {ts.year: float(row["Close"]) for ts, row in hist_raw.iterrows()}
    except Exception:
        year_prices = {}
    historical = compute_historical_multiples(funds, year_prices)

    # DCF using most recent annual FCF + shares
    latest = funds[0]
    dcf = dcf_fair_value(
        fcf_base=latest.free_cash_flow if math.isfinite(latest.free_cash_flow) else float("nan"),
        shares=latest.shares_outstanding if math.isfinite(latest.shares_outstanding) else float("nan"),
    )
    fill_dcf_price(dcf, current_price)

    # Sector median from screener cache
    sector_median = ValuationMultiples()
    sector = profile.sector if profile else None
    if sector:
        for u in ("S&P 500", "Nasdaq 100", "STOXX 600", "AEX"):
            peers = [r for r in (load_screener_rows(u) or []) if r.get("sector") == sector]
            if peers:
                sector_median = compute_sector_median(peers)
                break

    val = score_valuation(ticker, current, historical, sector_median, dcf)
    mos = dcf.margin_of_safety

    def _price(v):
        return f"${v:.2f}" if math.isfinite(v) else "—"

    cards = html.Div([
        _score_card("Valuation Score", val.valuation_score, "0 = expensive · 100 = cheap"),
        _score_card("Current Price",   _price(current_price)),
        _score_card("DCF Fair Value",  _price(dcf.fair_value_per_share)),
        _score_card("Margin of Safety", f"{mos*100:+.1f}%" if math.isfinite(mos) else "—",
                    "positive = undervalued"),
        _score_card("vs. History",     val.vs_history),
        _score_card("vs. Sector",      val.vs_sector),
    ], style={"display": "grid", "gridTemplateColumns": "repeat(3,1fr)", "gap": "10px", "marginBottom": "14px"})

    # Multiples comparison table
    mult_data = [
        ("Trailing P/E",  _n(current.pe),       _n(historical.pe_avg),        _n(sector_median.pe)),
        ("Forward P/E",   _n(current.forward_pe), "—",                         "—"),
        ("P/B",           _n(current.pb_ratio),  _n(historical.pb_avg),        _n(sector_median.pb_ratio)),
        ("P/S",           _n(current.ps_ratio),  _n(historical.ps_avg),        "—"),
        ("EV/EBITDA",     _n(current.ev_ebitda), "—",                          "—"),
    ]
    mult_table = html.Div([
        html.Div([html.Span("Valuation Multiples", className="chart-title")], className="chart-header"),
        html.Div(html.Table([
            html.Thead(html.Tr([html.Th("Multiple"), html.Th("Current"), html.Th("5Y Avg"), html.Th("Sector Median")])),
            html.Tbody([
                html.Tr([html.Td(lbl), html.Td(cur, className="num"),
                         html.Td(h, className="num"), html.Td(s, className="num")])
                for lbl, cur, h, s in mult_data
            ]),
        ], className="data-table"), style={"overflowX": "auto"}),
    ], className="chart-panel")

    signals = []
    if val.strengths:
        signals.append(html.Li(s, style={"color": SUCCESS, "fontSize": "13px", "marginBottom": "4px"})
                       for s in val.strengths)
    if val.weaknesses:
        signals.append(html.Li(s, style={"color": DANGER, "fontSize": "13px", "marginBottom": "4px"})
                       for s in val.weaknesses)

    return html.Div([cards, mult_table])


def _render_insider_tab(ticker: str) -> html.Div:
    from research.data.insider_fetcher import fetch_insider_transactions
    from research.analytics.insider_scorer import score_insider_activity

    df = fetch_insider_transactions(ticker)
    analysis = score_insider_activity(ticker, df)

    if df.empty:
        return html.Div("No insider trade data available.", className="pf-empty")

    h12 = analysis.h12
    score_color = SUCCESS if analysis.insider_score >= 65 else DANGER if analysis.insider_score <= 35 else WARNING

    summary_cards = html.Div([
        _score_card("Insider Score",   f"{analysis.insider_score:.0f}", analysis.signal),
        _score_card("12M Buys",        str(h12.n_buys),  f"${h12.value_bought/1e6:.1f}M value"),
        _score_card("12M Sells",       str(h12.n_sells), f"${h12.value_sold/1e6:.1f}M value"),
        _score_card("Last Buy",        f"{analysis.days_since_last_buy}d ago"
                    if analysis.days_since_last_buy >= 0 else "—"),
        _score_card("Last Sell",       f"{analysis.days_since_last_sell}d ago"
                    if analysis.days_since_last_sell >= 0 else "—"),
    ], style={"display": "grid", "gridTemplateColumns": "repeat(5,1fr)",
              "gap": "10px", "marginBottom": "14px"})

    table_rows = []
    for _, row in df.head(25).iterrows():
        date_val = row.get("date")
        date_str = str(date_val.date()) if hasattr(date_val, "date") else str(date_val or "—")
        shares   = row.get("shares", 0) or 0
        value    = row.get("value",  0) or 0
        txn      = str(row.get("transaction", "—"))
        color    = SUCCESS if any(k in txn.lower() for k in ("buy", "purchase")) else \
                   DANGER  if any(k in txn.lower() for k in ("sale", "sell"))    else TEXT
        table_rows.append(html.Tr([
            html.Td(date_str),
            html.Td(str(row.get("insider", "—"))),
            html.Td(str(row.get("position", "—"))),
            html.Td(txn, style={"color": color, "fontWeight": "600"}),
            html.Td(f"{shares:,.0f}", className="num"),
            html.Td(f"${value:,.0f}", className="num"),
        ]))

    table = html.Div([
        html.Div([html.Span("Recent Insider Transactions", className="chart-title")],
                 className="chart-header"),
        html.Div(html.Table([
            html.Thead(html.Tr([
                html.Th("Date"), html.Th("Insider"), html.Th("Role"),
                html.Th("Transaction"), html.Th("Shares"), html.Th("Value ($)"),
            ])),
            html.Tbody(table_rows),
        ], className="data-table"), style={"overflowX": "auto"}),
    ], className="chart-panel")

    return html.Div([summary_cards, table])


def _render_report_tab(ticker: str) -> html.Div:
    from research.data.fundamentals_fetcher import fetch_fundamentals, fetch_profile
    from research.data.insider_fetcher import fetch_insider_transactions
    from research.analytics.fundamental_scorer import score_fundamentals
    from research.analytics.insider_scorer import score_insider_activity
    from research.analytics.technical_scorer import score_technical
    from research.analytics.thesis_generator import generate_thesis
    import yfinance as yf

    funds   = fetch_fundamentals(ticker, n_years=5)
    profile = fetch_profile(ticker)
    if not funds:
        return html.Div("No fundamental data — cannot generate thesis.", className="pf-empty")

    analysis = score_fundamentals(ticker, funds)
    fund_score = float(analysis.fundamental_score) if analysis and analysis.fundamental_score is not None else 50.0

    # Insider score
    ins_df   = fetch_insider_transactions(ticker)
    ins_ana  = score_insider_activity(ticker, ins_df)
    insider_score = float(ins_ana.insider_score)

    # Technical score from recent price history
    try:
        price_hist = yf.Ticker(ticker).history(period="1y")
        tech_ana   = score_technical(ticker, price_hist)
        tech_score = float(tech_ana.score)
        tech_signal = tech_ana.signal
        ta = tech_ana
    except Exception:
        tech_score = 50.0
        tech_signal = "Neutral"
        ta = None

    # Sector score — try from screener cache peers
    from research.cache.screener_cache import load_screener_rows
    sector = profile.sector if profile else None
    sector_score = 50.0
    if sector:
        scores = []
        for u in ("S&P 500", "Nasdaq 100", "STOXX 600", "AEX"):
            for r in (load_screener_rows(u) or []):
                if r.get("sector") == sector:
                    v = r.get("fundamental_score")
                    if v is not None:
                        scores.append(float(v))
        if scores:
            sector_score = sum(scores) / len(scores)

    # Valuation score (best-effort; use 50 if data missing)
    val_score = 50.0
    try:
        from research.analytics.valuation_engine import (
            ValuationMultiples, dcf_fair_value, fill_dcf_price,
            compute_historical_multiples, score_valuation,
        )
        info = yf.Ticker(ticker).info or {}
        def _fi(k): return float(info.get(k) or float("nan"))
        current_price = _fi("currentPrice") if math.isfinite(_fi("currentPrice")) else _fi("regularMarketPrice")
        current = ValuationMultiples(
            pe=_fi("trailingPE"), forward_pe=_fi("forwardPE"),
            pb_ratio=_fi("priceToBook"), ps_ratio=_fi("priceToSalesTrailing12Months"),
        )
        hist_raw   = yf.Ticker(ticker).history(period="5y", interval="3mo")
        year_prices = {ts.year: float(r["Close"]) for ts, r in hist_raw.iterrows()}
        historical  = compute_historical_multiples(funds, year_prices)
        dcf = fill_dcf_price(dcf_fair_value(funds[0].free_cash_flow, funds[0].shares_outstanding), current_price)
        from research.analytics.valuation_engine import ValuationMultiples as _VM
        val = score_valuation(ticker, current, historical, _VM(), dcf)
        val_score = float(val.valuation_score) if math.isfinite(val.valuation_score) else 50.0
    except Exception:
        pass

    thesis = generate_thesis(
        company_name   = profile.name or ticker if profile else ticker,
        sector         = sector or "Unknown",
        fund_score     = fund_score,
        val_score      = val_score,
        tech_score     = tech_score,
        sector_score   = sector_score,
        insider_score  = insider_score,
        strengths      = list(analysis.strengths)  if analysis and hasattr(analysis, "strengths")  else [],
        weaknesses     = list(analysis.weaknesses) if analysis and hasattr(analysis, "weaknesses") else [],
        tech_signal    = tech_signal,
        insider_signal = ins_ana.signal,
        n_buys         = ins_ana.h12.n_buys,
        n_sells        = ins_ana.h12.n_sells,
        ta             = ta,
    )

    score_color = SUCCESS if thesis.overall_score >= 65 else WARNING if thesis.overall_score >= 40 else DANGER

    score_row = html.Div([
        _score_card("Overall Score",   f"{thesis.overall_score:.0f} / 100", thesis.verdict_label),
        _score_card("Fundamentals",    f"{fund_score:.0f}",  "30% weight"),
        _score_card("Valuation",       f"{val_score:.0f}",   "25% weight"),
        _score_card("Technical",       f"{tech_score:.0f}",  f"20% · {tech_signal}"),
        _score_card("Sector",          f"{sector_score:.0f}", "15% weight"),
        _score_card("Insider",         f"{insider_score:.0f}", f"10% · {ins_ana.signal}"),
    ], style={"display": "grid", "gridTemplateColumns": "repeat(6,1fr)",
              "gap": "10px", "marginBottom": "14px"})

    def _para(text: str) -> html.P:
        return html.P(text, style={"fontSize": "13px", "color": TEXT,
                                   "lineHeight": "1.65", "marginBottom": "10px"})

    paragraphs = []
    for attr in ("verdict_rationale", "quality_paragraph", "valuation_paragraph",
                 "technical_paragraph", "sector_paragraph", "insider_paragraph"):
        txt = getattr(thesis, attr, None)
        if txt:
            paragraphs.append(_para(txt))

    thesis_panel = html.Div([
        html.Div([
            html.Span("Investment Thesis", className="chart-title"),
            html.Span(f"  —  {thesis.verdict_label}",
                      style={"color": score_color, "fontWeight": "700", "fontSize": "13px"}),
        ], className="chart-header"),
        *paragraphs,
    ], className="chart-panel")

    risk_items = thesis.risk_bullets if hasattr(thesis, "risk_bullets") and thesis.risk_bullets else []
    risk_panel = html.Div([
        html.Div([html.Span("Key Risks", className="chart-title")], className="chart-header"),
        html.Ul([html.Li(r, style={"fontSize": "13px", "color": MUTED, "marginBottom": "5px"})
                 for r in risk_items],
                style={"paddingLeft": "18px"}),
    ], className="chart-panel") if risk_items else html.Div()

    return html.Div([score_row, thesis_panel, risk_panel])


# ── Sector renderer ────────────────────────────────────────────────────────────

def _render_sector(sector: str) -> html.Div:
    from research.data.sector_data import (
        fetch_sector_prices, SECTOR_ETF_MAP, momentum, relative_strength,
        aggregate_sector_fundamentals,
    )
    from research.cache.screener_cache import load_screener_rows

    # ── Price momentum ─────────────────────────────────────────────────────────
    etf_ticker = SECTOR_ETF_MAP.get(sector)
    prices     = fetch_sector_prices("1y")
    market     = prices.get("SPY")

    mom_1m = mom_3m = mom_6m = mom_1y = rs = float("nan")
    if etf_ticker and etf_ticker in prices:
        s = prices[etf_ticker]
        mom_1m = momentum(s, 1)
        mom_3m = momentum(s, 3)
        mom_6m = momentum(s, 6)
        mom_1y = momentum(s, 12)
        if market is not None:
            rs = relative_strength(s, market, 12)

    def _ret_card(label: str, val: float) -> html.Div:
        if math.isnan(val):
            disp, color = "—", MUTED
        else:
            disp  = f"{val*100:+.1f}%"
            color = SUCCESS if val > 0 else DANGER
        return html.Div([
            html.Div(label, className="kpi-label"),
            html.Div(disp, className="kpi-value", style={"color": color}),
        ], className="kpi-card")

    mom_row = html.Div([
        _ret_card("1M Return",   mom_1m),
        _ret_card("3M Return",   mom_3m),
        _ret_card("6M Return",   mom_6m),
        _ret_card("1Y Return",   mom_1y),
        html.Div([
            html.Div("vs. SPY (1Y)", className="kpi-label"),
            html.Div(
                f"{rs*100:+.1f}%" if not math.isnan(rs) else "—",
                className="kpi-value",
                style={"color": SUCCESS if not math.isnan(rs) and rs > 0 else DANGER},
            ),
        ], className="kpi-card"),
    ], style={"display": "grid", "gridTemplateColumns": "repeat(5,1fr)",
              "gap": "10px", "marginBottom": "14px"})

    # ── Price chart ────────────────────────────────────────────────────────────
    charts = []
    if etf_ticker and etf_ticker in prices:
        s = prices[etf_ticker]
        # Normalise to 100 at start
        norm = s / s.iloc[0] * 100
        dates = [str(d.date()) for d in norm.index]
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=dates, y=norm.values, name=f"{sector} ({etf_ticker})",
            line=dict(color=ACCENT, width=2),
        ))
        if market is not None:
            mn = market / market.iloc[0] * 100
            fig.add_trace(go.Scatter(
                x=[str(d.date()) for d in mn.index], y=mn.values,
                name="S&P 500 (SPY)", line=dict(color=BLUE, width=1.5, dash="dot"),
            ))
        fig.update_layout(**PLOTLY, height=250,
                          xaxis=dict(**GRID), yaxis=dict(**GRID))
        charts.append(html.Div([
            html.Div([html.Span(f"{sector} — Price vs. S&P 500 (1Y, rebased to 100)",
                                className="chart-title")], className="chart-header"),
            dcc.Graph(figure=fig, config={"displayModeBar": False}),
        ], className="chart-panel"))

    # ── Fundamental aggregation from screener cache ────────────────────────────
    fund_rows = []
    for u in ("S&P 500", "Nasdaq 100", "STOXX 600", "AEX"):
        cached = load_screener_rows(u) or []
        if cached:
            agg = aggregate_sector_fundamentals(cached, sector)
            if agg.get("n_peers", 0) > 0:
                fund_rows.append(html.Tr([
                    html.Td(u),
                    html.Td(str(int(agg["n_peers"])), className="num"),
                    html.Td(_score_badge(agg.get("avg_fund_score")), className="num"),
                    html.Td(_score_badge(agg.get("avg_val_score")),  className="num"),
                    html.Td(_score_badge(agg.get("avg_trend_score")), className="num"),
                    html.Td(_p(agg.get("avg_rev_growth")),           className="num"),
                    html.Td(_p(agg.get("avg_roe")),                  className="num"),
                ]))

    fund_panel = html.Div()
    if fund_rows:
        fund_panel = html.Div([
            html.Div([html.Span("Fundamentals by Universe (screener cache)", className="chart-title")],
                     className="chart-header"),
            html.Div(html.Table([
                html.Thead(html.Tr([
                    html.Th("Universe"), html.Th("Peers"),
                    html.Th("Fund."), html.Th("Val."), html.Th("Tech."),
                    html.Th("Rev. Growth"), html.Th("ROE"),
                ])),
                html.Tbody(fund_rows),
            ], className="data-table"), style={"overflowX": "auto"}),
        ], className="chart-panel")

    return html.Div([
        html.Div(sector, style={"fontSize": "17px", "fontWeight": 800,
                                "color": TEXT, "marginBottom": "14px"}),
        mom_row,
        *charts,
        fund_panel,
    ])


# ── Screener renderer ──────────────────────────────────────────────────────────

def _render_screener(universe: str) -> tuple[html.Div, str]:
    from research.cache.screener_cache import load_screener_rows

    rows = load_screener_rows(universe)
    if rows is None:
        from research.analytics.screener import run_screener
        rows = run_screener(universe)

    if not rows:
        return html.Div("No screener data.", className="pf-empty"), "No data"

    # Sort by composite_score desc
    rows = sorted(rows, key=lambda r: float(r.get("composite_score") or 0), reverse=True)

    # ── Market overview strip ──────────────────────────────────────────────────
    scores = [float(r["composite_score"]) for r in rows if r.get("composite_score") is not None]
    avg_score = sum(scores) / len(scores) if scores else 0
    top3    = rows[:3]
    bottom3 = rows[-3:][::-1]

    def _mini_card(label, val, color=TEXT):
        return html.Div([
            html.Div(label, className="kpi-label"),
            html.Div(str(val), className="kpi-value", style={"color": color, "fontSize": "16px"}),
        ], className="kpi-card")

    sector_counts: dict[str, int] = {}
    for r in rows:
        sec = r.get("sector") or "Unknown"
        sector_counts[sec] = sector_counts.get(sec, 0) + 1
    top_sector = max(sector_counts, key=sector_counts.get) if sector_counts else "—"

    score_color = SUCCESS if avg_score >= 60 else WARNING if avg_score >= 40 else DANGER
    overview = html.Div([
        html.Div([
            _mini_card("Companies",   len(rows)),
            _mini_card("Avg Score",   f"{avg_score:.0f}", score_color),
            _mini_card("Top Sector",  top_sector),
            html.Div([
                html.Div("Top 3", className="kpi-label"),
                html.Div([
                    html.Div(f"{r.get('ticker','—')}  {r.get('composite_score',0):.0f}",
                             style={"fontSize": "12px", "color": SUCCESS})
                    for r in top3
                ]),
            ], className="kpi-card"),
            html.Div([
                html.Div("Bottom 3", className="kpi-label"),
                html.Div([
                    html.Div(f"{r.get('ticker','—')}  {r.get('composite_score',0):.0f}",
                             style={"fontSize": "12px", "color": DANGER})
                    for r in bottom3
                ]),
            ], className="kpi-card"),
        ], style={"display": "grid", "gridTemplateColumns": "repeat(5,1fr)",
                  "gap": "10px", "marginBottom": "14px"}),
    ])

    table_rows = []
    for r in rows[:100]:
        score = r.get("composite_score")
        fund  = r.get("fundamental_score")
        val   = r.get("valuation_score")
        tech  = r.get("technical_score")
        table_rows.append(html.Tr([
            html.Td(r.get("ticker", ""),   className="ticker-cell"),
            html.Td(r.get("name", "")[:28]),
            html.Td(r.get("sector", "—")),
            html.Td(_score_badge(score),   className="num"),
            html.Td(_score_badge(fund),    className="num"),
            html.Td(_score_badge(val),     className="num"),
            html.Td(_score_badge(tech),    className="num"),
            html.Td(_p(r.get("pe_ratio")) if r.get("pe_ratio") else "—", className="num"),
            html.Td(_p(r.get("revenue_growth")), className="num",
                    style={"color": SUCCESS if (r.get("revenue_growth") or 0) > 0 else DANGER}),
        ]))

    table = html.Table([
        html.Thead(html.Tr([
            html.Th("Ticker"), html.Th("Name"), html.Th("Sector"),
            html.Th("Score"), html.Th("Fund."), html.Th("Val."), html.Th("Tech."),
            html.Th("P/E"), html.Th("Rev. Growth"),
        ])),
        html.Tbody(table_rows),
    ], className="data-table")

    status = f"{len(rows)} companies · {universe}"
    return html.Div([
        overview,
        html.Div(style={"overflowX": "auto"}, children=[table]),
    ], className="chart-panel"), status


# ── Watchlist content ──────────────────────────────────────────────────────────

def _render_watchlist(name: str) -> html.Div:
    from research.data.watchlist_store import load_watchlist
    wl = load_watchlist(name)
    if not wl or not wl.entries:
        return html.Div("This watchlist is empty.", className="pf-empty")
    rows = [html.Tr([
        html.Td(e.ticker, className="ticker-cell"),
        html.Td(e.note or "—"),
        html.Td(e.added_at or "—"),
    ]) for e in wl.entries]
    return html.Div([
        html.Div([
            html.Span(f"{wl.name} — {len(wl.entries)} tickers", className="chart-title"),
        ], className="chart-header"),
        html.Table([
            html.Thead(html.Tr([html.Th("Ticker"), html.Th("Note"), html.Th("Added")])),
            html.Tbody(rows),
        ], className="data-table"),
    ], className="chart-panel")


# ── Callbacks ─────────────────────────────────────────────────────────────────

@callback(
    Output("research-tab-content", "children"),
    Input("research-tabs", "value"),
)
def render_research_tab(tab):
    if tab == "tab-screener":
        return build_screener_tab()
    elif tab == "tab-watchlists":
        return build_watchlists_tab()
    elif tab == "tab-company":
        return build_company_tab()
    else:
        return build_sector_tab()


@callback(
    Output("rh-screener-results", "children"),
    Output("rh-screener-status", "children"),
    Input("rh-screen-btn", "n_clicks"),
    State("rh-universe-select", "value"),
    prevent_initial_call=True,
)
def run_screener_callback(n, universe):
    if not n or not universe:
        return no_update, no_update
    content, status = _render_screener(universe)
    return content, status


@callback(
    Output("rh-company-content", "children"),
    Input("rh-company-btn", "n_clicks"),
    State("rh-company-ticker", "value"),
    prevent_initial_call=True,
)
def lookup_company(n, ticker):
    if not n or not ticker:
        return no_update
    ticker = ticker.strip().upper()
    try:
        return _render_company(ticker)
    except Exception as exc:
        return html.Div(f"Error loading {ticker}: {exc}",
                        style={"color": DANGER, "fontSize": "13px"})


@callback(
    Output("company-tab-content", "children"),
    Input("company-tabs", "value"),
    State("company-ticker-store", "children"),
    prevent_initial_call=True,
)
def render_company_tab(tab, ticker):
    if not ticker:
        return no_update
    try:
        if tab == "tab-fund":
            return _render_fundamentals_tab(ticker)
        elif tab == "tab-val":
            return _render_valuation_tab(ticker)
        elif tab == "tab-ins":
            return _render_insider_tab(ticker)
        else:
            return _render_report_tab(ticker)
    except Exception as exc:
        return html.Div(f"Error: {exc}", style={"color": DANGER, "fontSize": "13px"})


@callback(
    Output("rh-sector-content", "children"),
    Input("rh-sector-btn", "n_clicks"),
    State("rh-sector-select", "value"),
    prevent_initial_call=True,
)
def run_sector_analysis(n, sector):
    if not n or not sector:
        return no_update
    try:
        return _render_sector(sector)
    except Exception as exc:
        return html.Div(f"Error: {exc}", style={"color": DANGER, "fontSize": "13px"})


@callback(
    Output("wl-content", "children"),
    Input("wl-select", "value"),
)
def show_watchlist(name):
    if not name:
        return html.Div("Select a watchlist above.", className="pf-empty")
    return _render_watchlist(name)
