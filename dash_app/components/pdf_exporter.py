"""Generate a professional portfolio analysis PDF report using ReportLab."""

from __future__ import annotations

import io
import math
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    HRFlowable, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table,
    TableStyle,
)

# ── Dimensions ────────────────────────────────────────────────────────────────
_W, _H    = A4          # 595.27 × 841.89 pt
_MARGIN   = 1.8 * cm
_CW       = _W - 2 * _MARGIN   # usable content width ≈ 493 pt

# ── Palette (print-safe) ──────────────────────────────────────────────────────
_DARK    = colors.HexColor("#0d1117")
_NAVY    = colors.HexColor("#161b22")
_BLUE    = colors.HexColor("#1a56db")
_MUTED   = colors.HexColor("#8b949e")
_ROW_ALT = colors.HexColor("#f3f6fb")
_SUCCESS = colors.HexColor("#1a7f37")
_WARN    = colors.HexColor("#9a6700")
_DANGER  = colors.HexColor("#cf222e")
_WHITE   = colors.white
_BORDER  = colors.HexColor("#d0d7de")


# ── Styles ────────────────────────────────────────────────────────────────────

def _S() -> dict:
    return {
        "h1": ParagraphStyle("h1", fontSize=28, fontName="Helvetica-Bold",
                              textColor=_DARK, spaceAfter=6),
        "h2": ParagraphStyle("h2", fontSize=13, fontName="Helvetica-Bold",
                              textColor=_BLUE, spaceBefore=14, spaceAfter=5),
        "body": ParagraphStyle("body", fontSize=8.5, fontName="Helvetica",
                               textColor=_DARK, spaceAfter=4, leading=13),
        "meta": ParagraphStyle("meta", fontSize=9, fontName="Helvetica",
                               textColor=_MUTED, spaceAfter=3),
        "cover_name": ParagraphStyle("cover_name", fontSize=20,
                                     fontName="Helvetica-Bold", textColor=_BLUE,
                                     spaceAfter=10),
        "disclaimer": ParagraphStyle("disc", fontSize=7.5,
                                     fontName="Helvetica-Oblique",
                                     textColor=_MUTED, leading=11),
    }


# ── Helpers ───────────────────────────────────────────────────────────────────

def _pct(v, d=2) -> str:
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return "—"
    return f"{v * 100:+.{d}f}%"


def _num(v, d=2) -> str:
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return "—"
    return f"{v:.{d}f}"


def _hr(color=_BLUE, space_after=8) -> HRFlowable:
    return HRFlowable(width="100%", thickness=0.75, color=color,
                      spaceAfter=space_after, spaceBefore=2)


