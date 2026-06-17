"""Portfolio Hub layout + callbacks."""

from __future__ import annotations

import math
import sys
from datetime import timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd
import plotly.graph_objects as go
from dash import ALL, Input, Output, State, callback, dcc, html, no_update

from dash_app.components.analysis_runner import run_analysis
from dash_app.components.theme import (
    ACCENT, BLUE, BORDER, CARD, DANGER, DIM, GRID, MUTED,
    PLOTLY, SUCCESS, TEXT, WARNING, color_metric,
)
from utils.constants import ANALYSIS_PERIODS, BENCHMARKS
from utils.ticker_suggestions import _TICKERS as _TICKER_NAMES, ticker_options

# ── Formatting ─────────────────────────────────────────────────────────────────

def _p(v, d=2):
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return "—"
    return f"{v * 100:+.{d}f} %" if v >= 0 else f"{v * 100:.{d}f} %"


def _n(v, d=2):
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return "—"
    return f"{v:.{d}f}"


def _c(v, good, warn):
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return MUTED
    return color_metric(v, good, warn)


# ── Sidebar layout ─────────────────────────────────────────────────────────────

def portfolio_sidebar(pf_data: dict | None) -> html.Div:
    pf_data = pf_data or {}
    tickers  = pf_data.get("tickers", [])
    weights  = pf_data.get("weights", {})
    benchmark = pf_data.get("benchmark", "SPY")
    period    = pf_data.get("period", "5y")
    rf_rate   = pf_data.get("rf_rate", 0.025)

    # Ticker rows
    ticker_rows = []
    for t in tickers:
        w  = weights.get(t, 0.0)
        pct = round(w * 100, 1)
        name = _TICKER_NAMES.get(t, "")[:22]
        ticker_rows.append(html.Div([
            html.Div(t[:5], className="ticker-badge"),
            html.Div([
                html.Div(t, className="ticker-name"),
                html.Div(name, className="ticker-fullname"),
            ], className="ticker-info"),
            html.Div([
                dcc.Input(
                    id={"type": "pf-weight-input", "index": t},
                    type="number", min=0, max=100, step=0.1,
                    value=pct, debounce=True,
                    className="weight-input",
                ),
                html.Span(" %", className="weight-pct"),
            ], className="ticker-weight-block"),
        ], className="ticker-row"))
        ticker_rows.append(html.Div(
            html.Div(className="weight-bar-fill", style={"width": f"{min(pct, 100)}%"}),
            className="weight-bar-track",
        ))

    if not ticker_rows:
        ticker_rows = [html.Div("No tickers added yet.", className="pf-empty")]

    return html.Div([
        # ── Add ticker ────────────────────────────────────────────────────────
        html.Div([
            html.Div("Portfolio", className="sb-section-title"),
            dcc.Dropdown(
                id="pf-ticker-dropdown",
                options=[{"label": o, "value": o} for o in ticker_options()],
                placeholder="Search ticker or company…",
                className="dash-dropdown",
                clearable=True,
                searchable=True,
                style={"marginBottom": "6px"},
            ),
            html.Button("+ Add ticker", id="pf-add-btn", className="sb-btn", n_clicks=0),
        ], className="sb-section"),

        # ── Ticker list ───────────────────────────────────────────────────────
        html.Div(ticker_rows, id="pf-ticker-list"),

        # ── Quick weight actions ──────────────────────────────────────────────
        html.Div([
            html.Div([
                html.Button("= Equal", id="pf-equalweight-btn", className="sb-btn", n_clicks=0, style={"flex": 1}),
                html.Button("↻ Norm.", id="pf-normalize-btn",  className="sb-btn", n_clicks=0, style={"flex": 1}),
            ], className="btn-row"),
            dcc.Dropdown(
                id="pf-remove-dropdown",
                options=[{"label": t, "value": t} for t in tickers],
                placeholder="Remove ticker…",
                className="dash-dropdown",
                clearable=True,
                style={"marginTop": "4px"},
            ),
            html.Button("✕ Remove", id="pf-remove-btn", className="sb-btn danger", n_clicks=0),
        ], className="sb-section"),

        # ── Settings ──────────────────────────────────────────────────────────
        html.Div([
            html.Div("Settings", className="sb-section-title"),
            html.Div([
                html.Div("Benchmark", className="setting-label"),
                dcc.Dropdown(
                    id="pf-benchmark-select",
                    options=[{"label": b, "value": b} for b in BENCHMARKS],
                    value=benchmark,
                    clearable=False, className="dash-dropdown",
                ),
            ], className="setting-row"),
            html.Div([
                html.Div("Analysis period", className="setting-label"),
                dcc.Dropdown(
                    id="pf-period-select",
                    options=[{"label": p, "value": p} for p in ANALYSIS_PERIODS],
                    value=period,
                    clearable=False, className="dash-dropdown",
                ),
            ], className="setting-row"),
            html.Div([
                html.Div("Risk-free rate", className="setting-label"),
                dcc.Dropdown(
                    id="pf-rfrate-select",
                    options=[{"label": f"{r:.1f} %", "value": r / 100} for r in [2.0, 2.5, 3.0, 3.5, 4.0, 5.0]],
                    value=rf_rate,
                    clearable=False, className="dash-dropdown",
                ),
            ], className="setting-row"),
        ], className="sb-section"),

        # ── Actions ───────────────────────────────────────────────────────────
        html.Div([
            html.Button("▶  Analyse Portfolio", id="pf-analyse-btn",
                        className="sb-btn primary", n_clicks=0),
            html.Div(id="pf-analyse-status", style={"fontSize": "11px", "color": MUTED, "textAlign": "center", "marginTop": "6px"}),
        ], className="sb-section"),
    ], className="sidebar", id="pf-sidebar")


