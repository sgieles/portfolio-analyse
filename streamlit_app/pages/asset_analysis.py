"""Asset Analysis page — per-asset metrics table and charts."""

from __future__ import annotations

import math

import plotly.graph_objects as go
import streamlit as st

from streamlit_app.state import session
from streamlit_app.styles.theme import (
    ACCENT, BG_PRIMARY, BG_SECONDARY, BG_TERTIARY, BORDER,
    DANGER, PLOTLY_TEMPLATE, SUCCESS, TEXT_PRIMARY, TEXT_SECONDARY, WARNING,
)


# ── Formatting ─────────────────────────────────────────────────────────────────

def _pct(v: float, dec: int = 2) -> str:
    return "—" if math.isnan(v) else f"{v * 100:.{dec}f}%"


def _num(v: float, dec: int = 2) -> str:
    return "—" if math.isnan(v) else f"{v:.{dec}f}"


def _eur(v: float) -> str:
    return "—" if math.isnan(v) else f"€ {v:,.2f}"


def _color_val(v: float, good_above: float, warn_above: float) -> str:
    if math.isnan(v):
        return TEXT_SECONDARY
    return SUCCESS if v > good_above else WARNING if v > warn_above else DANGER


# ── Plotly template ────────────────────────────────────────────────────────────

def _apply_template(fig: go.Figure, height: int = 320) -> go.Figure:
    t = PLOTLY_TEMPLATE["layout"]
    fig.update_layout(
        paper_bgcolor=t["paper_bgcolor"], plot_bgcolor=t["plot_bgcolor"],
        font=t["font"], margin=t["margin"], height=height,
        legend=dict(bgcolor=t["legend"]["bgcolor"], bordercolor=t["legend"]["bordercolor"]),
    )
    fig.update_xaxes(gridcolor=BORDER, zerolinecolor=BORDER, linecolor=BORDER)
    fig.update_yaxes(gridcolor=BORDER, zerolinecolor=BORDER, linecolor=BORDER)
    return fig


def _h3(text: str) -> None:
    st.markdown(
        f"<h3 style='color:{TEXT_PRIMARY}; margin:0 0 12px 0; font-size:17px;'>{text}</h3>",
        unsafe_allow_html=True,
    )


def _divider() -> None:
    st.markdown(
        f"<hr style='border:none; border-top:1px solid {BORDER}; margin:14px 0 20px 0;'>",
        unsafe_allow_html=True,
    )


# ── Dividend yield fetch (cached) ──────────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def _fetch_dividend_yields(tickers: tuple[str, ...]) -> dict[str, float]:
    """Return {ticker: dividend_yield} from yfinance info, cached 1h."""
    import yfinance as yf
    result: dict[str, float] = {}
    for t in tickers:
        try:
            info = yf.Ticker(t).info
            dy = info.get("dividendYield") or info.get("trailingAnnualDividendYield")
            result[t] = float(dy) if dy else float("nan")
        except Exception:
            result[t] = float("nan")
    return result


# ── Page ───────────────────────────────────────────────────────────────────────

