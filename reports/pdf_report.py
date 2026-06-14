"""PDF report generator — investor-grade portfolio analysis report.

Uses ReportLab PLATYPUS for layout. Charts are rendered to PNG with
matplotlib's Agg backend and embedded as images. The report uses a
light professional theme (navy/accent-red on white) suitable for printing.
"""

from __future__ import annotations

import math
from datetime import date
from io import BytesIO
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import seaborn as sns

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, mm
from reportlab.platypus import (
    HRFlowable, Image, PageBreak, Paragraph,
    SimpleDocTemplate, Spacer, Table, TableStyle,
)

from analytics.scenario import run_scenario_analysis
from models.results import AnalysisResult

# ── Page geometry ──────────────────────────────────────────────────────────────
PAGE_W, PAGE_H = A4
MARGIN     = 2.0 * cm
CONTENT_W  = PAGE_W - 2 * MARGIN

# ── Color palette (light theme for print) ─────────────────────────────────────
_NAVY    = colors.HexColor("#0f3460")
_NAVY2   = colors.HexColor("#1a3a6b")
_RED     = colors.HexColor("#e94560")
_LIGHT   = colors.HexColor("#f2f5fa")
_BORDER  = colors.HexColor("#d0d5dd")
_TEXT    = colors.HexColor("#1a1a2e")
_SUB     = colors.HexColor("#616161")
_SUCCESS = colors.HexColor("#2e7d32")
_DANGER  = colors.HexColor("#c62828")
_WHITE   = colors.white

# ── Paragraph styles ───────────────────────────────────────────────────────────
_BASE = getSampleStyleSheet()

def _ps(**kw) -> ParagraphStyle:
    return ParagraphStyle("_", parent=_BASE["Normal"], **kw)

_H1      = _ps(fontSize=20, textColor=_NAVY, fontName="Helvetica-Bold",
               spaceAfter=4*mm, spaceBefore=6*mm)
_H2      = _ps(fontSize=13, textColor=_NAVY, fontName="Helvetica-Bold",
               spaceAfter=3*mm, spaceBefore=8*mm)
_H3      = _ps(fontSize=10, textColor=_NAVY2, fontName="Helvetica-Bold",
               spaceAfter=2*mm, spaceBefore=4*mm)
_BODY    = _ps(fontSize=9,  textColor=_TEXT,  spaceAfter=2*mm)
_SMALL   = _ps(fontSize=8,  textColor=_SUB)
_CAPTION = _ps(fontSize=8,  textColor=_SUB,   alignment=TA_CENTER, spaceAfter=3*mm)


# ── ReportLab table style ──────────────────────────────────────────────────────

