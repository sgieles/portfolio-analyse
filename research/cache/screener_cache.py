"""Screener result cache — per-universe JSON, refreshed daily."""

from __future__ import annotations

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


def _fresh(data: dict) -> bool:
    return data.get("_date") == date.today().isoformat()


def load_screener_rows(universe: str) -> list[dict] | None:
    """Return cached screener rows for *universe* if fresh (today), else None."""
    _ensure()
    p = _path(universe)
    if not p.exists():
        return None
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return data.get("rows") if _fresh(data) else None
    except Exception as exc:
        _log.warning("Screener cache read error for %s: %s", universe, exc)
        return None


def save_screener_rows(universe: str, rows: list) -> None:
    """Persist screener rows (ScreenerRow dataclasses or dicts) for *universe*."""
    _ensure()
    serializable = [asdict(r) if hasattr(r, "__dataclass_fields__") else r for r in rows]
    _path(universe).write_text(
        json.dumps(
            {"_date": date.today().isoformat(), "rows": serializable},
            indent=2, ensure_ascii=False,
        ),
        encoding="utf-8",
    )
