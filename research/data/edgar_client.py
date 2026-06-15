"""SEC EDGAR API client.

Rules enforced here:
  - User-Agent header is mandatory (SEC returns 403 without it).
  - Rate limit: max 8 requests/second (SEC allows 10; we target 8 for safety).
  - company_tickers.json: fetch once, cache 7 days.
  - companyfacts/CIK.json: cache 24h (refreshed nightly by batch job).
"""

from __future__ import annotations

import logging
import time
from typing import Any

import requests

from research.cache import research_cache as _cache

_log = logging.getLogger(__name__)

_USER_AGENT = "PortfolioAnalyser stangieles@hotmail.com"
_BASE = "https://data.sec.gov"
_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"

# Naive rate limiter: track the timestamp of the last request
_last_request_time: float = 0.0
_MIN_INTERVAL = 1.0 / 8.0  # 8 req/s


def _get(url: str) -> dict:
    """HTTP GET with User-Agent header and rate limiting. Raises on error."""
    global _last_request_time
    wait = _MIN_INTERVAL - (time.monotonic() - _last_request_time)
    if wait > 0:
        time.sleep(wait)

    resp = requests.get(url, headers={"User-Agent": _USER_AGENT}, timeout=15)
    _last_request_time = time.monotonic()
    resp.raise_for_status()
    return resp.json()


# ── Ticker → CIK mapping ───────────────────────────────────────────────────────

def get_cik_map() -> dict[str, str]:
    """Return {TICKER: zero-padded-10-digit-CIK}. Fetches from EDGAR if stale."""
    cached = _cache.get_cik_map()
    if cached:
        return cached

    _log.info("Fetching company_tickers.json from SEC EDGAR")
    raw = _get(_TICKERS_URL)
    # raw is {str(index): {"cik_str": int, "ticker": str, "title": str}}
    mapping: dict[str, str] = {}
    for entry in raw.values():
        ticker = entry.get("ticker", "").upper()
        cik = str(entry.get("cik_str", "")).zfill(10)
        if ticker:
            mapping[ticker] = cik

    _cache.save_cik_map(mapping)
    _log.info("CIK map loaded: %d tickers", len(mapping))
    return mapping


def ticker_to_cik(ticker: str) -> str | None:
    """Return zero-padded CIK for a ticker, or None if not found."""
    return get_cik_map().get(ticker.upper())


# ── Company facts ──────────────────────────────────────────────────────────────

def get_company_facts(cik: str) -> dict | None:
    """Return the full companyfacts JSON for a CIK. Uses 24h cache."""
    cached = _cache.get_company_facts(cik)
    if cached:
        return cached

    url = f"{_BASE}/api/xbrl/companyfacts/CIK{cik}.json"
    try:
        _log.info("Fetching companyfacts for CIK %s", cik)
        facts = _get(url)
        _cache.save_company_facts(cik, facts)
        return facts
    except Exception as exc:
        _log.warning("companyfacts fetch failed for CIK %s: %s", cik, exc)
        return None


def get_company_facts_by_ticker(ticker: str) -> dict | None:
    """Convenience: resolve ticker → CIK → companyfacts."""
    cik = ticker_to_cik(ticker)
    if not cik:
        _log.warning("No CIK found for ticker %s", ticker)
        return None
    return get_company_facts(cik)


# ── Filing submissions (insider activity — Phase 20) ──────────────────────────

def get_submissions(cik: str) -> dict | None:
    """Return the submissions JSON for a CIK (filing history, Forms 3/4/5)."""
    url = f"{_BASE}/submissions/CIK{cik}.json"
    try:
        return _get(url)
    except Exception as exc:
        _log.warning("submissions fetch failed for CIK %s: %s", cik, exc)
        return None