# ── Main content ───────────────────────────────────────────────────────────────

def portfolio_hub_layout() -> html.Div:
    return html.Div([
        portfolio_sidebar(None),
        html.Div([
            html.Div([
                html.Span("Portfolio Hub", className="page-title"),
                html.Span(id="pf-header-meta", className="page-meta"),
            ], className="page-header"),
            dcc.Tabs(id="portfolio-tabs", value="tab-dashboard", className="main-tabs", children=[
                dcc.Tab(label="Dashboard",      value="tab-dashboard", className="tab"),
                dcc.Tab(label="Asset Analysis", value="tab-asset",     className="tab"),
                dcc.Tab(label="Monte Carlo",    value="tab-mc",        className="tab"),
            ]),
            dcc.Loading(
                html.Div(id="portfolio-tab-content"),
                type="circle", color=ACCENT,
            ),
        ], className="main"),
    ], className="app-body")


# ── Chart helpers ──────────────────────────────────────────────────────────────

def _filter_period(dates, values, period):
    if not dates:
        return dates, values
    df = pd.DataFrame({"v": values}, index=pd.to_datetime(dates))
    today = df.index[-1]
    cutoffs = {
        "1M":  today - timedelta(days=30),
        "3M":  today - timedelta(days=91),
        "6M":  today - timedelta(days=182),
        "YTD": pd.Timestamp(today.year, 1, 1),
        "1Y":  today - timedelta(days=365),
        "All": df.index[0],
    }
    start = cutoffs.get(period, df.index[0])
    sliced = df[df.index >= start]
    return sliced.index.strftime("%Y-%m-%d").tolist(), sliced["v"].tolist()


def _perf_fig(result: dict, period: str = "All") -> go.Figure:
    pv = result["series"]["port_val"]
    bv = result["series"]["bench_val"]
    bench = result["meta"]["benchmark"]

    p_dates, p_vals = _filter_period(pv["dates"], pv["values"], period)
    b_dates, b_vals = _filter_period(bv["dates"], bv["values"], period)

    # Re-base to 10 000
    if p_vals:
        base = p_vals[0] or 1
        p_vals = [v / base * 10_000 if v else None for v in p_vals]
    if b_vals:
        base = b_vals[0] or 1
        b_vals = [v / base * 10_000 if v else None for v in b_vals]

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=p_dates, y=p_vals, name="Portfolio",
                             line=dict(color=ACCENT, width=2.5),
                             fill="tozeroy", fillcolor="rgba(102,165,247,0.06)"))
    fig.add_trace(go.Scatter(x=b_dates, y=b_vals, name=bench,
                             line=dict(color=BLUE, width=1.8, dash="dot")))
    fig.update_layout(**PLOTLY, height=280,
                      xaxis=dict(**GRID, showgrid=True),
                      yaxis=dict(**GRID, tickprefix="€", showgrid=True),
                      hovermode="x unified")
    return fig


def _dd_fig(result: dict) -> go.Figure:
    dd = result["series"]["drawdown"]
    vals = [v * 100 if v is not None else None for v in dd["values"]]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=dd["dates"], y=vals, name="Drawdown",
                             fill="tozeroy", fillcolor="rgba(248,81,73,0.1)",
                             line=dict(color=DANGER, width=1.5)))
    fig.update_layout(**PLOTLY, height=200,
                      xaxis=dict(**GRID), yaxis=dict(**GRID, ticksuffix="%"))
    return fig


def _rollvol_fig(result: dict) -> go.Figure:
    rv = result["series"]["roll_vol"]
    vals = [v * 100 if v is not None else None for v in rv["values"]]
    clean = [v for v in vals if v is not None]
    avg = sum(clean) / len(clean) if clean else None
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=rv["dates"], y=vals, name="Vol 252d",
                             fill="tozeroy", fillcolor="rgba(88,166,255,0.07)",
                             line=dict(color=BLUE, width=1.5)))
    if avg:
        fig.add_hline(y=avg, line=dict(color=WARNING, width=1, dash="dot"),
                      annotation_text=f"avg {avg:.1f}%",
                      annotation_font=dict(color=WARNING, size=10))
    fig.update_layout(**PLOTLY, height=200,
                      xaxis=dict(**GRID), yaxis=dict(**GRID, ticksuffix="%"))
    return fig


def _corr_fig(result: dict) -> go.Figure:
    tickers = result["tickers"]
    rets    = result["returns"]
    if not tickers or not rets:
        return go.Figure()
    df = pd.DataFrame({t: rets[t] for t in tickers if t in rets})
    if df.empty:
        return go.Figure()
    corr = df.corr().values
    text = [[f"{v:.2f}" for v in row] for row in corr]
    fig = go.Figure(go.Heatmap(
        z=corr, x=tickers, y=tickers,
        text=text, texttemplate="%{text}",
        colorscale=[[0, DANGER], [0.5, "#1c2128"], [1, SUCCESS]],
        zmin=-1, zmax=1, showscale=True,
        colorbar=dict(thickness=10, len=0.8,
                      tickfont=dict(color=MUTED, size=10),
                      title=dict(text="ρ", font=dict(color=MUTED))),
        textfont=dict(size=11, color=TEXT),
    ))
    fig.update_layout(**PLOTLY, height=300)
    fig.update_yaxes(autorange="reversed")
    return fig


