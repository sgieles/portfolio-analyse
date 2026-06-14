"""Dark theme: PySide6 stylesheet + matplotlib/seaborn style registration."""

import matplotlib
import matplotlib.pyplot as plt

# ── Colour palette ──────────────────────────────────────────────────────────
BG_PRIMARY   = "#1a1a2e"   # deepest background
BG_SECONDARY = "#16213e"   # panel / card background
BG_TERTIARY  = "#0f3460"   # subtle accent panels
ACCENT       = "#e94560"   # primary accent (red-pink)
ACCENT_BLUE  = "#533483"   # secondary accent (purple)
TEXT_PRIMARY  = "#eaeaea"
TEXT_SECONDARY = "#a0a0b0"
BORDER       = "#2a2a4a"
SUCCESS      = "#4caf50"
WARNING      = "#ff9800"
DANGER       = "#f44336"

# ── PySide6 stylesheet ───────────────────────────────────────────────────────
DARK_STYLESHEET = f"""
/* ─── Base ─────────────────────────────────────────── */
QWidget {{
    background-color: {BG_PRIMARY};
    color: {TEXT_PRIMARY};
    font-family: "Segoe UI", Arial, sans-serif;
    font-size: 13px;
}}

QMainWindow, QDialog {{
    background-color: {BG_PRIMARY};
}}

/* ─── Tab bar ──────────────────────────────────────── */
QTabWidget::pane {{
    border: 1px solid {BORDER};
    background-color: {BG_SECONDARY};
}}
QTabBar::tab {{
    background-color: {BG_TERTIARY};
    color: {TEXT_SECONDARY};
    padding: 8px 20px;
    margin-right: 2px;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
}}
QTabBar::tab:selected {{
    background-color: {ACCENT};
    color: {TEXT_PRIMARY};
    font-weight: bold;
}}
QTabBar::tab:hover:!selected {{
    background-color: {BG_SECONDARY};
    color: {TEXT_PRIMARY};
}}

/* ─── Push buttons ─────────────────────────────────── */
QPushButton {{
    background-color: {ACCENT};
    color: {TEXT_PRIMARY};
    border: none;
    padding: 6px 16px;
    border-radius: 4px;
    font-weight: bold;
}}
QPushButton:hover {{
    background-color: #c73652;
}}
QPushButton:pressed {{
    background-color: #a02840;
}}
QPushButton:disabled {{
    background-color: {BG_TERTIARY};
    color: {TEXT_SECONDARY};
}}
QPushButton[secondary="true"] {{
    background-color: {BG_TERTIARY};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER};
}}
QPushButton[secondary="true"]:hover {{
    background-color: {ACCENT_BLUE};
}}

/* ─── Line edits / combo boxes ─────────────────────── */
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
    background-color: {BG_SECONDARY};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER};
    border-radius: 4px;
    padding: 4px 8px;
}}
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {{
    border: 1px solid {ACCENT};
}}
QComboBox::drop-down {{
    border: none;
    padding-right: 8px;
}}
QComboBox QAbstractItemView {{
    background-color: {BG_SECONDARY};
    color: {TEXT_PRIMARY};
    selection-background-color: {ACCENT};
}}

/* ─── Tables ───────────────────────────────────────── */
QTableWidget, QTableView {{
    background-color: {BG_SECONDARY};
    color: {TEXT_PRIMARY};
    gridline-color: {BORDER};
    border: 1px solid {BORDER};
    border-radius: 4px;
}}
QHeaderView::section {{
    background-color: {BG_TERTIARY};
    color: {TEXT_PRIMARY};
    padding: 6px;
    border: none;
    border-right: 1px solid {BORDER};
    font-weight: bold;
}}
QTableWidget::item:selected, QTableView::item:selected {{
    background-color: {ACCENT_BLUE};
}}
QTableWidget::item:alternate {{
    background-color: #1e1e38;
}}

/* ─── Scroll bars ──────────────────────────────────── */
QScrollBar:vertical {{
    background: {BG_SECONDARY};
    width: 10px;
    border-radius: 5px;
}}
QScrollBar::handle:vertical {{
    background: {BG_TERTIARY};
    border-radius: 5px;
    min-height: 20px;
}}
QScrollBar::handle:vertical:hover {{
    background: {ACCENT};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}

/* ─── Group boxes / frames ─────────────────────────── */
QGroupBox {{
    border: 1px solid {BORDER};
    border-radius: 6px;
    margin-top: 12px;
    padding-top: 8px;
    font-weight: bold;
    color: {TEXT_SECONDARY};
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 6px;
    color: {ACCENT};
}}

/* ─── Labels ───────────────────────────────────────── */
QLabel {{
    color: {TEXT_PRIMARY};
    background: transparent;
}}
QLabel[heading="true"] {{
    font-size: 16px;
    font-weight: bold;
    color: {TEXT_PRIMARY};
}}
QLabel[subheading="true"] {{
    font-size: 13px;
    color: {TEXT_SECONDARY};
}}

/* ─── Splitter ─────────────────────────────────────── */
QSplitter::handle {{
    background: {BORDER};
}}

/* ─── Tooltip ──────────────────────────────────────── */
QToolTip {{
    background-color: {BG_TERTIARY};
    color: {TEXT_PRIMARY};
    border: 1px solid {ACCENT};
    padding: 4px;
    border-radius: 4px;
}}

/* ─── Status bar ───────────────────────────────────── */
QStatusBar {{
    background-color: {BG_TERTIARY};
    color: {TEXT_SECONDARY};
}}
"""


def apply_matplotlib_dark_style() -> None:
    """Register and activate a dark rcParams style matching the app palette."""
    matplotlib.rcParams.update({
        "figure.facecolor":  BG_SECONDARY,
        "axes.facecolor":    BG_PRIMARY,
        "axes.edgecolor":    BORDER,
        "axes.labelcolor":   TEXT_PRIMARY,
        "axes.titlecolor":   TEXT_PRIMARY,
        "axes.grid":         True,
        "grid.color":        BORDER,
        "grid.linewidth":    0.6,
        "text.color":        TEXT_PRIMARY,
        "xtick.color":       TEXT_SECONDARY,
        "ytick.color":       TEXT_SECONDARY,
        "xtick.labelcolor":  TEXT_SECONDARY,
        "ytick.labelcolor":  TEXT_SECONDARY,
        "legend.facecolor":  BG_SECONDARY,
        "legend.edgecolor":  BORDER,
        "legend.labelcolor": TEXT_PRIMARY,
        "lines.linewidth":   1.8,
        "patch.edgecolor":   BG_SECONDARY,
        "figure.dpi":        100,
        "savefig.dpi":       150,
        "font.family":       "sans-serif",
        "font.size":         10,
    })


# Colour cycle for multi-series charts
CHART_COLORS: list[str] = [
    "#e94560",  # accent red
    "#00b4d8",  # cyan
    "#90e0ef",  # light cyan
    "#48cae4",  # sky blue
    "#f77f00",  # orange
    "#4cc9f0",  # bright blue
    "#a8dadc",  # pale teal
    "#f4a261",  # warm orange
    "#2ec4b6",  # teal
    "#cbf3f0",  # near-white teal
]