def render() -> None:
    result = session.get_result()
    if result is None:
        st.info("Run an analysis on the Dashboard first.")
        return

    pf = result.portfolio
    tickers = list(result.asset_metrics.keys())

    st.caption(
        f"Period: **{pf.period}**  ·  Benchmark: **{pf.benchmark}**  ·  "
        f"{len(tickers)} assets"
    )

    # ── Fetch supplementary data ───────────────────────────────────────────────
    with st.spinner("Loading dividend data…"):
        div_yields = _fetch_dividend_yields(tuple(tickers))

    # ── Section 1: Summary metrics table ──────────────────────────────────────
    _h3("Asset Metrics")

    rows = []
    for t in tickers:
        m = result.asset_metrics[t]
        dy = div_yields.get(t, float("nan"))
        rows.append({
            "Ticker":        m.ticker,
            "Weight":        round(m.weight * 100, 2),
            "Price (€)":     round(m.latest_price, 2) if not math.isnan(m.latest_price) else None,
            "CAGR %":        round(m.cagr * 100, 2) if not math.isnan(m.cagr) else None,
            "Return % ann.": round(m.annualized_return * 100, 2) if not math.isnan(m.annualized_return) else None,
            "Volatility %":  round(m.volatility * 100, 2) if not math.isnan(m.volatility) else None,
            "Sharpe":        round(m.sharpe, 3) if not math.isnan(m.sharpe) else None,
            "Sortino":       round(m.sortino, 3) if not math.isnan(m.sortino) else None,
            "Beta":          round(m.beta, 3) if not math.isnan(m.beta) else None,
            "Corr. Bench.":  round(m.benchmark_correlation, 3) if not math.isnan(m.benchmark_correlation) else None,
            "Max DD %":      round(m.max_drawdown * 100, 2) if not math.isnan(m.max_drawdown) else None,
            "VaR 95 %":      round(m.var_95 * 100, 2) if not math.isnan(m.var_95) else None,
            "CVaR %":        round(m.cvar * 100, 2) if not math.isnan(m.cvar) else None,
            "Div. Yield %":  round(dy * 100, 2) if not math.isnan(dy) else None,
            "Risk Contrib %": round(m.risk_contribution * 100, 2) if not math.isnan(m.risk_contribution) else None,
            "Ret. Contrib %": round(m.return_contribution * 100, 2) if not math.isnan(m.return_contribution) else None,
        })

    st.dataframe(
        rows,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Weight":         st.column_config.NumberColumn("Weight %", format="%.2f %%"),
            "Price (€)":      st.column_config.NumberColumn("Price (€)", format="€ %.2f"),
            "CAGR %":         st.column_config.NumberColumn("CAGR %", format="%.2f %%"),
            "Return % ann.":  st.column_config.NumberColumn("Return % ann.", format="%.2f %%"),
            "Volatility %":   st.column_config.NumberColumn("Volatility %", format="%.2f %%"),
            "Sharpe":         st.column_config.NumberColumn("Sharpe", format="%.3f"),
            "Sortino":        st.column_config.NumberColumn("Sortino", format="%.3f"),
            "Beta":           st.column_config.NumberColumn("Beta", format="%.3f"),
            "Corr. Bench.":   st.column_config.NumberColumn("Corr. Bench.", format="%.3f"),
            "Max DD %":       st.column_config.NumberColumn("Max DD %", format="%.2f %%"),
            "VaR 95 %":       st.column_config.NumberColumn("VaR 95 %", format="%.2f %%"),
            "CVaR %":         st.column_config.NumberColumn("CVaR %", format="%.2f %%"),
            "Div. Yield %":   st.column_config.NumberColumn("Div. Yield %", format="%.2f %%"),
            "Risk Contrib %": st.column_config.NumberColumn("Risk Contrib %", format="%.2f %%"),
            "Ret. Contrib %": st.column_config.NumberColumn("Ret. Contrib %", format="%.2f %%"),
        },
    )

    _divider()

    # ── Section 2: Normalised price chart ─────────────────────────────────────
    _h3("Relative Performance (normalised to 100)")

    if not result.prices.empty:
        palette = [ACCENT, "#2563eb", SUCCESS, WARNING, "#8b5cf6",
                   "#0ea5a4", "#64748b", "#f59e0b", DANGER, "#3f6f8f"]
        fig_perf = go.Figure()
        for i, t in enumerate(tickers):
            s = result.prices[t].dropna()
            norm = s / s.iloc[0] * 100
            fig_perf.add_trace(go.Scatter(
                x=norm.index, y=norm.values, name=t,
                line=dict(color=palette[i % len(palette)], width=1.8),
            ))
        if not result.benchmark_prices.empty:
            b = result.benchmark_prices.dropna()
            b_norm = b / b.iloc[0] * 100
            fig_perf.add_trace(go.Scatter(
                x=b_norm.index, y=b_norm.values, name=pf.benchmark,
                line=dict(color=TEXT_SECONDARY, width=1.2, dash="dot"),
            ))
        fig_perf.add_hline(y=100, line_dash="dot", line_color=BORDER)
        fig_perf.update_layout(
            title=dict(text="Price Performance (start = 100)", font=dict(size=13, color=TEXT_PRIMARY)),
            yaxis_title="Index",
        )
        _apply_template(fig_perf, height=340)
        st.plotly_chart(fig_perf, use_container_width=True)

    _divider()

    # ── Section 3: Risk / Return scatter ──────────────────────────────────────
    _h3("Risk / Return Map")

    fig_rr = go.Figure()
    palette = [ACCENT, "#2563eb", SUCCESS, WARNING, "#8b5cf6",
               "#0ea5a4", "#64748b", "#f59e0b", DANGER, "#3f6f8f"]
    for i, t in enumerate(tickers):
        m = result.asset_metrics[t]
        if math.isnan(m.volatility) or math.isnan(m.annualized_return):
            continue
        size = max(10, m.weight * 120)
        fig_rr.add_trace(go.Scatter(
            x=[m.volatility * 100], y=[m.annualized_return * 100],
            mode="markers+text",
            name=t,
            marker=dict(color=palette[i % len(palette)], size=size,
                        line=dict(color=BG_SECONDARY, width=1.5)),
            text=[t], textposition="top center",
            textfont=dict(size=10, color=TEXT_PRIMARY),
            showlegend=False,
        ))
    # Add portfolio point
    if not math.isnan(result.portfolio_volatility):
        fig_rr.add_trace(go.Scatter(
            x=[result.portfolio_volatility * 100],
            y=[result.portfolio_return * 100],
            mode="markers+text", name="Portfolio",
            marker=dict(color=TEXT_PRIMARY, size=14, symbol="diamond",
                        line=dict(color=ACCENT, width=2)),
            text=["Portfolio"], textposition="top center",
            textfont=dict(size=11, color=TEXT_PRIMARY),
        ))
    fig_rr.update_layout(
        title=dict(text="Risk / Return (bubble size = portfolio weight)", font=dict(size=13, color=TEXT_PRIMARY)),
        xaxis_title="Volatility %", yaxis_title="Annualised Return %",
    )
    _apply_template(fig_rr, height=360)
    st.plotly_chart(fig_rr, use_container_width=True)

    _divider()

    # ── Section 4: Sharpe & Sortino bars ──────────────────────────────────────
    _h3("Risk-Adjusted Returns")

    bar_col1, bar_col2 = st.columns(2)
    sharpes  = [result.asset_metrics[t].sharpe  for t in tickers]
    sortinos = [result.asset_metrics[t].sortino for t in tickers]

    with bar_col1:
        s_colors = [SUCCESS if v > 1 else WARNING if v > 0.5 else DANGER for v in sharpes]
        fig_sh = go.Figure(go.Bar(
            x=tickers, y=sharpes, marker_color=s_colors,
            text=[f"{v:.2f}" if not math.isnan(v) else "—" for v in sharpes],
            textposition="outside", textfont=dict(color=TEXT_PRIMARY, size=11),
        ))
        fig_sh.add_hline(y=1, line_dash="dot", line_color=SUCCESS,
                         annotation_text="Good (1.0)", annotation_font_color=SUCCESS)
        fig_sh.update_layout(
            title=dict(text="Sharpe Ratio", font=dict(size=13, color=TEXT_PRIMARY)),
            bargap=0.3,
        )
        _apply_template(fig_sh, height=280)
        st.plotly_chart(fig_sh, use_container_width=True)

    with bar_col2:
        so_colors = [SUCCESS if v > 1 else WARNING if v > 0.5 else DANGER for v in sortinos]
        fig_so = go.Figure(go.Bar(
            x=tickers, y=sortinos, marker_color=so_colors,
            text=[f"{v:.2f}" if not math.isnan(v) else "—" for v in sortinos],
            textposition="outside", textfont=dict(color=TEXT_PRIMARY, size=11),
        ))
        fig_so.add_hline(y=1, line_dash="dot", line_color=SUCCESS,
                         annotation_text="Good (1.0)", annotation_font_color=SUCCESS)
        fig_so.update_layout(
            title=dict(text="Sortino Ratio", font=dict(size=13, color=TEXT_PRIMARY)),
            bargap=0.3,
        )
        _apply_template(fig_so, height=280)
        st.plotly_chart(fig_so, use_container_width=True)

    _divider()

    # ── Section 5: Benchmark correlation & Max Drawdown bars ──────────────────
    _h3("Correlation to Benchmark & Drawdown")

    corr_col, dd_col = st.columns(2)
    corrs = [result.asset_metrics[t].benchmark_correlation for t in tickers]
    mdd_vals = [result.asset_metrics[t].max_drawdown * 100 for t in tickers]

    with corr_col:
        c_colors = [DANGER if v > 0.8 else WARNING if v > 0.6 else SUCCESS for v in corrs]
        fig_corr = go.Figure(go.Bar(
            x=tickers, y=corrs, marker_color=c_colors,
            text=[f"{v:.2f}" if not math.isnan(v) else "—" for v in corrs],
            textposition="outside", textfont=dict(color=TEXT_PRIMARY, size=11),
        ))
        fig_corr.update_layout(
            title=dict(text=f"Correlation with {pf.benchmark}", font=dict(size=13, color=TEXT_PRIMARY)),
            yaxis=dict(range=[-1, 1.2]), bargap=0.3,
        )
        _apply_template(fig_corr, height=260)
        st.plotly_chart(fig_corr, use_container_width=True)

    with dd_col:
        dd_colors = [DANGER if v < -20 else WARNING if v < -10 else SUCCESS for v in mdd_vals]
        fig_dd = go.Figure(go.Bar(
            x=tickers, y=mdd_vals, marker_color=dd_colors,
            text=[f"{v:.1f}%" if not math.isnan(v) else "—" for v in mdd_vals],
            textposition="outside", textfont=dict(color=TEXT_PRIMARY, size=11),
        ))
        fig_dd.update_layout(
            title=dict(text="Maximum Drawdown %", font=dict(size=13, color=TEXT_PRIMARY)),
            bargap=0.3,
        )
        _apply_template(fig_dd, height=260)
        st.plotly_chart(fig_dd, use_container_width=True)

    _divider()

    # ── Section 6: Per-asset detail (expandable) ───────────────────────────────
    _h3("Individual Asset Detail")

    for t in tickers:
        m = result.asset_metrics[t]
        dy = div_yields.get(t, float("nan"))

        with st.expander(f"{t}  —  weight {_pct(m.weight)}  ·  price {_eur(m.latest_price)}"):
            d1, d2, d3, d4 = st.columns(4)

            def _card(col, label: str, value: str, color: str = TEXT_PRIMARY) -> None:
                col.markdown(
                    f"""<div style="background:{BG_SECONDARY}; border:1px solid {BORDER};
                                border-radius:7px; padding:10px 14px; margin-bottom:6px;">
                        <div style="font-size:9px; color:{TEXT_SECONDARY}; text-transform:uppercase;
                                    letter-spacing:0.06em; margin-bottom:4px;">{label}</div>
                        <div style="font-size:18px; font-weight:700; color:{color};">{value}</div>
                    </div>""",
                    unsafe_allow_html=True,
                )

            _card(d1, "CAGR",       _pct(m.cagr),
                  _color_val(m.cagr, 0.08, 0.02))
            _card(d1, "Ann. Return", _pct(m.annualized_return),
                  _color_val(m.annualized_return, 0.08, 0.02))
            _card(d1, "Div. Yield",  _pct(dy) if not math.isnan(dy) else "—")

            _card(d2, "Volatility", _pct(m.volatility),
                  SUCCESS if m.volatility < 0.15 else WARNING if m.volatility < 0.25 else DANGER)
            _card(d2, "Sharpe",     _num(m.sharpe),
                  _color_val(m.sharpe, 1.0, 0.5))
            _card(d2, "Sortino",    _num(m.sortino),
                  _color_val(m.sortino, 1.0, 0.5))

            _card(d3, "Beta",        _num(m.beta),
                  SUCCESS if 0.8 <= m.beta <= 1.2 else WARNING)
            _card(d3, "Corr. Bench", _num(m.benchmark_correlation),
                  DANGER if m.benchmark_correlation > 0.8 else WARNING if m.benchmark_correlation > 0.6 else SUCCESS)
            _card(d3, "Max Drawdown", _pct(m.max_drawdown),
                  DANGER if m.max_drawdown < -0.20 else WARNING if m.max_drawdown < -0.10 else SUCCESS)

            _card(d4, "VaR 95 %",      _pct(m.var_95))
            _card(d4, "CVaR",          _pct(m.cvar))
            _card(d4, "Risk Contrib.",  _pct(m.risk_contribution))

            # Mini price chart inside expander
            if not result.prices.empty and t in result.prices.columns:
                s = result.prices[t].dropna()
                norm = s / s.iloc[0] * 100
                fig_mini = go.Figure(go.Scatter(
                    x=norm.index, y=norm.values, name=t,
                    line=dict(color=ACCENT, width=1.8),
                    fill="tozeroy", fillcolor="rgba(194,65,12,0.08)",
                ))
                if not result.benchmark_prices.empty:
                    b = result.benchmark_prices.dropna().reindex(norm.index).ffill()
                    b_norm = b / b.iloc[0] * 100
                    fig_mini.add_trace(go.Scatter(
                        x=b_norm.index, y=b_norm.values, name=pf.benchmark,
                        line=dict(color=TEXT_SECONDARY, width=1.2, dash="dot"),
                    ))
                fig_mini.add_hline(y=100, line_dash="dot", line_color=BORDER)
                fig_mini.update_layout(
                    title=dict(text=f"{t} vs {pf.benchmark} (normalised)", font=dict(size=12, color=TEXT_PRIMARY)),
                    showlegend=True,
                )
                _apply_template(fig_mini, height=220)
                st.plotly_chart(fig_mini, use_container_width=True)
