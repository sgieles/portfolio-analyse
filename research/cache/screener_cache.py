"""Screener result cache — per-universe JSON, refreshed daily.

The cache is invalidated when either the date changes OR the set of
tickers in the universe changes (e.g. after a ticker correction).
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import asdict
from datetime import date
from pathlib import Path

_log = logging.getLogger(__name__)
_DIR = Path(".research_cache") / "screener"


def _ensure() -> None:
    _DIR.mkdir(parents=True, exist_ok=True)


def _path(universe: str) -> Path:
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in universe)
    return _DIR / f"{safe}.json"


def _ticker_hash(tickers: list[str]) -> str:
    """Short hash of the sorted ticker list — used to detect universe changes."""
    blob = ",".join(sorted(tickers)).encode()
    return hashlib.md5(blob).hexdigest()[:8]


def _fresh(data: dict, tickers: list[str]) -> bool:
    """Cache is fresh only if the date AND the ticker list both match."""
    return (
        data.get("_date") == date.today().isoformat()
        and data.get("_ticker_hash") == _ticker_hash(tickers)
    )


def load_screener_rows(universe: str, tickers: list[str] | None = None) -> list[dict] | None:
    """Return cached screener rows for *universe* if fresh (today and same tickers).

    Pass *tickers* (the current universe list) to enable ticker-change detection.
    If omitted, only the date is checked (backward-compatible).
    """
    _ensure()
    p = _path(universe)
    if not p.exists():
        return None
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        if tickers is not None:
            return data.get("rows") if _fresh(data, tickers) else None
        # Legacy: date-only check
        return data.get("rows") if data.get("_date") == date.today().isoformat() else None
    except Exception as exc:
        _log.warning("Screener cache read error for %s: %s", universe, exc)
        return None


def save_screener_rows(universe: str, rows: list, tickers: list[str] | None = None) -> None:
    """Persist screener rows (ScreenerRow dataclasses or dicts) for *universe*."""
    _ensure()
    serializable = [asdict(r) if hasattr(r, "__dataclass_fields__") else r for r in rows]
    payload: dict = {"_date": date.today().isoformat(), "rows": serializable}
    if tickers is not None:
        payload["_ticker_hash"] = _ticker_hash(tickers)
    _path(universe).write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