def _frontier_fig(result: dict) -> go.Figure:
    fr = result["frontier"]
    opt = result["optimization"]
    fig = go.Figure()
    if fr["risk"] and fr["return"]:
        fig.add_trace(go.Scatter(
            x=[v * 100 for v in fr["risk"]],
            y=[v * 100 for v in fr["return"]],
            mode="lines", name="Frontier",
            line=dict(color=BLUE, width=2),
        ))

    colors = {"current": ACCENT, "max_sharpe": SUCCESS, "min_variance": WARNING, "black_litterman": BLUE}
    labels = {"current": "Current", "max_sharpe": "Max Sharpe", "min_variance": "Min Var", "black_litterman": "Black-Litterman"}
    for key, o in opt.items():
        if o["volatility"] is None or o["expected_return"] is None:
            continue
        fig.add_trace(go.Scatter(
            x=[o["volatility"] * 100], y=[o["expected_return"] * 100],
            mode="markers+text", name=labels.get(key, key),
            marker=dict(size=10, color=colors.get(key, TEXT), symbol="circle"),
            text=[labels.get(key, key)], textposition="top center",
            textfont=dict(size=10, color=colors.get(key, TEXT)),
        ))
    fig.update_layout(**PLOTLY, height=280,
                      xaxis=dict(**GRID, ticksuffix="%", title="Volatility"),
                      yaxis=dict(**GRID, ticksuffix="%", title="Return"))
    return fig


# ── Dashboard tab content ──────────────────────────────────────────────────────

_ALLOC_COLORS = [
    ACCENT, BLUE, SUCCESS, WARNING,
    "#9e6ede", "#e3b341", "#79c0ff", "#3d9970", "#f85149", "#58d68d",
]
_TICKER_COLORS = [
    ACCENT, BLUE, SUCCESS, WARNING,
    "#9e6ede", "#e3b341", "#79c0ff", "#3d9970", "#f85149", "#58d68d",
]

_OPT_DESCRIPTIONS = {
    "max_sharpe":      "Maximises risk-adjusted return — the highest return per unit of volatility (tangency portfolio).",
    "min_variance":    "Minimises portfolio volatility regardless of return — the lowest-risk feasible portfolio.",
    "black_litterman": "Blends market equilibrium weights with investor views for a Bayesian optimal allocation.",
}


def _cumret_fig(result: dict) -> go.Figure:
    pf_s  = result["series"].get("port_val",  {})
    bm_s  = result["series"].get("bench_val", {})
    bench = result["meta"]["benchmark"]
    fig   = go.Figure()
    if pf_s.get("dates") and pf_s.get("values"):
        base = pf_s["values"][0] or 1
        pct  = [(v / base - 1) * 100 if v is not None else None for v in pf_s["values"]]
        fig.add_trace(go.Scatter(x=pf_s["dates"], y=pct, name="Portfolio",
                                 line=dict(color=ACCENT, width=2)))
    if bm_s.get("dates") and bm_s.get("values"):
        base = bm_s["values"][0] or 1
        pct  = [(v / base - 1) * 100 if v is not None else None for v in bm_s["values"]]
        fig.add_trace(go.Scatter(x=bm_s["dates"], y=pct, name=bench,
                                 line=dict(color=BLUE, width=1.5, dash="dot")))
    fig.update_layout(**PLOTLY, height=250,
                      xaxis=dict(**GRID), yaxis=dict(**GRID, ticksuffix="%"))
    return fig


def _alloc_bar_rows(data: dict[str, float]) -> list:
    """Return HTML bar-list elements sorted by weight descending."""
    items = sorted(data.items(), key=lambda x: x[1], reverse=True)
    rows  = []
    for i, (label, w) in enumerate(items):
        pct   = w * 100
        color = _ALLOC_COLORS[i % len(_ALLOC_COLORS)]
        rows.append(html.Div([
            html.Div([
                html.Span(label,          style={"fontSize": "13px", "color": TEXT}),
                html.Span(f"{pct:.1f}%",  style={"fontSize": "13px", "color": MUTED, "fontWeight": "600"}),
            ], style={"display": "flex", "justifyContent": "space-between", "marginBottom": "5px"}),
            html.Div(
                html.Div(style={
                    "width":  f"{min(pct, 100):.1f}%",
                    "height": "5px",
                    "background": color,
                    "borderRadius": "3px",
                    "transition": "width 0.4s ease",
                }),
                style={"background": BORDER, "borderRadius": "3px",
                       "height": "5px", "marginBottom": "12px"},
            ),
        ]))
    return rows


def _fetch_alloc_data(result: dict) -> tuple[dict, dict]:
    """Return (sector_weights, region_weights) dicts keyed by name, value = portfolio weight."""
    import yfinance as yf
    tickers = result["tickers"]
    am      = result.get("asset_metrics", {})
    sector_w: dict[str, float] = {}
    region_w: dict[str, float] = {}
    for t in tickers:
        w = am.get(t, {}).get("weight", 0) or 0
        try:
            info    = yf.Ticker(t).info or {}
            sector  = info.get("sector")  or "Other"
            country = info.get("country") or "Other"
        except Exception:
            sector = country = "Other"
        sector_w[sector]  = sector_w.get(sector, 0)  + w
        region_w[country] = region_w.get(country, 0) + w
    return sector_w, region_w


def _build_allocation_panel(result: dict) -> html.Div:
    sector_w, region_w = _fetch_alloc_data(result)
    return html.Div([
        html.Div([
            html.Span("Allocation", className="chart-title"),
            dcc.RadioItems(
                id="alloc-type",
                options=[{"label": "Sector", "value": "sector"},
                         {"label": "Region", "value": "region"}],
                value="sector", inline=True,
                className="toggle-switch",
            ),
        ], className="chart-header"),
        html.Div(id="alloc-bars", children=_alloc_bar_rows(sector_w),
                 style={"padding": "4px 0"}),
        dcc.Store(id="alloc-sector-data", data=sector_w),
        dcc.Store(id="alloc-region-data", data=region_w),
    ], className="chart-panel", style={"minHeight": "200px"})


