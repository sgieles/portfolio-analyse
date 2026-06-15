"""Research caching layer — JSON files on disk, 24h TTL per entry.

Layout on disk:
    .research_cache/
        cik_map.json               ticker → CIK mapping (refreshed weekly)
        companyfacts/
            <CIK>.json             raw SEC companyfacts response
        fundamentals/
            <TICKER>.json          parsed AnnualFundamentals list
        profiles/
            <TICKER>.json          CompanyProfile
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

_log = logging.getLogger(__name__)
_CACHE_ROOT = Path(".research_cache")
_CIK_MAP_PATH = _CACHE_ROOT / "cik_map.json"
_FACTS_DIR = _CACHE_ROOT / "companyfacts"
_FUND_DIR = _CACHE_ROOT / "fundamentals"
_PROF_DIR = _CACHE_ROOT / "profiles"

_TTL_FACTS = timedelta(hours=24)
_TTL_CIK   = timedelta(days=7)
_TTL_FUND  = timedelta(hours=24)
_TTL_PROF  = timedelta(hours=24)


def _ensure_dirs() -> None:
    for d in (_FACTS_DIR, _FUND_DIR, _PROF_DIR):
        d.mkdir(parents=True, exist_ok=True)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _is_fresh(path: Path, ttl: timedelta) -> bool:
    if not path.exists():
        return False
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        ts = data.get("_cached_at", "")
        if not ts:
            return False
        cached = datetime.fromisoformat(ts)
        return (datetime.now(timezone.utc) - cached) < ttl
    except Exception:
        return False


def _read_json(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data["_cached_at"] = _now_iso()
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


# ── CIK map ────────────────────────────────────────────────────────────────────

def get_cik_map() -> dict[str, str] | None:
    """Return cached {ticker: cik} map, or None if stale/missing."""
    _ensure_dirs()
    if not _is_fresh(_CIK_MAP_PATH, _TTL_CIK):
        return None
    data = _read_json(_CIK_MAP_PATH)
    return data.get("map") if data else None


def save_cik_map(mapping: dict[str, str]) -> None:
    _ensure_dirs()
    _write_json(_CIK_MAP_PATH, {"map": mapping})


# ── Company facts (raw EDGAR JSON) ─────────────────────────────────────────────

def get_company_facts(cik: str) -> dict | None:
    _ensure_dirs()
    path = _FACTS_DIR / f"{cik}.json"
    if not _is_fresh(path, _TTL_FACTS):
        return None
    return _read_json(path)


def save_company_facts(cik: str, facts: dict) -> None:
    _ensure_dirs()
    _write_json(_FACTS_DIR / f"{cik}.json", facts)


# ── Parsed fundamentals ────────────────────────────────────────────────────────

def get_fundamentals(ticker: str) -> list[dict] | None:
    _ensure_dirs()
    path = _FUND_DIR / f"{ticker}.json"
    if not _is_fresh(path, _TTL_FUND):
        return None
    data = _read_json(path)
    return data.get("rows") if data else None


def save_fundamentals(ticker: str, rows: list[dict]) -> None:
    _ensure_dirs()
    _write_json(_FUND_DIR / f"{ticker}.json", {"rows": rows})


# ── Company profile ────────────────────────────────────────────────────────────

def get_profile(ticker: str) -> dict | None:
    _ensure_dirs()
    path = _PROF_DIR / f"{ticker}.json"
    if not _is_fresh(path, _TTL_PROF):
        return None
    return _read_json(path)


def save_profile(ticker: str, profile: dict) -> None:
    _ensure_dirs()
    _write_json(_PROF_DIR / f"{ticker}.json", profile)
