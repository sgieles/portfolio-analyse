"""Full-market screener runner.

Fetches every ticker in a universe, scores it, saves to daily cache.
First run for a large universe (S&P 500) may take 1–3 minutes;
subsequent runs today are instant from cache.
"""

from __future__ import annotations

import concurrent.futures
import logging
import math

_log = logging.getLogger(__name__)
_MAX_WORKERS = 20          # parallel yfinance.info threads
_PE_MAX      = 150.0       # cap P/E for heatmap normalisation (outlier filter)
_PB_MAX      = 30.0        # cap P/B for heatmap normalisation


# ── Helpers ───────────────────────────────────────────────────────────────────

def _momentum(prices, days: int) -> float:
    s = prices.dropna() if hasattr(prices, "dropna") else prices
    if len(s) < days + 1:
        return float("nan")
    end   = float(s.iloc[-1])
    start = float(s.iloc[max(-days, -len(s))])
    return (end / start) - 1.0 if start > 0 else float("nan")


def _fetch_info(ticker: str) -> tuple[str, dict]:
    try:
        import yfinance as yf
        return ticker, (yf.Ticker(ticker).info or {})
    except Exception as exc:
        _log.debug("info fetch failed %s: %s", ticker, exc)
        return ticker, {}


# ── Main entry point ──────────────────────────────────────────────────────────

def run_screener(universe: str) -> list[dict]:
    """Return scored screener rows for every ticker in *universe*.

    Loads from cache when fresh (same day + same ticker list).
    Runs a full fetch + score otherwise, then saves to cache.
    """
    from dataclasses import asdict
    import yfinance as yf

    from research.data.universe import get_universe
    from research.analytics.screener import score_from_info
    from research.cache.screener_cache import load_screener_rows, save_screener_rows

    tickers = get_universe(universe)
    if not tickers:
        return []

    # ── Cache hit ─────────────────────────────────────────────────────────────
    cached = load_screener_rows(universe, tickers)
    if cached is not None:
        return cached

    # ── Batch price download (6M history, all tickers at once) ───────────────
    _log.info("Downloading price history for %d tickers (%s)…", len(tickers), universe)
    price_map: dict[str, object] = {}
    try:
        import pandas as pd
        raw = yf.download(tickers, period="6mo", auto_adjust=True,
                          progress=False, group_by="ticker")
        if isinstance(tickers, list) and len(tickers) == 1:
            t = tickers[0]
            price_map[t] = raw["Close"] if "Close" in raw.columns else pd.Series(dtype=float)
        else:
            for t in tickers:
                try:
                    col = raw[t]["Close"]
                    price_map[t] = col
                except Exception:
                    price_map[t] = None
    except Exception as exc:
        _log.warning("Batch price download failed: %s", exc)

    # ── Parallel info fetch ───────────────────────────────────────────────────
    _log.info("Fetching yfinance info for %d tickers…", len(tickers))
    info_map: dict[str, dict] = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=_MAX_WORKERS) as ex:
        futures = {ex.submit(_fetch_info, t): t for t in tickers}
        for fut in concurrent.futures.as_completed(futures):
            tkr, info = fut.result()
            info_map[tkr] = info

    # ── Score each ticker ─────────────────────────────────────────────────────
    rows: list = []
    for ticker in tickers:
        prices = price_map.get(ticker)
        mom_1m = _momentum(prices, 21)  if prices is not None else float("nan")
        mom_3m = _momentum(prices, 63)  if prices is not None else float("nan")
        mom_6m = _momentum(prices, 126) if prices is not None else float("nan")
        info   = info_map.get(ticker, {})
        row    = score_from_info(ticker, info, mom_1m, mom_3m, mom_6m)
        rows.append(row)

    # ── Save to cache and return ──────────────────────────────────────────────
    save_screener_rows(universe, rows, tickers)
    return [asdict(r) if hasattr(r, "__dataclass_fields__") else r for r in rows]


# ── Heatmap helpers (used by research_hub.py) ─────────────────────────────────

def heatmap_bg(t: float, inverse: bool = False) -> str:
    """CSS background colour for a normalised value t ∈ [0,1].

    t=1 → green (best), t=0 → red (worst).
    inverse=True flips so that lower raw values are green (used for P/E, P/B).
    Returns empty string for NaN.
    """
    if math.isnan(t):
        return ""
    if inverse:
        t = 1.0 - t
    dev = abs(t - 0.5) * 2          # 0 = neutral, 1 = extreme
    r, g, b = (39, 174, 96) if t >= 0.5 else (192, 57, 43)
    alpha = dev * 0.35
    return f"rgba({r},{g},{b},{alpha:.2f})"


def normalize_col(
    values: list[float],
    inverse: bool = False,
    lo_cap: float | None = None,
    hi_cap: float | None = None,
    skip_zero: bool = False,
) -> list[float]:
    """Normalise a column of floats to [0,1].

    NaN → NaN.  Optional lo_cap / hi_cap clip outliers before normalisation.
    skip_zero: treat 0 as NaN (e.g. dividend yield — no dividend ≠ bad).
    Returns t values in [0,1] (not yet inverted).
    """
    valid: list[float] = []
    for v in values:
        if math.isnan(v):
            continue
        if skip_zero and v == 0.0:
            continue
        if lo_cap is not None and v < lo_cap:
            continue
        if hi_cap is not None and v > hi_cap:
            continue
        valid.append(v)

    if not valid:
        return [float("nan")] * len(values)

    vmin, vmax = min(valid), max(valid)
    out: list[float] = []
    for v in values:
        if math.isnan(v) or (skip_zero and v == 0.0):
            out.append(float("nan"))
        elif lo_cap is not None and v < lo_cap:
            out.append(0.0)
        elif hi_cap is not None and v > hi_cap:
            out.append(1.0)
        elif vmax == vmin:
            out.append(0.5)
        else:
            out.append((v - vmin) / (vmax - vmin))
    return out
