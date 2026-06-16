"""Run a full portfolio analysis and store the result in session state."""

from __future__ import annotations

import streamlit as st

from analytics.diversification import (
    average_correlation, diversification_score,
    return_contributions, risk_contributions,
)
from analytics.returns import (
    annualized_return, benchmark_value_series, capm_expected_return,
    cagr, portfolio_daily_returns, portfolio_value_series,
)
from analytics.risk import (
    annualized_volatility, beta as compute_beta,
    drawdown_series, historical_cvar, historical_var,
    max_drawdown, portfolio_beta, portfolio_volatility,
    rolling_volatility, sharpe_ratio, sortino_ratio,
)
from models.portfolio import Portfolio
from models.results import AnalysisResult, AssetMetrics, OptimizationResult
from models.settings import AnalysisSettings
from optimization.efficient_frontier import build_frontier_data
from optimization.optimizers import black_litterman, max_sharpe, min_variance
from services.data_service import DataService
from streamlit_app.state import session


@st.cache_data(show_spinner=False, ttl=300)
def _fetch(tickers: tuple[str, ...], benchmark: str, period: str):
    """Cached price fetch — re-runs only when inputs change."""
    svc = DataService()
    fetch = svc.fetch_prices(list(tickers), period)
    bench = svc.fetch_single(benchmark, period)
    return fetch, bench


def run_analysis() -> AnalysisResult | None:
    """Fetch prices and compute all analytics. Returns None on error."""
    pf: Portfolio = session.get_portfolio()
    settings: AnalysisSettings = session.get_settings()

    if not pf.assets:
        st.warning("Add at least one ticker to analyse.")
        return None

    with st.spinner("Fetching price data and computing analytics…"):
        try:
            fetch, bench_prices = _fetch(
                tuple(pf.tickers), pf.benchmark, pf.period
            )
        except Exception as exc:
            st.error(f"Data fetch failed: {exc}")
            return None

        prices = fetch.prices.copy()
        # Strip timezone info from both indices so reindex never raises
        # ValueError("Cannot join DatetimeIndex with mixed timezones").
        if hasattr(prices.index, "tz") and prices.index.tz is not None:
            prices.index = prices.index.tz_localize(None)
        if hasattr(bench_prices.index, "tz") and bench_prices.index.tz is not None:
            bench_prices.index = bench_prices.index.tz_localize(None)
        bench_prices = bench_prices.reindex(prices.index).ffill().dropna()

        available = set(prices.columns)
        weights = {t: pf.weight_of(t) for t in pf.tickers if t in available}
        w_total = sum(weights.values())
        if w_total == 0:
            st.error("All tickers failed — no data returned.")
            return None
        if abs(w_total - 1.0) > 1e-4:
            weights = {t: w / w_total for t, w in weights.items()}

        tickers_ok = list(weights.keys())
        prices = prices[tickers_ok]

        rets = prices.pct_change().dropna()
        bench_rets_raw = bench_prices.pct_change().dropna()
        common = rets.index.intersection(bench_rets_raw.index)
        rets_a      = rets.loc[common]
        bench_rets_a = bench_rets_raw.loc[common]
        port_rets = portfolio_daily_returns(prices, weights).loc[common]

        ann_ret   = annualized_return(port_rets)
        port_val  = portfolio_value_series(prices, weights)
        port_cagr = cagr(port_val)
        port_vol  = portfolio_volatility(rets_a, weights)
        p_sharpe  = sharpe_ratio(ann_ret, port_vol, settings.risk_free_rate)
        p_sortino = sortino_ratio(port_rets, ann_ret, settings.risk_free_rate)
        p_beta    = portfolio_beta(port_rets, bench_rets_a)
        capm_ret  = capm_expected_return(p_beta, settings.risk_free_rate, settings.market_expected_return)
        mdd       = max_drawdown(port_val)
        var95     = historical_var(port_rets, 0.95)
        var99     = historical_var(port_rets, 0.99)
        p_cvar    = historical_cvar(port_rets, 0.95)
        avg_c     = average_correlation(rets_a)
        div_sc    = diversification_score(rets_a, weights)

        current_opt = OptimizationResult(
            method="current", weights=weights,
            expected_return=ann_ret, volatility=port_vol,
            sharpe=p_sharpe, beta=p_beta, var_95=var95, max_drawdown=mdd,
        )

        risk_c = risk_contributions(rets_a, weights)
        ann_rets_per_ticker = {t: annualized_return(rets_a[t]) for t in tickers_ok}
        ret_c  = return_contributions(ann_rets_per_ticker, weights)

        asset_metrics: dict[str, AssetMetrics] = {}
        for ticker in tickers_ok:
            a_rets = rets_a[ticker]
            a_ann  = ann_rets_per_ticker[ticker]
            a_vol  = annualized_volatility(a_rets)
            asset_metrics[ticker] = AssetMetrics(
                ticker=ticker, weight=weights[ticker],
                cagr=cagr(prices[ticker]), annualized_return=a_ann,
                volatility=a_vol,
                sharpe=sharpe_ratio(a_ann, a_vol, settings.risk_free_rate),
                sortino=sortino_ratio(a_rets, a_ann, settings.risk_free_rate),
                beta=compute_beta(a_rets, bench_rets_a),
                max_drawdown=max_drawdown(prices[ticker]),
                var_95=historical_var(a_rets, 0.95),
                var_99=historical_var(a_rets, 0.99),
                cvar=historical_cvar(a_rets, 0.95),
                latest_price=float(prices[ticker].iloc[-1]),
                benchmark_correlation=float(a_rets.corr(bench_rets_a)),
                risk_contribution=risk_c.get(ticker, float("nan")),
                return_contribution=ret_c.get(ticker, float("nan")),
            )

        opt_results: dict[str, OptimizationResult] = {"current": current_opt}
        for key, fn in [("max_sharpe", max_sharpe), ("min_variance", min_variance), ("black_litterman", black_litterman)]:
            try:
                opt_results[key] = fn(prices, settings, bench_prices)
            except Exception:
                opt_results[key] = OptimizationResult(method=key)

        frontier_risks, frontier_returns = [], []
        try:
            fd = build_frontier_data(prices, weights, settings, bench_prices, n_points=50)
            frontier_risks, frontier_returns = fd.frontier_risks, fd.frontier_returns
        except Exception:
            pass

        bench_vals = benchmark_value_series(bench_prices)
        dd_series  = drawdown_series(port_val)
        roll_vol   = rolling_volatility(port_rets, window=252)

        result = AnalysisResult(
            portfolio=pf, settings=settings,
            prices=prices, returns=rets_a,
            benchmark_prices=bench_prices, benchmark_returns=bench_rets_a,
            portfolio_return=ann_ret, portfolio_cagr=port_cagr,
            portfolio_expected_return_capm=capm_ret,
            portfolio_volatility=port_vol, sharpe_ratio=p_sharpe,
            sortino_ratio=p_sortino, beta=p_beta,
            max_drawdown=mdd, var_95=var95, var_99=var99, cvar=p_cvar,
            avg_correlation=avg_c, diversification_score=div_sc,
            asset_metrics=asset_metrics, optimization=opt_results,
            portfolio_value_series=port_val, benchmark_value_series=bench_vals,
            drawdown_series=dd_series, rolling_volatility_series=roll_vol,
            frontier_risk=frontier_risks, frontier_return=frontier_returns,
            failed_tickers=fetch.failed_tickers, warnings=fetch.warnings,
        )

        session.set_result(result)
        return result
