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


# ── Research sidebar ───────────────────────────────────────────────────────────

def research_sidebar() -> html.Div:
    return html.Div([
        html.Div([
            html.Div("Research Hub", className="sb-section-title"),
            html.Div("Fundamentals · Valuation · Insider · Sector",
                     style={"fontSize": "11px", "color": MUTED, "lineHeight": "1.5"}),
        ], className="sb-section"),
        html.Div([
            html.Div("Quick look-up", className="sb-section-title"),
            dcc.Input(id="rh-quick-ticker", type="text", placeholder="AAPL",
                      debounce=True,
                      style={"width": "100%", "background": "#1c2128", "border": f"1px solid {BORDER}",
                             "borderRadius": "6px", "color": TEXT, "padding": "7px 10px",
                             "fontSize": "12px", "fontFamily": "inherit", "outline": "none"}),
            html.Button("Look up →", id="rh-quick-btn", className="sb-btn", n_clicks=0,
                        style={"marginTop": "5px"}),
        ], className="sb-section"),
    ], className="sidebar")


# ── Research Hub main layout ───────────────────────────────────────────────────

def research_hub_layout() -> html.Div:
    return html.Div([
        research_sidebar(),
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
    return html.Div([
        html.Div([
            dcc.Input(id="rh-company-ticker", type="text", placeholder="AAPL",
                      debounce=True,
                      style={"flex": 1, "background": "#1c2128", "border": f"1px solid {BORDER}",
                             "borderRadius": "6px", "color": TEXT, "padding": "8px 12px",
                             "fontSize": "13px", "fontFamily": "inherit", "outline": "none",
                             "maxWidth": "280px"}),
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
    import yfinance as yf

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
        _score_card("Fundamental Score", analysis.overall_score if analysis else None, "composite quality score"),
        _score_card("Profitability",     analysis.profitability_score if analysis else None),
        _score_card("Growth",            analysis.growth_score if analysis else None),
        _score_card("Financial Health",  analysis.financial_health_score if analysis else None),
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
    from streamlit_app.pages.etf_analysis import render_detail as etf_render
    # ETF routing — fallback to simple display if Streamlit page isn't convertible
    fund_family = info.get("fundFamily", "—")
    return html.Div([
        html.Div([
            html.Div([
                html.Span(info.get("longName") or ticker, className="company-name"),
                html.Span(ticker, className="company-ticker"),
            ]),
            html.Div(f"{fund_family} · ETF / Fund", className="company-meta"),
        ], className="company-header"),
        html.Div([
            _score_card("AUM",        info.get("totalAssets"), fmt="aum"),
            _score_card("Expense",    info.get("annualReportExpenseRatio"), fmt="pct"),
            _score_card("Holdings",   info.get("holdings") and len(info["holdings"]) or None),
            _score_card("YTD",        info.get("ytdReturn"), fmt="pct"),
        ], style={"display": "grid", "gridTemplateColumns": "repeat(4,1fr)", "gap": "10px", "marginBottom": "14px"}),
        html.Div(f"ETF analysis: open Research Hub → Company Look-up → {ticker}",
                 style={"color": MUTED, "fontSize": "13px"}),
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
    from research.analytics.valuation_engine import run_valuation
    import yfinance as yf

    funds   = fetch_fundamentals(ticker, n_years=5)
    profile = fetch_profile(ticker)
    if not funds:
        return html.Div("No data.", className="pf-empty")

    try:
        val = run_valuation(ticker, funds, profile)
    except Exception as e:
        return html.Div(f"Valuation error: {e}", style={"color": DANGER, "fontSize": "12px"})

    price = yf.Ticker(ticker).info.get("currentPrice")

    cards = html.Div([
        _score_card("Current Price",  f"${price:.2f}" if price else "—"),
        _score_card("DCF Intrinsic",  f"${val.dcf_value:.2f}" if val.dcf_value else "—"),
        _score_card("P/E Fair",       f"${val.pe_fair_value:.2f}" if val.pe_fair_value else "—"),
        _score_card("Margin of Safety", _p(val.margin_of_safety) if val.margin_of_safety else "—"),
    ], style={"display": "grid", "gridTemplateColumns": "repeat(4,1fr)", "gap": "10px", "marginBottom": "14px"})

    return html.Div([cards])


def _render_insider_tab(ticker: str) -> html.Div:
    from research.data.insider_fetcher import fetch_insider_trades
    from research.analytics.insider_scorer import score_insider_activity

    trades = fetch_insider_trades(ticker)
    if not trades:
        return html.Div("No insider trade data available.", className="pf-empty")

    score_result = score_insider_activity(trades)

    rows = []
    for t in trades[:20]:
        rows.append(html.Tr([
            html.Td(t.filing_date or "—"),
            html.Td(t.insider_name or "—"),
            html.Td(t.title or "—"),
            html.Td(t.transaction_type or "—"),
            html.Td(f"{t.shares:,.0f}" if t.shares else "—", className="num"),
            html.Td(f"${t.price_per_share:.2f}" if t.price_per_share else "—", className="num"),
            html.Td(f"${t.total_value:,.0f}" if t.total_value else "—", className="num"),
        ]))

    return html.Div([
        html.Div([
            _score_card("Insider Score", score_result.score if score_result else None, "0=bearish, 100=bullish"),
            _score_card("Buy Transactions",  score_result.buy_count if score_result else None),
            _score_card("Sell Transactions", score_result.sell_count if score_result else None),
        ], style={"display": "grid", "gridTemplateColumns": "repeat(3,1fr)", "gap": "10px", "marginBottom": "14px"}),
        html.Div([
            html.Div([html.Span("Recent Insider Trades", className="chart-title")], className="chart-header"),
            html.Div(html.Table([
                html.Thead(html.Tr([
                    html.Th("Date"), html.Th("Insider"), html.Th("Title"),
                    html.Th("Type"), html.Th("Shares"), html.Th("Price"), html.Th("Value"),
                ])),
                html.Tbody(rows),
            ], className="data-table"), style={"overflowX": "auto"}),
        ], className="chart-panel"),
    ])


def _render_report_tab(ticker: str) -> html.Div:
    from research.data.fundamentals_fetcher import fetch_fundamentals, fetch_quarterly, fetch_profile
    from research.analytics.fundamental_scorer import score_fundamentals
    from research.analytics.thesis_generator import generate_thesis

    funds    = fetch_fundamentals(ticker, n_years=5)
    quarters = fetch_quarterly(ticker, n_quarters=8)
    profile  = fetch_profile(ticker)
    analysis = score_fundamentals(ticker, funds) if funds else None
    thesis   = generate_thesis(ticker, funds, analysis, profile) if funds else None

    if not thesis:
        return html.Div("Could not generate thesis.", className="pf-empty")

    bullets = [html.Li(b, style={"marginBottom": "6px"}) for b in (thesis.bullets or [])]
    risks   = [html.Li(r, style={"marginBottom": "6px"}) for r in (thesis.risks or [])]

    return html.Div([
        html.Div([
            html.Div("Overall Score", className="kpi-label"),
            html.Div(f"{thesis.overall_score:.0f} / 100",
                     className="kpi-value",
                     style={"color": SUCCESS if thesis.overall_score >= 65 else WARNING if thesis.overall_score >= 40 else DANGER}),
        ], className="kpi-card", style={"display": "inline-block", "marginBottom": "14px", "minWidth": "120px"}),
        html.Div([
            html.Div([html.Span("Thesis", className="chart-title")], className="chart-header"),
            html.P(thesis.summary or "", style={"fontSize": "13px", "color": TEXT, "lineHeight": "1.6", "marginBottom": "12px"}),
            html.Ul(bullets, style={"paddingLeft": "18px", "fontSize": "13px", "color": MUTED, "lineHeight": "1.7"}),
        ], className="chart-panel"),
        html.Div([
            html.Div([html.Span("Key Risks", className="chart-title")], className="chart-header"),
            html.Ul(risks, style={"paddingLeft": "18px", "fontSize": "13px", "color": MUTED, "lineHeight": "1.7"}),
        ], className="chart-panel") if risks else None,
    ])


# ── Sector renderer ────────────────────────────────────────────────────────────

def _render_sector(sector: str) -> html.Div:
    from research.pages import sector_intel as _si

    try:
        from research.data.sector_fetcher import fetch_sector_summary
        data = fetch_sector_summary(sector)
    except Exception:
        data = None

    if not data:
        return html.Div(f"No sector data for {sector}.", className="pf-empty")

    return html.Div([
        html.Div([
            html.Div(sector, style={"fontSize": "17px", "fontWeight": 800, "color": TEXT, "marginBottom": "14px"}),
        ]),
        html.Div(str(data), style={"fontSize": "12px", "color": MUTED, "whiteSpace": "pre-wrap"}),
    ], className="chart-panel")


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
    Input("rh-quick-btn", "n_clicks"),
    State("rh-company-ticker", "value"),
    State("rh-quick-ticker", "value"),
    prevent_initial_call=True,
)
def lookup_company(n1, n2, ticker1, ticker2):
    from dash import callback_context
    ctx = callback_context
    if not ctx.triggered:
        return no_update
    trigger = ctx.triggered[0]["prop_id"]
    ticker = (ticker2 if "quick" in trigger else ticker1 or "").strip().upper()
    if not ticker:
        return no_update

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