def _table(rows: list[list], col_widths: list[float],
           style_extra: list | None = None) -> Table:
    """Build a dark-header, alternating-row table."""
    tbl = Table(rows, colWidths=col_widths, repeatRows=1)
    style = [
        # Header
        ("BACKGROUND",   (0, 0), (-1, 0), _DARK),
        ("TEXTCOLOR",    (0, 0), (-1, 0), _WHITE),
        ("FONTNAME",     (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",     (0, 0), (-1, 0), 7.5),
        ("TOPPADDING",   (0, 0), (-1, 0), 6),
        ("BOTTOMPADDING",(0, 0), (-1, 0), 6),
        # Data rows
        ("FONTNAME",     (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE",     (0, 1), (-1, -1), 8),
        ("TOPPADDING",   (0, 1), (-1, -1), 4),
        ("BOTTOMPADDING",(0, 1), (-1, -1), 4),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [_WHITE, _ROW_ALT]),
        # Grid + padding
        ("GRID",         (0, 0), (-1, -1), 0.3, _BORDER),
        ("LEFTPADDING",  (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
    ]
    if style_extra:
        style.extend(style_extra)
    tbl.setStyle(TableStyle(style))
    return tbl


# ── Canvas callback — header / footer ────────────────────────────────────────

def _make_canvas_cb(pf_name: str, generated: str):
    def _draw(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(_MUTED)
        y = _MARGIN * 0.55
        canvas.drawString(_MARGIN, y, f"{pf_name}  •  Portfolio Analysis Report  •  {generated}")
        canvas.drawRightString(_W - _MARGIN, y, f"Page {doc.page}")
        canvas.restoreState()
    return _draw


# ── Section builders ──────────────────────────────────────────────────────────

def _cover(result: dict, pf_data: dict, st: dict) -> list:
    name     = result["meta"].get("pf_name") or (pf_data or {}).get("name", "Portfolio")
    period   = result["meta"]["period"]
    bench    = result["meta"]["benchmark"]
    rf       = (result["meta"].get("rf_rate") or 0.025) * 100
    tickers  = result.get("tickers", [])
    hs       = result["scalars"].get("health_score", 0)
    generated = datetime.now().strftime("%d %B %Y, %H:%M")

    summary_cw = [_CW * f for f in [0.2, 0.2, 0.2, 0.2, 0.2]]
    summary = _table(
        [
            ["Period", "Benchmark", "Risk-free Rate", "# Assets", "Health Score"],
            [period, bench, f"{rf:.1f}%", str(len(tickers)), f"{hs} / 100"],
        ],
        col_widths=summary_cw,
        style_extra=[("ALIGN", (0, 0), (-1, -1), "CENTER")],
    )

    return [
        Spacer(1, 2.5 * cm),
        Paragraph("PORTFOLIO ANALYSIS", st["h1"]),
        _hr(space_after=10),
        Paragraph(name, st["cover_name"]),
        Paragraph(f"Generated: {generated}", st["meta"]),
        Spacer(1, 0.8 * cm),
        summary,
        Spacer(1, 0.6 * cm),
        Paragraph(f"Tickers: {', '.join(tickers)}", st["meta"]),
        PageBreak(),
    ]


def _metrics_section(result: dict, st: dict) -> list:
    s     = result["scalars"]
    bench = result["meta"]["benchmark"]
    rf    = (result["meta"].get("rf_rate") or 0.025) * 100

    cw = [_CW * f for f in [0.42, 0.18, 0.40]]
    rows = [
        ["Metric", "Value", "Description"],
        ["CAGR",                  _pct(s.get("portfolio_cagr")),                   "Compound Annual Growth Rate over the full period"],
        ["Ann. Return",           _pct(s.get("portfolio_return")),                 "Mean daily return × 252 trading days"],
        ["CAPM Expected Return",  _pct(s.get("portfolio_expected_return_capm")),   f"rf = {rf:.1f}%, market = 10%"],
        ["Volatility (ann.)",     _pct(s.get("portfolio_volatility")),             "Std dev of daily returns × √252"],
        ["Sharpe Ratio",          _num(s.get("sharpe_ratio")),                     "(Ann. return − rf) / Volatility"],
        ["Sortino Ratio",         _num(s.get("sortino_ratio")),                    "Uses downside deviation only"],
        [f"Beta (vs {bench})",    _num(s.get("beta")),                             "Sensitivity to benchmark moves"],
        ["Max Drawdown",          _pct(s.get("max_drawdown")),                     "Largest peak-to-trough decline"],
        ["VaR 95%",               _pct(s.get("var_95")),                           "Historical, 1-day, 95% confidence"],
        ["CVaR (Expected Shortfall)", _pct(s.get("cvar")),                         "Avg loss beyond VaR threshold"],
        ["Health Score",          f"{s.get('health_score', 0)} / 100",            "Composite: return + risk + diversif."],
        ["Avg Correlation",       _num(s.get("avg_correlation")),                  "Average pairwise Pearson ρ"],
        ["Diversification Score", _num(s.get("diversification_score") or 0, 3),   "Higher = more diversified"],
    ]
    return [
        Paragraph("Key Performance Metrics", st["h2"]),
        _hr(),
        _table(rows, cw),
        Spacer(1, 0.4 * cm),
    ]


def _weights_section(result: dict, st: dict) -> list:
    tickers = result["tickers"]
    opt     = result["optimization"]
    cur_w   = opt.get("current", {}).get("weights", {})
    ms_w    = opt.get("max_sharpe", {}).get("weights", {})
    mv_w    = opt.get("min_variance", {}).get("weights", {})
    bl_w    = opt.get("black_litterman", {}).get("weights", {})

    cols = ["Ticker", "Current"]
    if ms_w: cols.append("Max Sharpe")
    if mv_w: cols.append("Min Variance")
    if bl_w: cols.append("Black-Litterman")

    n = len(cols)
    cw = [_CW * (0.22 if i == 0 else (0.78 / (n - 1))) for i in range(n)]

    rows = [cols]
    for t in tickers:
        row = [t, f"{cur_w.get(t, 0) * 100:.1f}%"]
        if ms_w: row.append(f"{ms_w.get(t, 0) * 100:.1f}%")
        if mv_w: row.append(f"{mv_w.get(t, 0) * 100:.1f}%")
        if bl_w: row.append(f"{bl_w.get(t, 0) * 100:.1f}%")
        rows.append(row)

    return [
        Paragraph("Asset Allocation", st["h2"]),
        _hr(),
        _table(rows, cw),
        Spacer(1, 0.4 * cm),
    ]


def _per_asset_section(result: dict, st: dict) -> list:
    tickers = result["tickers"]
    am      = result["asset_metrics"]

    cw = [_CW * f for f in [0.14, 0.14, 0.14, 0.12, 0.12, 0.12, 0.11, 0.11]]
    rows = [["Ticker", "CAGR", "Ann. Return", "Volatility", "Sharpe", "Beta", "Max DD", "VaR 95%"]]
    for t in tickers:
        m = am.get(t, {})
        rows.append([
            t,
            _pct(m.get("cagr")),
            _pct(m.get("annualized_return")),
            _pct(m.get("volatility")),
            _num(m.get("sharpe")),
            _num(m.get("beta")),
            _pct(m.get("max_drawdown")),
            _pct(m.get("var_95")),
        ])

    return [
        Paragraph("Per-Asset Metrics", st["h2"]),
        _hr(),
        _table(rows, cw),
        Spacer(1, 0.4 * cm),
    ]


def _optimization_section(result: dict, st: dict) -> list:
    opt    = result["optimization"]
    labels = {
        "current":         "Current Weights",
        "max_sharpe":      "Max Sharpe",
        "min_variance":    "Min Variance",
        "black_litterman": "Black-Litterman",
    }
    cw = [_CW * f for f in [0.30, 0.24, 0.23, 0.23]]
    rows = [["Strategy", "Expected Return", "Volatility", "Sharpe Ratio"]]
    for key, label in labels.items():
        d = opt.get(key, {})
        if not d or (key != "current" and not d.get("weights")):
            continue
        rows.append([label, _pct(d.get("expected_return")), _pct(d.get("volatility")), _num(d.get("sharpe"))])

    if len(rows) == 1:
        return []
    return [
        Paragraph("Portfolio Optimisation", st["h2"]),
        _hr(),
        _table(rows, cw),
        Spacer(1, 0.4 * cm),
    ]


def _scenario_section(result: dict, st: dict) -> list:
    scenarios = result.get("scenarios", [])
    if not scenarios:
        return []

    cw = [_CW * f for f in [0.34, 0.16, 0.17, 0.18, 0.15]]
    rows = [["Scenario", "Market Impact", "Portfolio Impact", "New Value (€10k)", "Stressed Vol"]]
    extra = []
    for i, sc in enumerate(scenarios, start=1):
        mkt = sc.get("market_return")
        prt = sc.get("portfolio_return")
        nv  = sc.get("new_value")
        sv  = sc.get("stressed_vol")
        rows.append([
            sc["name"],
            _pct(mkt),
            _pct(prt),
            f"€{nv:,.0f}" if nv is not None else "—",
            _pct(sv),
        ])
        if prt is not None:
            c = _SUCCESS if prt >= 0 else _DANGER
            extra += [("TEXTCOLOR", (2, i), (2, i), c),
                      ("FONTNAME",  (2, i), (2, i), "Helvetica-Bold")]

    return [
        PageBreak(),
        Paragraph("Stress-Test / Scenario Analysis", st["h2"]),
        _hr(),
        _table(rows, cw, style_extra=extra),
        Spacer(1, 0.4 * cm),
    ]


def _notes_section(result: dict, st: dict) -> list:
    bench  = result["meta"]["benchmark"]
    period = result["meta"]["period"]
    return [
        Spacer(1, 0.6 * cm),
        Paragraph("Notes & Methodology", st["h2"]),
        _hr(),
        Paragraph(
            "• Returns are calculated on Adjusted Close prices sourced from Yahoo Finance.<br/>"
            "• Annualised return = mean daily return × 252 trading days.<br/>"
            "• Volatility = standard deviation of daily returns × √252.<br/>"
            "• Sharpe Ratio = (Annualised Return − Risk-free Rate) / Annualised Volatility.<br/>"
            "• Sortino Ratio uses only downside deviation (negative daily returns) in the denominator.<br/>"
            "• Beta = Covariance(portfolio, benchmark) / Variance(benchmark) on daily returns.<br/>"
            "• Max Drawdown = largest peak-to-trough percentage decline over the full analysis period.<br/>"
            "• VaR 95% = worst expected daily loss at 95% confidence level (historical simulation).<br/>"
            "• CVaR (Expected Shortfall) = average loss on days worse than the 95% VaR threshold.<br/>"
            "• Health Score = composite 0–100 weighted across return, risk, diversification and drawdown.<br/>"
            f"• Benchmark: {bench}.  Analysis period: {period}.",
            st["body"],
        ),
        Spacer(1, 0.5 * cm),
        Paragraph(
            "This report is generated automatically from historical market data. "
            "Past performance is not indicative of future results. "
            "This document does not constitute investment advice.",
            st["disclaimer"],
        ),
    ]


# ── Public API ────────────────────────────────────────────────────────────────

def generate_pdf(result: dict, pf_data: dict | None = None) -> bytes:
    """Build portfolio analysis PDF and return raw bytes."""
    buf = io.BytesIO()
    pf_data = pf_data or {}
    name      = result["meta"].get("pf_name") or pf_data.get("name", "Portfolio")
    generated = datetime.now().strftime("%d %B %Y")
    cb        = _make_canvas_cb(name, generated)

    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=_MARGIN, rightMargin=_MARGIN,
        topMargin=_MARGIN, bottomMargin=_MARGIN + 0.6 * cm,
        title=f"{name} — Portfolio Analysis",
        author="Portfolio Analyser",
    )

    st    = _S()
    story = []
    story.extend(_cover(result, pf_data, st))
    story.extend(_metrics_section(result, st))
    story.extend(_weights_section(result, st))
    story.extend(_per_asset_section(result, st))
    story.extend(_optimization_section(result, st))
    story.extend(_scenario_section(result, st))
    story.extend(_notes_section(result, st))

    doc.build(story, onFirstPage=cb, onLaterPages=cb)
    return buf.getvalue()