def _render_opt_content(strategy: str, result: dict) -> html.Div:
    opt     = result["optimization"]
    current = opt.get("current", {})
    target  = opt.get(strategy, {})
    tickers = result["tickers"]

    desc = html.Div(_OPT_DESCRIPTIONS.get(strategy, ""),
                    style={"fontSize": "12px", "color": MUTED,
                           "marginBottom": "14px", "lineHeight": "1.5"})

    # Metric delta cards
    def _delta_card(label: str, cur, tgt, is_pct: bool = True, higher_is_better: bool = True):
        if cur is None or tgt is None:
            return html.Div([html.Div(label, className="kpi-label"), html.Div("—", className="kpi-value")],
                            className="kpi-card")
        delta = tgt - cur
        fmt   = _p if is_pct else _n
        delta_str = f"{delta*100:+.1f}pp" if is_pct else f"{delta:+.2f}"
        good  = delta > 0 if higher_is_better else delta < 0
        color = SUCCESS if good else DANGER
        return html.Div([
            html.Div(label, className="kpi-label"),
            html.Div([
                html.Span(f"{fmt(cur)} ", style={"color": MUTED, "fontSize": "13px"}),
                html.Span("→ ", style={"color": DIM, "fontSize": "13px"}),
                html.Span(fmt(tgt),       style={"color": TEXT,  "fontSize": "20px", "fontWeight": "700"}),
            ], style={"marginBottom": "3px"}),
            html.Div(delta_str, style={"fontSize": "11px", "color": color, "fontWeight": "600"}),
        ], className="kpi-card")

    metric_row = html.Div([
        _delta_card("Expected return",   current.get("expected_return"), target.get("expected_return"), higher_is_better=True),
        _delta_card("Volatility",        current.get("volatility"),      target.get("volatility"),      higher_is_better=False),
        _delta_card("Sharpe ratio",      current.get("sharpe"),          target.get("sharpe"), is_pct=False, higher_is_better=True),
    ], style={"display": "grid", "gridTemplateColumns": "repeat(3,1fr)",
              "gap": "10px", "marginBottom": "16px"})

    # Weight bars — current (faded) + optimised (solid) overlay
    cur_weights = current.get("weights", {})
    tgt_weights = target.get("weights", {})

    weight_rows = [
        html.Div([
            html.Div([
                html.Span("■ ", style={"color": "rgba(200,200,200,0.25)", "fontSize": "10px"}),
                html.Span("Current", style={"fontSize": "10px", "color": MUTED}),
                html.Span("  ■ ", style={"color": ACCENT, "fontSize": "10px", "marginLeft": "10px"}),
                html.Span("Optimised", style={"fontSize": "10px", "color": MUTED}),
            ]),
            html.Span("Target %", style={"fontSize": "10px", "color": MUTED}),
        ], style={"display": "flex", "justifyContent": "space-between",
                  "marginBottom": "10px"}),
    ]
    for i, t in enumerate(tickers):
        cur_w = (cur_weights.get(t) or 0) * 100
        tgt_w = (tgt_weights.get(t) or 0) * 100
        color = _TICKER_COLORS[i % len(_TICKER_COLORS)]
        delta = tgt_w - cur_w
        delta_str  = f"{delta:+.1f}pp"
        delta_color = SUCCESS if delta > 0.5 else DANGER if delta < -0.5 else MUTED
        weight_rows.append(html.Div([
            # Ticker label
            html.Span(t, style={"fontSize": "12px", "fontWeight": "700",
                                "color": TEXT, "width": "52px", "flexShrink": "0"}),
            # Double bar track
            html.Div([
                # Current weight — faded background
                html.Div(style={
                    "position": "absolute", "left": "0", "top": "0",
                    "width": f"{min(cur_w, 100):.1f}%", "height": "100%",
                    "background": color, "opacity": "0.25", "borderRadius": "3px",
                }),
                # Optimised weight — solid foreground
                html.Div(style={
                    "position": "absolute", "left": "0", "top": "0",
                    "width": f"{min(tgt_w, 100):.1f}%", "height": "100%",
                    "background": color, "opacity": "1", "borderRadius": "3px",
                }),
            ], style={
                "flex": "1", "height": "8px", "background": BORDER,
                "borderRadius": "3px", "margin": "0 10px",
                "position": "relative",
            }),
            # Target % + delta
            html.Div([
                html.Span(f"{tgt_w:.1f}%", style={"fontSize": "12px", "color": TEXT,
                                                   "fontWeight": "600"}),
                html.Span(f" {delta_str}", style={"fontSize": "10px", "color": delta_color,
                                                   "marginLeft": "4px"}),
            ], style={"width": "72px", "textAlign": "right", "flexShrink": "0"}),
        ], style={"display": "flex", "alignItems": "center", "marginBottom": "10px"}))

    apply_btn = html.Button(
        "Apply optimised weights",
        id="opt-apply-btn",
        n_clicks=0,
        style={
            "width": "100%", "marginTop": "14px",
            "background": ACCENT, "color": "#fff",
            "border": "none", "borderRadius": "8px",
            "padding": "12px", "fontSize": "14px",
            "fontWeight": "700", "cursor": "pointer",
        },
    )

    return html.Div([desc, metric_row, *weight_rows, apply_btn])


