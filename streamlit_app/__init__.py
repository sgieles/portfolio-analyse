"""Ensure the repo root is on sys.path regardless of how Streamlit invokes pages.

Streamlit Cloud runs each page file as a standalone script and only adds the
main script's directory (streamlit_app/) to sys.path.  The root-level packages
(research/, analytics/, services/, etc.) would then be unreachable.

Putting the fix here means it fires automatically whenever any
``from streamlit_app.* import …`` statement is executed — which is always
the very first import in every page file.
"""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent   # repo root
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
