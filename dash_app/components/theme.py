"""Shared colour constants and Plotly layout defaults."""

BG     = "#0d1117"
CARD   = "#161b22"
BORDER = "#30363d"
ACCENT = "#66a5f7"
BLUE   = "#58a6ff"
SUCCESS= "#3fb950"
DANGER = "#f85149"
WARNING= "#d29922"
TEXT   = "#c9d1d9"
MUTED  = "#8b949e"
DIM    = "#484f58"

PLOTLY = dict(
    paper_bgcolor=CARD,
    plot_bgcolor=CARD,
    font=dict(family="Inter, -apple-system, sans-serif", color=TEXT, size=11),
    margin=dict(l=10, r=10, t=10, b=10),
    legend=dict(bgcolor="rgba(0,0,0,0)", bordercolor=BORDER, font=dict(size=11)),
)

GRID = dict(gridcolor="#1c2128", zerolinecolor=BORDER, linecolor=BORDER)


def color_metric(v: float, good: float, warn: float) -> str:
    import math
    if math.isnan(v):
        return MUTED
    return SUCCESS if v > good else WARNING if v > warn else DANGER