def _build_optimization_panel(result: dict) -> html.Div:
    opt = result["optimization"]
    # Determine which strategies succeeded
    available = [k for k in ("max_sharpe", "min_variance", "black_litterman")
                 if opt.get(k, {}).get("weights")]
    if not available:
        return html.Div([
            html.Div([html.Span("Optimisation", className="chart-title")], className="chart-header"),
            html.Div("Optimisation failed — insufficient data or too few assets.",
                     className="pf-empty"),
        ], className="chart-panel")

    default = available[0]
    labels  = {"max_sharpe": "Max Sharpe", "min_variance": "Min Variance",
               "black_litterman": "Black-Litterman"}

    return html.Div([
        html.Div([
            html.Span("Optimisation", className="chart-title"),
            dcc.RadioItems(
                id="opt-strategy",
                options=[{"label": labels[k], "value": k} for k in available],
                value=default, inline=True,
                className="toggle-switch",
            ),
        ], className="chart-header"),
        html.Div(id="opt-display", children=_render_opt_content(default, result)),
        dcc.Store(id="opt-result-store", data=result),
    ], className="chart-panel")


def _kpi(label, value, sub="", color=TEXT, tooltip=""):
    return html.Div([
        html.Div([
            html.Div(label, className="kpi-label"),
            html.I("i", className="mc-info", **{"data-tooltip": tooltip}) if tooltip else None,
        ], style={"display": "flex", "justifyContent": "space-between", "alignItems": "flex-start"}),
        html.Div(value, className="kpi-value", style={"color": color}),
        html.Div(sub, className="kpi-sub") if sub else None,
    ], className="kpi-card")


_METRIC_TOOLTIPS: dict[str, str] = {
    "Expected Return (ann.)":   "Mean daily return × 252 trading days",
    "CAGR":                     "Compound Annual Growth Rate over the full period",
    "CAPM Expected Return":     "Risk-free rate + Beta × (market return − risk-free rate)",
    "Volatility (ann.)":        "Standard deviation of daily returns × √252",
    "Sharpe Ratio":             "(Ann. return − risk-free rate) / Ann. volatility",
    "Sortino Ratio":            "Sharpe but denominator uses downside deviation only",
    "Beta":                     "Covariance(portfolio, benchmark) / Variance(benchmark)",
    "Max Drawdown":             "Largest peak-to-trough decline over the full period",
    "VaR 95 %":                 "Worst daily loss at 95% confidence (historical)",
    "CVaR (ES)":                "Average loss in the worst 5% of days (Expected Shortfall)",
    "Number of Assets":         "Total number of tickers in the portfolio",
    "Avg Correlation":          "Average pairwise correlation across all asset pairs",
    "Diversification Score":    "1 − average correlation; higher = better diversified",
    "Health Score":             "Composite 0–100: return, risk, diversification, drawdown",
}


def _mc_card(label, value, sub="", color=TEXT, danger_sub=False):
    tooltip = _METRIC_TOOLTIPS.get(label, sub)
    return html.Div([
        html.Div([
            html.Span(label, className="mc-label"),
            html.I("i", className="mc-info", **{"data-tooltip": tooltip}),
        ], className="mc-header"),
        html.Div(value, className="mc-value", style={"color": color}),
        html.Div(sub, className=f"mc-sub{'  danger' if danger_sub else ''}") if sub else None,
    ], className="mc")


def _section_header(title, color=ACCENT):
    return html.Div([
        html.Div(className="section-bar", style={"background": color}),
        html.Span(title, className="section-label", style={"color": color}),
    ], className="section-header")


