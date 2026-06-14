"""Warm/light theme constants and CSS for the Streamlit app.

Colour palette derived from mockup CSS variables:
  --bg      #f3efe7   main background (cream/beige)
  --surface #fffdf9   card / panel background
  --surface2 #f7f2ea  secondary surface
  --ink     #231d15   primary text (dark brown)
  --ink2    #6b6354   secondary text
  --line    #e6dfd1   borders / dividers
  --accent  #c2410c   orange-red / terracotta
  --pos     #2f7d57   forest green (positive)
  --neg     #b14223   dark red (negative)
"""

# ── Colour palette ─────────────────────────────────────────────────────────────
BG_PRIMARY    = "#f3efe7"   # main page background
BG_SECONDARY  = "#fffdf9"   # sidebar / card background
BG_TERTIARY   = "#f7f2ea"   # secondary surfaces (hover, alt rows)
ACCENT        = "#c2410c"   # orange-red / terracotta
TEXT_PRIMARY  = "#231d15"   # primary ink (dark brown)
TEXT_SECONDARY = "#6b6354"  # secondary ink (warm gray-brown)
BORDER        = "#e6dfd1"   # dividers and outlines
SUCCESS       = "#2f7d57"   # forest green
WARNING       = "#b58900"   # amber/gold
DANGER        = "#b14223"   # dark red-orange

# ── Plotly layout defaults ─────────────────────────────────────────────────────
PLOTLY_TEMPLATE = {
    "layout": {
        "paper_bgcolor": BG_SECONDARY,
        "plot_bgcolor":  BG_PRIMARY,
        "font":          {"color": TEXT_PRIMARY, "family": "-apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif"},
        "xaxis":         {"gridcolor": BORDER, "zerolinecolor": BORDER},
        "yaxis":         {"gridcolor": BORDER, "zerolinecolor": BORDER},
        "legend":        {"bgcolor": BG_SECONDARY, "bordercolor": BORDER},
        "colorway":      [ACCENT, "#2563eb", "#2f7d57", "#b58900", "#8b5cf6",
                          "#0ea5a4", "#64748b", "#f59e0b", "#3f6f8f"],
        "margin":        {"l": 48, "r": 20, "t": 44, "b": 40},
    }
}

# ── Streamlit page CSS ─────────────────────────────────────────────────────────
DARK_CSS = f"""
<style>
/* ─── Base ─────────────────────────────────────────────────────────── */
html, body, [class*="css"] {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif;
    background-color: {BG_PRIMARY};
    color: {TEXT_PRIMARY};
}}
.stApp {{
    background-color: {BG_PRIMARY};
}}

/* ─── Sidebar ───────────────────────────────────────────────────────── */
[data-testid="stSidebar"] {{
    background-color: {BG_SECONDARY};
    border-right: 1px solid {BORDER};
}}
[data-testid="stSidebar"] .stMarkdown h1,
[data-testid="stSidebar"] .stMarkdown h2,
[data-testid="stSidebar"] .stMarkdown h3 {{
    color: {ACCENT};
}}
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] .stMarkdown p,
[data-testid="stSidebar"] .stMarkdown span {{
    color: {TEXT_PRIMARY} !important;
}}

/* ─── Metric cards ──────────────────────────────────────────────────── */
[data-testid="metric-container"] {{
    background-color: {BG_SECONDARY};
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 12px 16px;
}}
[data-testid="stMetricLabel"] {{
    color: {TEXT_SECONDARY} !important;
    font-size: 11px !important;
    text-transform: uppercase;
    letter-spacing: 0.04em;
}}
[data-testid="stMetricValue"] {{
    color: {TEXT_PRIMARY} !important;
    font-size: 22px !important;
    font-weight: bold !important;
}}

/* ─── Buttons ───────────────────────────────────────────────────────── */
.stButton > button {{
    background-color: {ACCENT};
    color: #ffffff;
    border: none;
    border-radius: 6px;
    font-weight: 600;
    transition: background-color 0.15s;
}}
.stButton > button:hover {{
    background-color: #a33509;
    color: #ffffff;
    border: none;
}}
.stButton > button[kind="secondary"] {{
    background-color: {BG_TERTIARY};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER};
}}
.stButton > button[kind="secondary"]:hover {{
    background-color: {BORDER};
}}

/* ─── Inputs ────────────────────────────────────────────────────────── */
.stTextInput > div > input,
.stSelectbox > div > div,
.stNumberInput > div > input {{
    background-color: {BG_SECONDARY};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER};
    border-radius: 4px;
}}
.stTextInput > div > input:focus,
.stNumberInput > div > input:focus {{
    border-color: {ACCENT} !important;
    box-shadow: 0 0 0 2px rgba(194,65,12,0.15) !important;
}}

/* ─── Sliders ───────────────────────────────────────────────────────── */
.stSlider [data-baseweb="slider"] [data-testid="stTickBarMin"],
.stSlider [data-baseweb="slider"] [data-testid="stTickBarMax"] {{
    color: {TEXT_SECONDARY};
}}

/* ─── Dataframes / tables ───────────────────────────────────────────── */
.stDataFrame {{
    border: 1px solid {BORDER};
    border-radius: 6px;
    background-color: {BG_SECONDARY};
}}

/* ─── Section headers ───────────────────────────────────────────────── */
h1, h2, h3 {{
    color: {TEXT_PRIMARY};
    font-weight: 700;
}}
h1 span.accent {{
    color: {ACCENT};
}}

/* ─── Dividers ──────────────────────────────────────────────────────── */
hr {{
    border-color: {BORDER};
}}

/* ─── Tabs ──────────────────────────────────────────────────────────── */
.stTabs [data-baseweb="tab-list"] {{
    background-color: {BG_TERTIARY};
    border-radius: 6px;
    border: 1px solid {BORDER};
}}
.stTabs [data-baseweb="tab"] {{
    color: {TEXT_SECONDARY};
    font-weight: 600;
}}
.stTabs [aria-selected="true"] {{
    color: {ACCENT} !important;
    border-bottom: 2px solid {ACCENT};
    background-color: {BG_SECONDARY};
}}

/* ─── Info / warning / error boxes ─────────────────────────────────── */
.stAlert {{
    border-radius: 6px;
    border: 1px solid {BORDER};
}}
[data-testid="stInfoAlertContent"] {{
    color: {TEXT_PRIMARY};
}}

/* ─── Caption / small text ──────────────────────────────────────────── */
.stCaption, small {{
    color: {TEXT_SECONDARY} !important;
}}

/* ─── Spinner ───────────────────────────────────────────────────────── */
.stSpinner > div {{
    border-top-color: {ACCENT} !important;
}}

/* ─── File uploader ─────────────────────────────────────────────────── */
[data-testid="stFileUploader"] {{
    border: 1px dashed {BORDER};
    border-radius: 6px;
    background-color: {BG_TERTIARY};
}}

/* ─── Mobile / small screen ─────────────────────────────────────────────── */
@media (max-width: 768px) {{
    .block-container {{
        padding-left: 1rem !important;
        padding-right: 1rem !important;
    }}
    [data-testid="stMetricValue"] {{
        font-size: 18px !important;
    }}
    [data-testid="stRadio"] > div {{
        flex-wrap: wrap !important;
        gap: 4px !important;
    }}
    .stDownloadButton > button {{
        width: 100%;
    }}
    .stDataFrame {{
        overflow-x: auto;
    }}
}}

@media (max-width: 480px) {{
    h1 {{ font-size: 20px !important; }}
    h2 {{ font-size: 17px !important; }}
    h3 {{ font-size: 15px !important; }}
}}
</style>
"""
