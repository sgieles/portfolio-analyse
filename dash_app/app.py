"""Portfolio Analyser — Dash web application entry point.

Run:  python dash_app/app.py
Open: http://localhost:8050
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dash import Dash, Input, Output, State, callback, dcc, html

# ── App init ───────────────────────────────────────────────────────────────────
app = Dash(
    __name__,
    assets_folder=str(Path(__file__).parent / "assets"),
    suppress_callback_exceptions=True,
    title="Portfolio Analyser",
    meta_tags=[
        {"name": "viewport",                       "content": "width=device-width, initial-scale=1.0"},
        {"name": "apple-mobile-web-app-capable",   "content": "yes"},
        {"name": "apple-mobile-web-app-title",     "content": "PA"},
        {"name": "apple-mobile-web-app-status-bar-style", "content": "black-translucent"},
        {"name": "theme-color",                    "content": "#0d1117"},
    ],
)

# Add manifest + touch-icon links (Dash meta_tags only supports <meta>, not <link>)
app.index_string = """<!DOCTYPE html>
<html>
<head>
    {%metas%}
    <title>{%title%}</title>
    {%favicon%}
    {%css%}
    <link rel="manifest" href="/assets/manifest.json">
    <link rel="apple-touch-icon" href="/assets/apple-touch-icon.png">
</head>
<body>
    {%app_entry%}
    <footer>
        {%config%}
        {%scripts%}
        {%renderer%}
    </footer>
</body>
</html>"""
server = app.server  # for gunicorn / Streamlit Cloud

# Import layouts AFTER app is created so @callback decorators register correctly
from dash_app.layouts.portfolio_hub import portfolio_hub_layout  # noqa: E402
from dash_app.layouts.research_hub import research_hub_layout    # noqa: E402

# ── Default state ──────────────────────────────────────────────────────────────
_DEFAULT_PF: dict = {
    "tickers":   [],
    "weights":   {},
    "benchmark": "SPY",
    "period":    "5y",
    "rf_rate":   0.025,
    "name":      "My Portfolio",
}

# ── Header ─────────────────────────────────────────────────────────────────────

def _header() -> html.Div:
    return html.Div([
        html.Div([
            html.Span(["PA", html.Span("·")], className="logo-mark"),
            html.Span("Portfolio Analyser", className="logo-sub"),
        ], style={"display": "flex", "alignItems": "center", "gap": "10px"}),

        html.Nav([
            html.Button("Portfolio Hub", id="nav-portfolio", className="hub-tab active",
                        n_clicks=0),
            html.Button("Research Hub",  id="nav-research",  className="hub-tab",
                        n_clicks=0),
        ], className="hub-nav"),

        html.Div([
            html.Div(className="status-dot"),
            html.Span("Live data", className="status-label"),
        ], className="header-right"),
    ], className="app-header")


# ── Root layout ────────────────────────────────────────────────────────────────
app.layout = html.Div([
    dcc.Location(id="url", refresh=False),
    dcc.Store(id="pf-store",     storage_type="session", data=_DEFAULT_PF),
    dcc.Store(id="result-store", storage_type="memory"),
    _header(),
    html.Div(id="page-content"),
])

# ── Routing ────────────────────────────────────────────────────────────────────

@callback(
    Output("page-content",   "children"),
    Output("nav-portfolio",  "className"),
    Output("nav-research",   "className"),
    Input("url", "pathname"),
)
def route(pathname: str | None):
    if pathname and pathname.startswith("/research"):
        return research_hub_layout(), "hub-tab", "hub-tab active"
    return portfolio_hub_layout(), "hub-tab active", "hub-tab"


@callback(
    Output("url", "pathname", allow_duplicate=True),
    Input("nav-portfolio", "n_clicks"),
    prevent_initial_call=True,
)
def go_portfolio(n):
    return "/"


@callback(
    Output("url", "pathname", allow_duplicate=True),
    Input("nav-research", "n_clicks"),
    prevent_initial_call=True,
)
def go_research(n):
    return "/research"


# ── Entry point ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8050))
    debug = os.environ.get("DASH_DEBUG", "true").lower() == "true"
    app.run(debug=debug, port=port, host="0.0.0.0")