def build_dashboard(result: dict, period: str = "All") -> html.Div:
    s  = result["scalars"]
    rf = s.get("portfolio_expected_return_capm")
    bench = result["meta"]["benchmark"]

    # Combined KPI strip (2 rows of 7)
    hs      = s.get("health_score", 0)
    pv      = s.get("portfolio_volatility") or 1
    sr      = s.get("sharpe_ratio") or 0
    so      = s.get("sortino_ratio") or 0
    mdd     = s.get("max_drawdown") or 0
    rf_label = f"rf {(result['meta'].get('rf_rate') or 0.025) * 100:.1f}%"
    kpi = html.Div([
        _kpi("CAGR",          _p(s.get("portfolio_cagr")),                   "compounded annual",   _c(s.get("portfolio_cagr"), 0.08, 0.02),  "Compound Annual Growth Rate over the full period"),
        _kpi("Ann. Return",   _p(s.get("portfolio_return")),                 "daily mean × 252",    _c(s.get("portfolio_return"), 0.08, 0.02), "Mean daily return × 252 trading days"),
        _kpi("CAPM Return",   _p(s.get("portfolio_expected_return_capm")),   rf_label,              TEXT,                                      "Risk-free rate + Beta × (market return − risk-free rate)"),
        _kpi("Volatility",    _p(pv),                                        "σ annualised",        SUCCESS if pv < 0.15 else WARNING if pv < 0.25 else DANGER, "Standard deviation of daily returns × √252"),
        _kpi("Sharpe",        _n(sr),                                        rf_label,              _c(sr, 1.0, 0.5),  "(Ann. return − risk-free rate) / Ann. volatility"),
        _kpi("Sortino",       _n(so),                                        "downside-adjusted",   _c(so, 1.0, 0.5),  "Sharpe but denominator uses downside deviation only"),
        _kpi("Beta",          _n(s.get("beta")),                             f"vs. {bench}",        TEXT,              f"Sensitivity to {bench} market moves; 1 = moves with market"),
        _kpi("Max DD",        _p(mdd),                                       "peak-to-trough",      DANGER if mdd < -0.20 else WARNING if mdd < -0.10 else SUCCESS, "Largest peak-to-trough decline in the period"),
        _kpi("VaR 95%",       _p(s.get("var_95")),                          "historical · 95%",    TEXT,              "Worst expected daily loss 95% of the time (historical method)"),
        _kpi("CVaR (ES)",     _p(s.get("cvar")),                            "expected shortfall",   TEXT,              "Average loss on days worse than the 95% VaR threshold"),
        _kpi("Health",        f"{hs} / 100",                                 "composite score",     SUCCESS if hs >= 60 else WARNING if hs >= 35 else DANGER, "Composite 0–100: return, risk, diversification, drawdown"),
        _kpi("# Assets",      str(result["meta"]["n_assets"]),               "tickers",             TEXT,              "Number of distinct tickers in the portfolio"),
        _kpi("Avg ρ",         _n(s.get("avg_correlation")),                  "avg pairwise",        _c(-(s.get("avg_correlation") or 0), -0.5, -0.75), "Average pairwise Pearson correlation between assets"),
        _kpi("Diversif.",     _n(s.get("diversification_score") or 0, 3),   "lower ρ = higher",    TEXT,              "Ratio of weighted avg vol to portfolio vol; higher = more diversified"),
    ], className="kpi-strip")

    # Performance chart
    perf = html.Div([
        html.Div([
            html.Span("Growth from €10,000", className="chart-title"),
            dcc.RadioItems(
                id="perf-period",
                options=[{"label": p, "value": p} for p in ["1M", "3M", "6M", "YTD", "1Y", "All"]],
                value=period,
                className="period-strip",
                inline=True,
            ),
        ], className="chart-header"),
        dcc.Graph(id="perf-chart", figure=_perf_fig(result, period),
                  config={"displayModeBar": False}),
    ], className="chart-panel")

    # Cumulative return (% rebased)
    cumret = html.Div([
        html.Div([html.Span("Cumulative Return (rebased to period start)", className="chart-title")],
                 className="chart-header"),
        dcc.Graph(figure=_cumret_fig(result), config={"displayModeBar": False}),
    ], className="chart-panel")

    # Drawdown + Rolling vol
    chart_row = html.Div([
        html.Div([
            html.Div([html.Span("Drawdown", className="chart-title")], className="chart-header"),
            dcc.Graph(figure=_dd_fig(result), config={"displayModeBar": False}),
        ], className="chart-panel"),
        html.Div([
            html.Div([html.Span("Rolling Volatility (252d)", className="chart-title")], className="chart-header"),
            dcc.Graph(figure=_rollvol_fig(result), config={"displayModeBar": False}),
        ], className="chart-panel"),
    ], className="chart-row")

    # Correlation matrix + Allocation side by side
    corr_row = html.Div([
        html.Div([
            html.Div([html.Span("Correlation Matrix", className="chart-title")], className="chart-header"),
            dcc.Graph(figure=_corr_fig(result), config={"displayModeBar": False}),
        ], className="chart-panel"),
        _build_allocation_panel(result),
    ], className="chart-row")

    # Efficient frontier + Optimisation
    frontier = html.Div([
        html.Div([
            html.Div([
                html.Div([html.Span("Efficient Frontier", className="chart-title")], className="chart-header"),
                dcc.Graph(figure=_frontier_fig(result), config={"displayModeBar": False}),
            ], className="chart-panel"),
            _build_optimization_panel(result),
        ], className="chart-row"),
    ])

    return html.Div([kpi, frontier, perf, cumret, chart_row, corr_row])


# ── Allocation + Optimisation callbacks ───────────────────────────────────────

@callback(
    Output("alloc-bars", "children"),
    Input("alloc-type", "value"),
    State("alloc-sector-data", "data"),
    State("alloc-region-data", "data"),
    prevent_initial_call=True,
)
def update_alloc_bars(alloc_type, sector_data, region_data):
    data = sector_data if alloc_type == "sector" else (region_data or {})
    return _alloc_bar_rows(data)


@callback(
    Output("opt-display", "children"),
    Input("opt-strategy", "value"),
    State("opt-result-store", "data"),
    prevent_initial_call=True,
)
def update_opt_display(strategy, result):
    if not result or not strategy:
        return no_update
    return _render_opt_content(strategy, result)


@callback(
    Output("pf-store", "data", allow_duplicate=True),
    Output("pf-analyse-status", "children", allow_duplicate=True),
    Input("opt-apply-btn", "n_clicks"),
    State("opt-strategy", "value"),
    State("opt-result-store", "data"),
    State("pf-store", "data"),
    prevent_initial_call=True,
)
def apply_opt_weights(n, strategy, result, pf_data):
    if not n or not result or not strategy:
        return no_update, no_update
    weights = result["optimization"].get(strategy, {}).get("weights", {})
    if not weights:
        return no_update, html.Span("No optimised weights available.", style={"color": DANGER})
    new_pf = dict(pf_data or {})
    new_pf["weights"] = weights
    label = {"max_sharpe": "Max Sharpe", "min_variance": "Min Variance",
             "black_litterman": "Black-Litterman"}.get(strategy, strategy)
    return new_pf, html.Span(f"✓ {label} weights applied — click Analyse Portfolio to refresh.",
                              style={"color": SUCCESS})


# ── Asset Analysis tab ─────────────────────────────────────────────────────────

