"""Commodity analysis page — rendered on demand by the Research Hub."""

from __future__ import annotations

import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import plotly.graph_objects as go
from dash import dcc, html

from dash_app.components.theme import (
    ACCENT, BLUE, BORDER, CARD, DANGER, GRID, MUTED,
    PLOTLY, SUCCESS, TEXT, WARNING,
)

_NAN = float("nan")


# ── Formatting helpers ─────────────────────────────────────────────────────────

def _p(v) -> str:
    if v is None or (isinstance(v, float) and not math.isfinite(v)):
        return "—"
    return f"{v * 100:+.1f}%"


def _pp(v) -> str:
    """Format with colour suffix only (no sign)."""
    if v is None or (isinstance(v, float) and not math.isfinite(v)):
        return "—"
    return f"{v * 100:.1f}%"


def _fmt_price(v, unit: str) -> str:
    if v is None or (isinstance(v, float) and not math.isfinite(v)):
        return "—"
    return f"${v:,.2f} ({unit})"


# ── Score card ─────────────────────────────────────────────────────────────────

def _score_card(label: str, value, sub: str = "") -> html.Div:
    if value is None or (isinstance(value, float) and not math.isfinite(value)):
        disp, color = "—", MUTED
    else:
        v = float(value)
        disp  = f"{v:.0f}"
        color = SUCCESS if v >= 65 else WARNING if v >= 40 else DANGER
    return html.Div([
        html.Div(label, className="kpi-label"),
        html.Div(disp,  className="kpi-value", style={"color": color}),
        html.Div(sub,   className="kpi-sub") if sub else None,
    ], className="kpi-card")


def _ret_card(label: str, value) -> html.Div:
    if value is None or (isinstance(value, float) and not math.isfinite(value)):
        disp, color = "—", MUTED
    else:
        v = float(value)
        disp  = f"{v * 100:+.1f}%"
        color = SUCCESS if v > 0 else DANGER
    return html.Div([
        html.Div(label, className="kpi-label"),
        html.Div(disp,  className="kpi-value", style={"color": color}),
    ], className="kpi-card")


def _signal_color(signal: str) -> str:
    return {
        "Bullish":  SUCCESS,
        "Positive": "#58a6ff",
        "Neutral":  MUTED,
        "Negative": WARNING,
        "Bearish":  DANGER,
    }.get(signal, TEXT)


# ── Chart builders ─────────────────────────────────────────────────────────────

def _price_chart(history, name: str) -> go.Figure:
    close = history["Close"].dropna()
    dates = [str(d.date()) for d in close.index]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=dates, y=close.values,
        name=name, line=dict(color=ACCENT, width=2),
        fill="tozeroy", fillcolor="rgba(102,165,247,0.08)",
    ))

    # MA50 / MA200
    if len(close) >= 50:
        ma50 = close.rolling(50).mean()
        fig.add_trace(go.Scatter(
            x=dates, y=ma50.values,
            name="MA50", line=dict(color=BLUE, width=1.2, dash="dot"),
        ))
    if len(close) >= 200:
        ma200 = close.rolling(200).mean()
        fig.add_trace(go.Scatter(
            x=dates, y=ma200.values,
            name="MA200", line=dict(color=WARNING, width=1.2, dash="dot"),
        ))

    fig.update_layout(
        **PLOTLY, height=280,
        xaxis=dict(**GRID),
        yaxis=dict(**GRID),
        showlegend=True,
    )
    return fig


def _drawdown_chart(history) -> go.Figure:
    close = history["Close"].dropna()
    rets  = close.pct_change().dropna()
    cum   = (1 + rets).cumprod()
    peak  = cum.cummax()
    dd    = ((cum - peak) / peak) * 100
    dates = [str(d.date()) for d in dd.index]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=dates, y=dd.values,
        name="Drawdown", line=dict(color=DANGER, width=1.5),
        fill="tozeroy", fillcolor="rgba(248,81,73,0.12)",
    ))
    fig.update_layout(
        **PLOTLY, height=200,
        xaxis=dict(**GRID),
        yaxis=dict(**GRID, ticksuffix="%"),
    )
    return fig


def _seasonality_chart(monthly_avg: dict[str, float]) -> go.Figure:
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
              "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    values = [monthly_avg.get(m, 0) * 100 for m in months]
    colors = [SUCCESS if v >= 0 else DANGER for v in values]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=months, y=values,
        marker_color=colors, name="Avg monthly return",
    ))
    fig.update_layout(
        **PLOTLY, height=210,
        xaxis=dict(**GRID),
        yaxis=dict(**GRID, ticksuffix="%"),
        showlegend=False,
    )
    return fig


# ── Main renderer ──────────────────────────────────────────────────────────────

