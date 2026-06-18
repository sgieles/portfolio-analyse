"""Pure analysis runner — no Streamlit, no session state.

Takes portfolio config as a plain dict, returns a JSON-serializable dict
or raises on error.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd

from analytics.diversification import (
    average_correlation, diversification_score,
    return_contributions, risk_contributions,
)
from analytics.health_score import portfolio_health_score
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
from models.asset import Asset
from models.portfolio import Portfolio
from models.results import AnalysisResult, AssetMetrics, OptimizationResult
from models.settings import AnalysisSettings
from analytics.scenario import run_scenario_analysis
from optimization.efficient_frontier import build_frontier_data
from optimization.optimizers import black_litterman, max_sharpe, min_variance
from services.data_service import DataService

# Module-level price cache keyed by (tickers_tuple, benchmark, period)
_CACHE: dict[tuple, tuple] = {}


def _fetch_prices(tickers: tuple[str, ...], benchmark: str, period: str):
    key = (tickers, benchmark, period)
    if key in _CACHE:
        return _CACHE[key]
    svc = DataService()
    result = svc.fetch_prices(list(tickers), period)
    bench  = svc.fetch_single(benchmark, period)
    _CACHE[key] = (result, bench)
    return result, bench


def _safe(v: float) -> float | None:
    return None if (math.isnan(v) or math.isinf(v)) else round(v, 8)


def _series_dict(s: pd.Series) -> dict:
    if s is None or s.empty:
        return {"dates": [], "values": []}
    idx = s.index
    dates = idx.strftime("%Y-%m-%d").tolist() if hasattr(idx, "strftime") else [str(i) for i in idx]
    vals  = [_safe(float(v)) for v in s.values]
    return {"dates": dates, "values": vals}


def run_analysis(pf_data: dict) -> tuple[dict | None, str | None]:
    """Run full portfolio analysis.

    Returns (result_dict, None) on success, (None, error_message) on failure.
    """
    tickers = pf_data.get("tickers", [])
    weights_raw: dict[str, float] = pf_data.get("weights", {})
    benchmark = pf_data.get("benchmark", "SPY")
    period    = pf_data.get("period", "5y")
    rf_rate   = float(pf_data.get("rf_rate", 0.025))

    if not tickers:
        return None, "Add at least one ticker to analyse."

    settings = AnalysisSettings(
        risk_free_rate=rf_rate,
        market_expected_return=0.10,
    )
    pf = Portfolio(
        assets=[Asset(ticker=t, weight=weights_raw.get(t, 1.0 / len(tickers))) for t in tickers],
        benchmark=benchmark,
        period=period,
        name=pf_data.get("name", "My Portfolio"),
    )

    try:
        fetch, bench_prices = _fetch_prices(tuple(tickers), benchmark, period)
    except Exception as exc:
        return None, f"Data fetch failed: {exc}"

    prices = fetch.prices.copy()
    if hasattr(prices.index, "tz") and prices.index.tz is not None:
        prices.index = prices.index.tz_localize(None)
    if hasattr(bench_prices.index, "tz") and bench_prices.index.tz is not None:
        bench_prices.index = bench_prices.index.tz_localize(None)
    bench_prices = bench_prices.reindex(prices.index).ffill().dropna()

    available = set(prices.columns)
    weights   = {t: pf.weight_of(t) for t in pf.tickers if t in available}
    w_total   = sum(weights.values())
    if w_total == 0:
        return None, "All tickers failed — no data returned."
    if abs(w_total - 1.0) > 1e-4:
        weights = {t: w / w_total for t, w in weights.items()}

    tickers_ok = list(weights.keys())
    prices = prices[tickers_ok]

    rets          = prices.pct_change().dropna()
    bench_rets_raw = bench_prices.pct_change().dropna()
    common        = rets.index.intersection(bench_rets_raw.index)
    rets_a        = rets.loc[common]
    bench_rets_a  = bench_rets_raw.loc[common]
    port_rets     = portfolio_daily_returns(prices, weights).loc[common]

    ann_ret  = annualized_return(port_rets)
    port_val = portfolio_value_series(prices, weights)
    p_cagr   = cagr(port_val)
    p_vol    = portfolio_volatility(rets_a, weights)
    p_sharpe = sharpe_ratio(ann_ret, p_vol, rf_rate)
    p_sortino= sortino_ratio(port_rets, ann_ret, rf_rate)
    p_beta   = portfolio_beta(port_rets, bench_rets_a)
    capm_ret = capm_expected_return(p_beta, rf_rate, settings.market_expected_return)
    mdd      = max_drawdown(port_val)
    var95    = historical_var(port_rets, 0.95)
    var99    = historical_var(port_rets, 0.99)
    p_cvar   = historical_cvar(port_rets, 0.95)
    avg_c    = average_correlation(rets_a)
    div_sc   = diversification_score(rets_a, weights)

    risk_c          = risk_contributions(rets_a, weights)
    ann_per_ticker  = {t: annualized_return(rets_a[t]) for t in tickers_ok}
    ret_c           = return_contributions(ann_per_ticker, weights)

    asset_metrics: dict[str, dict] = {}
    for ticker in tickers_ok:
        a_rets = rets_a[ticker]
        a_ann  = ann_per_ticker[ticker]
        a_vol  = annualized_volatility(a_rets)
        asset_metrics[ticker] = {
            "weight":               _safe(weights[ticker]),
            "cagr":                 _safe(cagr(prices[ticker])),
            "annualized_return":    _safe(a_ann),
            "volatility":           _safe(a_vol),
            "sharpe":               _safe(sharpe_ratio(a_ann, a_vol, rf_rate)),
            "sortino":              _safe(sortino_ratio(a_rets, a_ann, rf_rate)),
            "beta":                 _safe(compute_beta(a_rets, bench_rets_a)),
            "max_drawdown":         _safe(max_drawdown(prices[ticker])),
            "var_95":               _safe(historical_var(a_rets, 0.95)),
            "var_99":               _safe(historical_var(a_rets, 0.99)),
            "cvar":                 _safe(historical_cvar(a_rets, 0.95)),
            "latest_price":         _safe(float(prices[ticker].iloc[-1])),
            "benchmark_correlation":_safe(float(a_rets.corr(bench_rets_a))),
            "risk_contribution":    _safe(risk_c.get(ticker, float("nan"))),
            "return_contribution":  _safe(ret_c.get(ticker, float("nan"))),
        }

    optimization: dict[str, dict] = {
        "current": {
            "weights": weights,
            "expected_return": _safe(ann_ret),
            "volatility": _safe(p_vol),
            "sharpe": _safe(p_sharpe),
        }
    }
    for key, fn in [("max_sharpe", max_sharpe), ("min_variance", min_variance), ("black_litterman", black_litterman)]:
        try:
            opt = fn(prices, settings, bench_prices)
            optimization[key] = {
                "weights": opt.weights,
                "expected_return": _safe(opt.expected_return),
                "volatility": _safe(opt.volatility),
                "sharpe": _safe(opt.sharpe),
            }
        except Exception:
            optimization[key] = {"weights": {}, "expected_return": None, "volatility": None, "sharpe": None}

    frontier_risks, frontier_returns = [], []
    try:
        fd = build_frontier_data(prices, weights, settings, bench_prices, n_points=50)
        frontier_risks, frontier_returns = fd.frontier_risks, fd.frontier_returns
    except Exception:
        pass

    bench_vals = benchmark_value_series(bench_prices)
    dd_series  = drawdown_series(port_val)
    roll_vol   = rolling_volatility(port_rets, window=252)

    hs, _ = portfolio_health_score(p_sharpe, mdd, p_vol, div_sc, weights)

    # Scenario / stress-test analysis
    scenarios_out: list[dict] = []
    try:
        scenario_results = run_scenario_analysis(
            daily_returns=rets_a,
            weights=weights,
            benchmark_returns=bench_rets_a,
        )
        for sr in scenario_results:
            scenarios_out.append({
                "name":              sr.name,
                "market_return":     _safe(sr.market_return),
                "portfolio_return":  _safe(sr.portfolio_return),
                "new_value":         _safe(sr.new_value),
                "stressed_vol":      _safe(sr.stressed_vol),
                "asset_impacts":     {t: _safe(v) for t, v in sr.asset_impacts.items()},
            })
    except Exception:
        pass

    # Serialize returns matrix (needed for correlation chart)
    returns_dict: dict[str, list] = {}
    for col in rets_a.columns:
        returns_dict[col] = [_safe(float(v)) for v in rets_a[col].values]

    return {
        "scalars": {
            "portfolio_return":               _safe(ann_ret),
            "portfolio_cagr":                 _safe(p_cagr),
            "portfolio_expected_return_capm": _safe(capm_ret),
            "portfolio_volatility":           _safe(p_vol),
            "sharpe_ratio":                   _safe(p_sharpe),
            "sortino_ratio":                  _safe(p_sortino),
            "beta":                           _safe(p_beta),
            "max_drawdown":                   _safe(mdd),
            "var_95":                         _safe(var95),
            "var_99":                         _safe(var99),
            "cvar":                           _safe(p_cvar),
            "avg_correlation":                _safe(avg_c),
            "diversification_score":          _safe(div_sc),
            "health_score":                   int(hs),
        },
        "series": {
            "port_val":  _series_dict(port_val),
            "bench_val": _series_dict(bench_vals),
            "drawdown":  _series_dict(dd_series),
            "roll_vol":  _series_dict(roll_vol),
        },
        "returns": returns_dict,
        "asset_metrics": asset_metrics,
        "optimization": optimization,
        "frontier": {
            "risk":   [_safe(v) for v in frontier_risks],
            "return": [_safe(v) for v in frontier_returns],
        },
        "scenarios": scenarios_out,
        "tickers": tickers_ok,
        "meta": {
            "period":         period,
            "benchmark":      benchmark,
            "rf_rate":        rf_rate,
            "n_assets":       len(tickers_ok),
            "failed_tickers": fetch.failed_tickers,
            "pf_name":        pf_data.get("name", "My Portfolio"),
        },
    }, None
