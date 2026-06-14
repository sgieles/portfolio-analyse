"""On-disk price-history cache keyed by (ticker, period).

Stores each series as a pickle file. Entries expire after CACHE_EXPIRY_HOURS.
"""

import pickle
import time
from pathlib import Path

import pandas as pd

from utils.constants import CACHE_DIR, CACHE_EXPIRY_HOURS
from utils.logging import get_logger
from services.exceptions import CacheError

log = get_logger(__name__)

_SUFFIX = ".pkl"


class PriceCache:
    """Simple file-based cache for adjusted-close price series."""

    def __init__(self, cache_dir: Path | str = CACHE_DIR) -> None:
        self._dir = Path(cache_dir)
        try:
            self._dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            log.warning("Cannot create cache directory '%s': %s", self._dir, exc)

    # ── Public API ───────────────────────────────────────────────────────────

    def get(self, ticker: str, period: str) -> pd.Series | None:
        """Return cached series or None if missing / expired."""
        path = self._path(ticker, period)
        if not path.exists():
            return None
        if self._is_expired(path):
            log.debug("Cache expired: %s", path.name)
            path.unlink(missing_ok=True)
            return None
        try:
            with path.open("rb") as fh:
                series: pd.Series = pickle.load(fh)
            log.debug("Cache hit: %s", path.name)
            return series
        except Exception as exc:  # noqa: BLE001
            log.warning("Cache read error for '%s/%s': %s", ticker, period, exc)
            return None

    def put(self, ticker: str, period: str, series: pd.Series) -> None:
        """Persist *series* to disk. Silently ignores write errors."""
        path = self._path(ticker, period)
        try:
            with path.open("wb") as fh:
                pickle.dump(series, fh, protocol=pickle.HIGHEST_PROTOCOL)
            log.debug("Cache write: %s", path.name)
        except Exception as exc:  # noqa: BLE001
            log.warning("Cache write error for '%s/%s': %s", ticker, period, exc)

    def invalidate(self, ticker: str, period: str) -> None:
        """Remove a single cache entry."""
        self._path(ticker, period).unlink(missing_ok=True)

    def clear(self) -> None:
        """Delete all cache files."""
        for f in self._dir.glob(f"*{_SUFFIX}"):
            f.unlink(missing_ok=True)
        log.info("Price cache cleared.")

    # ── Internals ────────────────────────────────────────────────────────────

    def _path(self, ticker: str, period: str) -> Path:
        safe_ticker = ticker.replace("/", "_").replace("\\", "_")
        return self._dir / f"{safe_ticker}__{period}{_SUFFIX}"

    @staticmethod
    def _is_expired(path: Path) -> bool:
        age_seconds = time.time() - path.stat().st_mtime
        return age_seconds > CACHE_EXPIRY_HOURS * 3600