def build_asset_analysis(result: dict) -> html.Div:
    am = result["asset_metrics"]
    tickers = result["tickers"]
    bench = result["meta"]["benchmark"]

    if not am:
        return html.Div("No asset data.", className="pf-empty")

    rows = []
    for t in tickers:
        m = am.get(t, {})
        w = (m.get("weight") or 0)
        rows.append(html.Tr([
            html.Td(t, className="ticker-cell"),
            html.Td(f"{w * 100:.1f}%",          className="num"),
            html.Td(f"€{m.get('latest_price') or 0:,.2f}", className="num"),
            html.Td(_p(m.get("cagr")),           className="num", style={"color": _c(m.get("cagr"), 0.08, 0.02)}),
            html.Td(_p(m.get("annualized_return")), className="num", style={"color": _c(m.get("annualized_return"), 0.08, 0.02)}),
            html.Td(_p(m.get("volatility")),     className="num"),
            html.Td(_n(m.get("sharpe")),         className="num", style={"color": _c(m.get("sharpe"), 1.0, 0.5)}),
            html.Td(_n(m.get("sortino")),        className="num", style={"color": _c(m.get("sortino"), 1.0, 0.5)}),
            html.Td(_n(m.get("beta")),           className="num"),
            html.Td(_p(m.get("max_drawdown")),   className="num", style={"color": DANGER}),
            html.Td(_p(m.get("var_95")),         className="num"),
            html.Td(f"{(m.get('benchmark_correlation') or 0):.2f}", className="num"),
        ]))

    return html.Div([
        html.Div([html.Span("Per-Asset Metrics", className="chart-title"),
                  html.Span(f"  benchmark: {bench}", style={"fontSize": "11px", "color": MUTED, "marginLeft": "10px"})],
                 className="chart-header"),
        html.Div(html.Table([
            html.Thead(html.Tr([
                html.Th("Ticker"), html.Th("Weight"), html.Th("Price"),
                html.Th("CAGR"), html.Th("Ann. Ret."), html.Th("Vol"),
                html.Th("Sharpe"), html.Th("Sortino"), html.Th("Beta"),
                html.Th("Max DD"), html.Th("VaR 95%"), html.Th("ρ Bench"),
            ])),
            html.Tbody(rows),
        ], className="data-table"), style={"overflowX": "auto"}),
    ], className="chart-panel")


# ── Monte Carlo tab ────────────────────────────────────────────────────────────

def build_monte_carlo(result: dict) -> html.Div:
    import numpy as np

    s = result["scalars"]
    ann_ret = s.get("portfolio_return") or 0.07
    ann_vol = s.get("portfolio_volatility") or 0.15
    n_sims  = 500
    n_years = 10
    n_days  = int(n_years * 252)

    np.random.seed(42)
    daily_ret = ann_ret / 252
    daily_vol = ann_vol / (252 ** 0.5)
    returns   = np.random.normal(daily_ret, daily_vol, (n_days, n_sims))
    paths     = 10_000 * np.cumprod(1 + returns, axis=0)

    pct5   = float(np.percentile(paths[-1], 5))
    pct50  = float(np.percentile(paths[-1], 50))
    pct95  = float(np.percentile(paths[-1], 95))

    fig = go.Figure()
    for i in range(min(80, n_sims)):
        fig.add_trace(go.Scatter(
            y=paths[:, i], mode="lines",
            line=dict(width=0.4, color=f"rgba(102,165,247,0.15)"),
            showlegend=False, hoverinfo="skip",
        ))
    fig.add_trace(go.Scatter(y=np.percentile(paths, 5,  axis=1), name="5th pct",
                             line=dict(color=DANGER, width=2, dash="dot")))
    fig.add_trace(go.Scatter(y=np.percentile(paths, 50, axis=1), name="Median",
                             line=dict(color=ACCENT, width=2.5)))
    fig.add_trace(go.Scatter(y=np.percentile(paths, 95, axis=1), name="95th pct",
                             line=dict(color=SUCCESS, width=2, dash="dot")))
    fig.update_layout(**PLOTLY, height=350,
                      xaxis=dict(**GRID, title="Trading days"),
                      yaxis=dict(**GRID, tickprefix="€"))

    return html.Div([
        html.Div([
            html.Span(f"Monte Carlo — {n_sims} simulations, {n_years}-year horizon", className="chart-title"),
            html.Span(f"  μ={ann_ret*100:.1f}%  σ={ann_vol*100:.1f}%",
                      style={"fontSize": "11px", "color": MUTED, "marginLeft": "10px"}),
        ], className="chart-header"),
        dcc.Graph(figure=fig, config={"displayModeBar": False}),
        html.Div([
            html.Div([html.Div("5th pct", className="kpi-label"), html.Div(f"€{pct5:,.0f}", className="kpi-value", style={"color": DANGER}), html.Div("worst-case", className="kpi-sub")], className="kpi-card"),
            html.Div([html.Div("Median", className="kpi-label"), html.Div(f"€{pct50:,.0f}", className="kpi-value", style={"color": ACCENT}), html.Div("expected", className="kpi-sub")], className="kpi-card"),
            html.Div([html.Div("95th pct", className="kpi-label"), html.Div(f"€{pct95:,.0f}", className="kpi-value", style={"color": SUCCESS}), html.Div("best-case", className="kpi-sub")], className="kpi-card"),
        ], style={"display": "grid", "gridTemplateColumns": "repeat(3,1fr)", "gap": "10px", "marginTop": "14px"}),
    ], className="chart-panel")


# ── Empty state ────────────────────────────────────────────────────────────────

def _empty_state() -> html.Div:
    return html.Div([
        html.Div("📊", className="empty-state-icon"),
        html.Div("No portfolio analysed yet", className="empty-state-title"),
        html.Div("Add tickers in the sidebar, then click Analyse Portfolio.", className="empty-state-sub"),
    ], className="empty-state")


# ── Callbacks ─────────────────────────────────────────────────────────────────

