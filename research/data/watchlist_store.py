"""Watchlist persistence — JSON files under .research_cache/watchlists/."""

from __future__ import annotations

import json
import logging
from datetime import date
from pathlib import Path

from research.models.fundamentals import Watchlist, WatchlistEntry

_log = logging.getLogger(__name__)
_WL_DIR = Path(".research_cache") / "watchlists"


def _ensure() -> None:
    _WL_DIR.mkdir(parents=True, exist_ok=True)


def _path(name: str) -> Path:
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in name)
    return _WL_DIR / f"{safe}.json"


def list_watchlists() -> list[str]:
    """Return names of all saved watchlists."""
    _ensure()
    return [p.stem for p in sorted(_WL_DIR.glob("*.json"))]


def load_watchlist(name: str) -> Watchlist:
    """Load a watchlist from disk. Returns empty Watchlist if not found."""
    _ensure()
    p = _path(name)
    if not p.exists():
        return Watchlist(name=name, created_at=date.today().isoformat())
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        entries = [WatchlistEntry(**e) for e in data.get("entries", [])]
        return Watchlist(
            name=data.get("name", name),
            entries=entries,
            created_at=data.get("created_at", ""),
        )
    except Exception as exc:
        _log.warning("Could not load watchlist %s: %s", name, exc)
        return Watchlist(name=name)


def save_watchlist(wl: Watchlist) -> None:
    """Persist a Watchlist to disk."""
    _ensure()
    data = {
        "name":       wl.name,
        "created_at": wl.created_at or date.today().isoformat(),
        "entries": [
            {"ticker": e.ticker, "note": e.note, "added_at": e.added_at,
             "score": e.score}
            for e in wl.entries
        ],
    }
    _path(wl.name).write_text(json.dumps(data, indent=2, ensure_ascii=False),
                               encoding="utf-8")


def delete_watchlist(name: str) -> None:
    p = _path(name)
    if p.exists():
        p.unlink()