def render_commodity(ticker: str) -> html.Div:
    """Return the full commodity analysis page for *ticker*."""
    from research.data.commodity_fetcher import fetch_commodity_profile, fetch_commodity_history
    from research.analytics.commodity_scorer import score_commodity

    profile = fetch_commodity_profile(ticker)
    history = fetch_commodity_history(ticker, "5y")

    if history.empty:
        return html.Div([
            html.Div([
                html.Span(profile.name, className="company-name"),
                html.Span(ticker, className="company-ticker"),
            ], className="company-header"),
            html.Div(f"No price data available for {ticker}.", className="pf-empty"),
        ])

    analysis = score_commodity(
        ticker=ticker,
        name=profile.name,
        group=profile.group,
        unit=profile.unit,
        price_history=history,
    )

    sig_color = _signal_color(analysis.signal)

    # Header
    header = html.Div([
        html.Div([
            html.Span(profile.name, className="company-name"),
            html.Span(ticker, className="company-ticker"),
            html.Span(analysis.signal, style={
                "color": sig_color, "fontSize": "13px",
                "fontWeight": "600", "marginLeft": "10px",
            }),
        ]),
        html.Div(
            f"{profile.group} · {_fmt_price(analysis.current_price, profile.unit)}",
            className="company-meta",
        ),
    ], className="company-header")

    # Score cards
    score_row = html.Div([
        _score_card("Composite",  analysis.composite_score, analysis.signal),
        _score_card("Momentum",   analysis.momentum_score),
        _score_card("Trend",      analysis.trend_score),
        _score_card("Volatility", analysis.volatility_score),
    ], style={"display": "grid", "gridTemplateColumns": "repeat(4,1fr)",
              "gap": "10px", "marginBottom": "14px"})

    # Return cards
    ret_row = html.Div([
        _ret_card("1 Month",  analysis.return_1m),
        _ret_card("3 Months", analysis.return_3m),
        _ret_card("6 Months", analysis.return_6m),
        _ret_card("1 Year",   analysis.return_1y),
        _ret_card("3Y Ann.",  analysis.return_3y_ann),
        _ret_card("Max DD",   analysis.max_drawdown),
    ], style={"display": "grid", "gridTemplateColumns": "repeat(6,1fr)",
              "gap": "10px", "marginBottom": "14px"})

    # Trend indicator strip
    ma_items = []
    for label, above, val in [
        ("MA50", analysis.above_ma50, analysis.ma_50),
        ("MA200", analysis.above_ma200, analysis.ma_200),
        ("Golden Cross", analysis.golden_cross, None),
    ]:
        color = SUCCESS if above else DANGER
        tick  = "▲" if above else "▼"
        sub   = f"${val:,.1f}" if val and math.isfinite(val) else ""
        ma_items.append(html.Div([
            html.Span(tick + " ", style={"color": color}),
            html.Span(label, style={"fontWeight": "600"}),
            html.Span(f"  {sub}", style={"color": MUTED, "fontSize": "11px"}),
        ], style={"padding": "8px 12px", "background": CARD,
                  "border": f"1px solid {BORDER}", "borderRadius": "6px",
                  "fontSize": "13px", "color": color}))

    trend_row = html.Div(ma_items, style={
        "display": "flex", "gap": "10px", "marginBottom": "14px",
    })

    # Price chart
    price_panel = html.Div([
        html.Div([html.Span("Price History (5Y) + Moving Averages", className="chart-title")],
                 className="chart-header"),
        dcc.Graph(figure=_price_chart(history, profile.name),
                  config={"displayModeBar": False}),
    ], className="chart-panel")

    # Drawdown + Seasonality
    dd_panel = html.Div([
        html.Div([html.Span("Drawdown", className="chart-title")], className="chart-header"),
        dcc.Graph(figure=_drawdown_chart(history), config={"displayModeBar": False}),
    ], className="chart-panel")

    seas_panel = html.Div([
        html.Div([html.Span("Average Monthly Return (Seasonality)", className="chart-title")],
                 className="chart-header"),
        dcc.Graph(figure=_seasonality_chart(analysis.monthly_avg_returns),
                  config={"displayModeBar": False}),
    ], className="chart-panel")

    charts_row2 = html.Div([dd_panel, seas_panel], className="chart-row")

    # Strengths / Weaknesses
    def _bullets(items: list[str], color: str) -> html.Ul:
        return html.Ul([
            html.Li(i, style={"color": TEXT, "fontSize": "13px", "marginBottom": "5px"})
            for i in items
        ], style={"paddingLeft": "18px", "margin": "0"}) if items else html.Div("—", style={"color": MUTED})

    sw_panel = html.Div([
        html.Div([html.Span("Signals", className="chart-title")], className="chart-header"),
        html.Div([
            html.Div([
                html.Div("Strengths", style={"color": SUCCESS, "fontWeight": "600",
                                             "fontSize": "12px", "marginBottom": "6px"}),
                _bullets(analysis.strengths, SUCCESS),
            ], style={"flex": "1"}),
            html.Div([
                html.Div("Weaknesses", style={"color": DANGER, "fontWeight": "600",
                                              "fontSize": "12px", "marginBottom": "6px"}),
                _bullets(analysis.weaknesses, DANGER),
            ], style={"flex": "1"}),
        ], style={"display": "flex", "gap": "24px", "padding": "12px"}),
    ], className="chart-panel")

    return html.Div([
        header,
        score_row,
        ret_row,
        trend_row,
        price_panel,
        charts_row2,
        sw_panel,
    ])