@callback(
    Output("pf-store", "data", allow_duplicate=True),
    Input("pf-add-btn", "n_clicks"),
    State("pf-ticker-dropdown", "value"),
    State("pf-store", "data"),
    prevent_initial_call=True,
)
def add_ticker(n, selected, pf_data):
    if not n or not selected:
        return no_update
    from utils.ticker_suggestions import extract_ticker
    ticker = extract_ticker(selected).upper()
    pf_data = dict(pf_data or {})
    tickers = list(pf_data.get("tickers", []))
    weights = dict(pf_data.get("weights", {}))
    if ticker in tickers:
        return no_update
    tickers.append(ticker)
    n_t = len(tickers)
    weights = {t: 1.0 / n_t for t in tickers}
    pf_data["tickers"] = tickers
    pf_data["weights"] = weights
    return pf_data


@callback(
    Output("pf-store", "data", allow_duplicate=True),
    Input("pf-remove-btn", "n_clicks"),
    State("pf-remove-dropdown", "value"),
    State("pf-store", "data"),
    prevent_initial_call=True,
)
def remove_ticker(n, ticker, pf_data):
    if not n or not ticker:
        return no_update
    pf_data = dict(pf_data or {})
    tickers = [t for t in pf_data.get("tickers", []) if t != ticker]
    weights = {t: 1.0 / len(tickers) for t in tickers} if tickers else {}
    pf_data["tickers"] = tickers
    pf_data["weights"] = weights
    return pf_data


@callback(
    Output("pf-store", "data", allow_duplicate=True),
    Input("pf-equalweight-btn", "n_clicks"),
    State("pf-store", "data"),
    prevent_initial_call=True,
)
def equal_weight(n, pf_data):
    if not n:
        return no_update
    pf_data = dict(pf_data or {})
    tickers = pf_data.get("tickers", [])
    if not tickers:
        return no_update
    pf_data["weights"] = {t: 1.0 / len(tickers) for t in tickers}
    return pf_data


@callback(
    Output("pf-store", "data", allow_duplicate=True),
    Input("pf-normalize-btn", "n_clicks"),
    State("pf-store", "data"),
    prevent_initial_call=True,
)
def normalize_weights(n, pf_data):
    if not n:
        return no_update
    pf_data = dict(pf_data or {})
    weights = dict(pf_data.get("weights", {}))
    total = sum(weights.values())
    if total > 0:
        pf_data["weights"] = {t: w / total for t, w in weights.items()}
    return pf_data


@callback(
    Output("pf-store", "data", allow_duplicate=True),
    Input({"type": "pf-weight-input", "index": ALL}, "value"),
    State({"type": "pf-weight-input", "index": ALL}, "id"),
    State("pf-store", "data"),
    prevent_initial_call=True,
)
def update_weights_from_inputs(values, ids, pf_data):
    if not ids:
        return no_update
    pf_data = dict(pf_data or {})
    weights = dict(pf_data.get("weights", {}))
    for id_dict, val in zip(ids, values):
        t = id_dict["index"]
        weights[t] = (val or 0) / 100.0
    pf_data["weights"] = weights
    return pf_data


@callback(
    Output("pf-store", "data", allow_duplicate=True),
    Input("pf-benchmark-select", "value"),
    Input("pf-period-select", "value"),
    Input("pf-rfrate-select", "value"),
    State("pf-store", "data"),
    prevent_initial_call=True,
)
def update_settings(benchmark, period, rf_rate, pf_data):
    pf_data = dict(pf_data or {})
    if benchmark: pf_data["benchmark"] = benchmark
    if period:    pf_data["period"]    = period
    if rf_rate is not None: pf_data["rf_rate"] = float(rf_rate)
    return pf_data


@callback(
    Output("pf-sidebar", "children"),
    Input("pf-store", "data"),
)
def refresh_sidebar(pf_data):
    return portfolio_sidebar(pf_data).children


@callback(
    Output("result-store", "data"),
    Output("pf-analyse-status", "children"),
    Input("pf-analyse-btn", "n_clicks"),
    State("pf-store", "data"),
    prevent_initial_call=True,
)
def run_portfolio_analysis(n, pf_data):
    if not n or not pf_data:
        return no_update, no_update
    result, err = run_analysis(pf_data)
    if err:
        return no_update, html.Span(f"⚠ {err}", style={"color": DANGER})
    meta = result["meta"]
    status = f"{meta['n_assets']} assets · {meta['period']} · {meta['benchmark']}"
    if meta.get("failed_tickers"):
        status += f" · failed: {', '.join(meta['failed_tickers'])}"
    return result, html.Span(status, style={"color": MUTED})


@callback(
    Output("portfolio-tab-content", "children"),
    Output("pf-header-meta", "children"),
    Input("portfolio-tabs", "value"),
    Input("result-store", "data"),
)
def render_portfolio_tab(tab, result):
    if result is None:
        meta = ""
        content = _empty_state()
    else:
        m = result["meta"]
        meta = f"Period: {m['period']}  ·  Benchmark: {m['benchmark']}  ·  {m['n_assets']} assets"
        try:
            if tab == "tab-dashboard":
                content = build_dashboard(result)
            elif tab == "tab-asset":
                content = build_asset_analysis(result)
            else:
                content = build_monte_carlo(result)
        except Exception as exc:
            content = html.Div(f"Render error: {exc}",
                               style={"color": DANGER, "padding": "16px", "fontSize": "13px"})
    return content, meta


@callback(
    Output("perf-chart", "figure"),
    Input("perf-period", "value"),
    State("result-store", "data"),
    prevent_initial_call=True,
)
def update_perf_chart(period, result):
    if not result:
        return go.Figure()
    return _perf_fig(result, period)