def _tbl(has_header: bool = True) -> TableStyle:
    cmds = [
        ("FONTNAME",    (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE",    (0, 0), (-1, -1), 8),
        ("TOPPADDING",  (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("GRID",        (0, 0), (-1, -1), 0.5, _BORDER),
        ("VALIGN",      (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1 if has_header else 0), (-1, -1),
         [_WHITE, _LIGHT]),
    ]
    if has_header:
        cmds += [
            ("BACKGROUND", (0, 0), (-1, 0), _NAVY),
            ("TEXTCOLOR",  (0, 0), (-1, 0), _WHITE),
            ("FONTNAME",   (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE",   (0, 0), (-1, 0), 8),
            ("ALIGN",      (0, 0), (-1, 0), "CENTER"),
        ]
    return TableStyle(cmds)


def _hr() -> HRFlowable:
    return HRFlowable(width="100%", thickness=1, color=_NAVY, spaceAfter=3*mm)


# ── Formatting helpers ─────────────────────────────────────────────────────────

def _pct(v: float, dec: int = 2) -> str:
    return "—" if math.isnan(v) else f"{v * 100:.{dec}f} %"


def _num(v: float, dec: int = 2) -> str:
    return "—" if math.isnan(v) else f"{v:.{dec}f}"


def _eur(v: float) -> str:
    return "—" if math.isnan(v) else f"€ {v:,.0f}"


# ── Chart → Image helpers ──────────────────────────────────────────────────────

_NAVY_MPL = "#0f3460"   # same hue as _NAVY but as a plain string for matplotlib


def _lighten(ax: plt.Axes, fig: plt.Figure) -> None:
    """Convert a dark-theme matplotlib axes to a print-friendly light theme."""
    fig.patch.set_facecolor("white")
    ax.set_facecolor("#f8f9fa")
    ax.tick_params(colors="#333333", labelcolor="#333333")
    ax.xaxis.label.set_color("#333333")
    ax.yaxis.label.set_color("#333333")
    ax.title.set_color(_NAVY_MPL)
    for spine in ax.spines.values():
        spine.set_color("#cccccc")
    ax.grid(True, color="#e8e8e8", linewidth=0.5)
    leg = ax.get_legend()
    if leg:
        leg.get_frame().set_facecolor("white")
        leg.get_frame().set_edgecolor("#cccccc")
        for txt in leg.get_texts():
            txt.set_color("#333333")


def _ax_to_img(
    draw_fn,
    width_cm: float,
    height_cm: float,
    *args,
    **kwargs,
) -> Image:
    """Render a chart function to a ReportLab Image."""
    fig_w = width_cm / 2.54
    fig_h = height_cm / 2.54
    fig, ax = plt.subplots(figsize=(fig_w, fig_h), facecolor="white")
    try:
        draw_fn(ax, *args, **kwargs)
    except Exception:
        ax.text(0.5, 0.5, "Chart unavailable", transform=ax.transAxes,
                ha="center", va="center", color="#aaaaaa", fontsize=9)
    _lighten(ax, fig)
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight",
                facecolor="white")
    plt.close(fig)
    buf.seek(0)
    return Image(buf, width=width_cm * cm, height=height_cm * cm)


def _two_ax_to_img(
    draw_fn_left,
    draw_fn_right,
    width_cm: float,
    height_cm: float,
    left_args: tuple = (),
    right_args: tuple = (),
) -> Image:
    """Render two chart functions side-by-side into one Image."""
    fig_w = width_cm / 2.54
    fig_h = height_cm / 2.54
    fig, (ax_l, ax_r) = plt.subplots(1, 2, figsize=(fig_w, fig_h),
                                      facecolor="white")
    for draw_fn, ax, args in [
        (draw_fn_left, ax_l, left_args),
        (draw_fn_right, ax_r, right_args),
    ]:
        try:
            draw_fn(ax, *args)
        except Exception:
            ax.text(0.5, 0.5, "Chart unavailable", transform=ax.transAxes,
                    ha="center", va="center", color="#aaaaaa", fontsize=9)
        _lighten(ax, fig)
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight",
                facecolor="white")
    plt.close(fig)
    buf.seek(0)
    return Image(buf, width=width_cm * cm, height=height_cm * cm)


def _seaborn_corr_img(returns, width_cm: float, height_cm: float) -> Image:
    """Correlation heatmap for PDF (seaborn, light theme)."""
    fig_w = width_cm / 2.54
    fig_h = height_cm / 2.54
    fig, ax = plt.subplots(figsize=(fig_w, fig_h), facecolor="white")
    corr = returns.corr(numeric_only=False)
    n = corr.shape[0]
    sns.heatmap(
        corr, ax=ax, annot=(n <= 12), fmt=".2f",
        cmap="RdYlGn", vmin=-1.0, vmax=1.0,
        linewidths=0.5, linecolor="#dddddd",
        annot_kws={"size": 7},
        cbar_kws={"shrink": 0.8},
    )
    ax.set_title("Correlation Matrix", fontsize=10, color="#0f3460")
    ax.tick_params(labelcolor="#333333")
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    buf.seek(0)
    return Image(buf, width=width_cm * cm, height=height_cm * cm)


def _scenario_bar_img(scenarios, start_val: float,
                      width_cm: float, height_cm: float) -> Image:
    """Scenario bar chart for PDF."""
    SC_COLORS = {
        "Bull Market":    "#4caf50",
        "Mild Recession": "#ff9800",
        "Recession":      "#f44336",
        "Severe Crash":   "#880e4f",
    }
    fig_w = width_cm / 2.54
    fig_h = height_cm / 2.54
    fig, ax = plt.subplots(figsize=(fig_w, fig_h), facecolor="white")
    names  = [s.name for s in scenarios]
    values = [s.new_value for s in scenarios]
    clrs   = [SC_COLORS.get(n, "#0f3460") for n in names]
    bars   = ax.barh(names, values, color=clrs, edgecolor="none", height=0.55)
    ax.axvline(start_val, color="#2e7d32", linewidth=1.2, linestyle="--",
               label=f"Baseline {_eur(start_val)}")
    for bar, val in zip(bars, values):
        ax.text(bar.get_width() + start_val * 0.005,
                bar.get_y() + bar.get_height() / 2,
                _eur(val), va="center", fontsize=8, color="#333333")
    ax.set_xlabel("Portfolio Value (€)", fontsize=9, color="#333333")
    ax.set_title("Portfolio Value under Stress Scenarios", fontsize=10, color="#0f3460")
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"€{v:,.0f}"))
    ax.legend(fontsize=8)
    ax.set_facecolor("#f8f9fa")
    fig.patch.set_facecolor("white")
    ax.tick_params(colors="#333333", labelcolor="#333333")
    for spine in ax.spines.values():
        spine.set_color("#cccccc")
    ax.grid(True, axis="x", color="#e8e8e8", linewidth=0.5)
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    buf.seek(0)
    return Image(buf, width=width_cm * cm, height=height_cm * cm)


# ── Page header / footer callback ──────────────────────────────────────────────

def _make_page_template(portfolio_name: str):
    def _on_page(canvas, doc):
        canvas.saveState()
        # Top rule
        canvas.setStrokeColor(_NAVY)
        canvas.setLineWidth(1.5)
        canvas.line(MARGIN, PAGE_H - 1.4 * cm, PAGE_W - MARGIN, PAGE_H - 1.4 * cm)
        # Portfolio name in header
        canvas.setFont("Helvetica-Bold", 8)
        canvas.setFillColor(_NAVY)
        canvas.drawString(MARGIN, PAGE_H - 1.1 * cm, portfolio_name)
        # Date top-right
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(_SUB)
        canvas.drawRightString(PAGE_W - MARGIN, PAGE_H - 1.1 * cm,
                               date.today().isoformat())
        # Bottom rule + page number
        canvas.setStrokeColor(_BORDER)
        canvas.setLineWidth(0.5)
        canvas.line(MARGIN, 1.2 * cm, PAGE_W - MARGIN, 1.2 * cm)
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(_SUB)
        canvas.drawCentredString(PAGE_W / 2, 0.8 * cm, f"Page {canvas.getPageNumber()}")
        canvas.restoreState()
    return _on_page


# ── Report sections ────────────────────────────────────────────────────────────

def _section_cover(story, result: AnalysisResult) -> None:
    portfolio = result.portfolio
    name      = portfolio.name      if portfolio else "Portfolio"
    period    = portfolio.period    if portfolio else "?"
    benchmark = portfolio.benchmark if portfolio else "?"

    story.append(Spacer(1, 3 * cm))
    story.append(Paragraph("Portfolio Analysis Report", _H1))
    story.append(_hr())
    story.append(Spacer(1, 5 * mm))

    meta = [
        ["Portfolio", name],
        ["Benchmark", benchmark],
        ["Analysis Period", period],
        ["Report Date", date.today().strftime("%d %B %Y")],
        ["# Assets", str(len(result.asset_metrics))],
    ]
    tbl = Table(meta, colWidths=[5 * cm, 10 * cm])
    tbl.setStyle(TableStyle([
        ("FONTNAME",  (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME",  (1, 0), (1, -1), "Helvetica"),
        ("FONTSIZE",  (0, 0), (-1, -1), 10),
        ("TEXTCOLOR", (0, 0), (0, -1), _NAVY),
        ("TEXTCOLOR", (1, 0), (1, -1), _TEXT),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LINEBELOW", (0, 0), (-1, -2), 0.5, _BORDER),
    ]))
    story.append(tbl)
    story.append(PageBreak())


def _section_metrics(story, result: AnalysisResult) -> None:
    story.append(Paragraph("Portfolio Metrics", _H2))

    rows = [
        # (label, value, note)
        ["Metric", "Value", "Note"],
        ["Expected Return (ann.)", _pct(result.portfolio_return), "Historical avg × 252"],
        ["CAGR", _pct(result.portfolio_cagr), "Compound annual growth"],
        ["CAPM Expected Return", _pct(result.portfolio_expected_return_capm), "Risk-free + β × ERP"],
        ["Volatility (ann.)", _pct(result.portfolio_volatility), "std(r_daily) × √252"],
        ["Sharpe Ratio", _num(result.sharpe_ratio), "(Return − Rf) / Vol"],
        ["Sortino Ratio", _num(result.sortino_ratio), "(Return − Rf) / Downside dev"],
        ["Beta", _num(result.beta), "Cov(p, bench) / Var(bench)"],
        ["Max Drawdown", _pct(result.max_drawdown), "Peak-to-trough loss"],
        ["VaR 95 %", _pct(result.var_95), "Daily 95% historical VaR"],
        ["VaR 99 %", _pct(result.var_99), "Daily 99% historical VaR"],
        ["CVaR (95 %)", _pct(result.cvar), "Expected Shortfall"],
        ["Avg Pairwise Correlation", _num(result.avg_correlation), ""],
        ["Diversification Score", _num(result.diversification_score), "0 = none, 1 = max"],
    ]
    col_w = [CONTENT_W * 0.40, CONTENT_W * 0.25, CONTENT_W * 0.35]
    tbl = Table(rows, colWidths=col_w)
    tbl.setStyle(_tbl())
    story.append(tbl)
    story.append(Spacer(1, 5 * mm))


def _section_assets(story, result: AnalysisResult) -> None:
    story.append(Paragraph("Asset Analysis", _H2))

    headers = [
        "Ticker", "Weight", "CAGR", "Return",
        "Vol", "Sharpe", "Beta", "Max DD", "VaR 95%",
    ]
    rows = [headers]
    for m in result.asset_metrics.values():
        rows.append([
            m.ticker,
            _pct(m.weight),
            _pct(m.cagr),
            _pct(m.annualized_return),
            _pct(m.volatility),
            _num(m.sharpe),
            _num(m.beta),
            _pct(m.max_drawdown),
            _pct(m.var_95),
        ])

    n = len(headers)
    col_w = [CONTENT_W / n] * n
    col_w[0] = 2.5 * cm   # wider ticker column
    tbl = Table(rows, colWidths=col_w)
    tbl.setStyle(_tbl())
    story.append(tbl)
    story.append(Spacer(1, 5 * mm))


def _section_optimization(story, result: AnalysisResult) -> None:
    story.append(Paragraph("Portfolio Optimization", _H2))

    opt_map = [
        ("max_sharpe",      "Maximum Sharpe Portfolio"),
        ("min_variance",    "Minimum Variance Portfolio"),
        ("black_litterman", "Black-Litterman Portfolio"),
    ]
    current = result.optimization.get("current")
    tickers = (
        list(current.weights.keys())
        if current and current.weights
        else list(result.asset_metrics.keys())
    )

    for key, label in opt_map:
        opt = result.optimization.get(key)
        story.append(Paragraph(label, _H3))

        # Weight table
        w_rows = [["Ticker", "Current Weight", "Optimized Weight", "Δ Weight"]]
        for ticker in tickers:
            cw = current.weights.get(ticker, 0.0) if current else 0.0
            ow = opt.weights.get(ticker, 0.0) if (opt and opt.weights) else 0.0
            w_rows.append([ticker, _pct(cw), _pct(ow), f"{(ow - cw) * 100:+.2f} %"])
        wt = Table(w_rows, colWidths=[3*cm, 4*cm, 4*cm, 4*cm])
        wt.setStyle(_tbl())
        story.append(wt)
        story.append(Spacer(1, 3*mm))

        # Metric comparison
        metric_defs = [
            ("Expected Return",  lambda o: _pct(o.expected_return)),
            ("Volatility",       lambda o: _pct(o.volatility)),
            ("Sharpe",           lambda o: _num(o.sharpe)),
            ("Beta",             lambda o: _num(o.beta)),
            ("VaR 95 %",         lambda o: _pct(o.var_95)),
            ("Max Drawdown",     lambda o: _pct(o.max_drawdown)),
        ]
        m_rows = [["Metric", "Current", "Optimized"]]
        for mlabel, fn in metric_defs:
            m_rows.append([mlabel, fn(current) if current else "—",
                           fn(opt) if opt else "—"])
        mt = Table(m_rows, colWidths=[5*cm, 4*cm, 4*cm])
        mt.setStyle(_tbl())
        story.append(mt)
        story.append(Spacer(1, 5*mm))


def _section_charts(story, result: AnalysisResult) -> None:
    story.append(Paragraph("Portfolio Visualizations", _H2))

    from charts.growth import draw_growth_chart
    from charts.drawdown import draw_drawdown_chart
    from charts.rolling_vol import draw_rolling_vol_chart
    from charts.risk_contribution import draw_risk_contribution_chart, draw_return_contribution_chart
    from charts.frontier import draw_frontier_chart

    bench_label = result.portfolio.benchmark if result.portfolio else "Benchmark"
    port_label  = result.portfolio.name      if result.portfolio else "Portfolio"

    # Growth chart
    if not result.portfolio_value_series.empty:
        story.append(Paragraph("Growth of €10,000", _H3))
        img = _ax_to_img(
            draw_growth_chart,
            CONTENT_W / cm, 7.0,
            result.portfolio_value_series,
            result.benchmark_value_series,
            portfolio_label=port_label,
            benchmark_label=bench_label,
        )
        story.append(img)
        story.append(Paragraph(
            "Historical portfolio growth vs benchmark starting from €10,000.", _CAPTION
        ))

    # Frontier + Drawdown side by side
    half = (CONTENT_W / 2 - 3*mm) / cm
    story.append(Paragraph("Efficient Frontier &amp; Drawdown", _H3))

    def _draw_frontier(ax):
        draw_frontier_chart(
            ax,
            result.frontier_risk,
            result.frontier_return,
            current=result.optimization.get("current"),
            max_sharpe_result=result.optimization.get("max_sharpe"),
            min_variance_result=result.optimization.get("min_variance"),
            black_litterman_result=result.optimization.get("black_litterman"),
        )

    def _draw_dd(ax):
        draw_drawdown_chart(ax, result.drawdown_series)

    img_pair = _two_ax_to_img(
        _draw_frontier, _draw_dd,
        CONTENT_W / cm, 7.0,
        left_args=(), right_args=(),
    )
    story.append(img_pair)
    story.append(Paragraph(
        "Left: Efficient Frontier with current and optimised portfolios marked.  "
        "Right: Historical peak-to-trough drawdown of the portfolio.", _CAPTION
    ))

    # Rolling volatility
    if not result.rolling_volatility_series.dropna().empty:
        story.append(Paragraph("Rolling 12-Month Volatility", _H3))
        img = _ax_to_img(
            draw_rolling_vol_chart,
            CONTENT_W / cm, 6.0,
            result.rolling_volatility_series,
        )
        story.append(img)
        story.append(Paragraph(
            "Annualised portfolio volatility computed over a rolling 252-day window.", _CAPTION
        ))

    # Risk & return contribution
    rc = {t: m.risk_contribution for t, m in result.asset_metrics.items()
          if not math.isnan(m.risk_contribution)}
    ret_c = {t: m.return_contribution for t, m in result.asset_metrics.items()
             if not math.isnan(m.return_contribution)}
    if rc and ret_c:
        story.append(Paragraph("Risk &amp; Return Contribution", _H3))
        img_contrib = _two_ax_to_img(
            draw_risk_contribution_chart,
            draw_return_contribution_chart,
            CONTENT_W / cm, 5.5,
            left_args=(rc,),
            right_args=(ret_c,),
        )
        story.append(img_contrib)
        story.append(Paragraph(
            "Left: each asset's marginal contribution to total portfolio risk. "
            "Right: weighted return contribution per asset.", _CAPTION
        ))


def _section_correlation(story, result: AnalysisResult) -> None:
    if result.returns.empty:
        return
    story.append(Paragraph("Correlation Analysis", _H2))
    img = _seaborn_corr_img(result.returns, CONTENT_W / cm, 8.0)
    story.append(img)
    story.append(Paragraph(
        "Pearson correlation matrix of daily asset returns over the analysis period.", _CAPTION
    ))


def _section_scenarios(story, result: AnalysisResult) -> None:
    story.append(Paragraph("Scenario Analysis", _H2))
    story.append(Paragraph(
        "Beta-weighted CAPM stress tests: each scenario applies a market-level shock. "
        "Stressed volatility uses a correlation-surge model where pairwise correlations "
        "increase toward 1 in severe downturns.",
        _BODY,
    ))

    try:
        weights = {t: m.weight for t, m in result.asset_metrics.items()}
        start_val = float(result.portfolio_value_series.iloc[-1]) \
            if not result.portfolio_value_series.empty else 10_000.0
        scenarios = run_scenario_analysis(
            result.returns, weights, result.benchmark_returns, start_value=start_val,
        )
    except Exception:
        story.append(Paragraph("Scenario data unavailable.", _SMALL))
        return

    rows = [["Scenario", "Market Return", "Portfolio Return",
             "New Value (€)", "Change", "Stressed Vol"]]
    for sc in scenarios:
        rows.append([
            sc.name,
            _pct(sc.market_return),
            _pct(sc.portfolio_return),
            _eur(sc.new_value),
            f"{sc.new_value - start_val:+,.0f} €",
            _pct(sc.stressed_vol),
        ])

    col_w = [4*cm, 3*cm, 3.5*cm, 3.5*cm, 3*cm, 3*cm]
    tbl = Table(rows, colWidths=col_w)
    style = _tbl()
    # Colour positive/negative scenario rows
    for i, sc in enumerate(scenarios, start=1):
        if sc.portfolio_return >= 0:
            style.add("TEXTCOLOR", (0, i), (-1, i), _SUCCESS)
        else:
            style.add("TEXTCOLOR", (0, i), (-1, i), _DANGER)
    tbl.setStyle(style)
    story.append(tbl)
    story.append(Spacer(1, 4*mm))

    img = _scenario_bar_img(scenarios, start_val, CONTENT_W / cm, 7.0)
    story.append(img)


# ── Public API ─────────────────────────────────────────────────────────────────

def export_portfolio_pdf(result: AnalysisResult, path: Path) -> None:
    """Generate a professional investor-grade PDF portfolio report.

    Sections: Cover · Metrics · Assets · Optimization ·
              Visualizations · Correlation · Scenarios

    Args:
        result: Full AnalysisResult from the analysis engine.
        path:   Destination .pdf file path.
    """
    portfolio  = result.portfolio
    port_name  = portfolio.name if portfolio else "Portfolio"
    on_page    = _make_page_template(port_name)

    doc = SimpleDocTemplate(
        str(path),
        pagesize=A4,
        topMargin=1.8 * cm,
        bottomMargin=1.8 * cm,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
    )

    story: list = []
    _section_cover(story, result)
    _section_metrics(story, result)
    _section_assets(story, result)
    story.append(PageBreak())
    _section_optimization(story, result)
    story.append(PageBreak())
    _section_charts(story, result)
    story.append(PageBreak())
    _section_correlation(story, result)
    story.append(PageBreak())
    _section_scenarios(story, result)

    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
