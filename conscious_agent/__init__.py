from __future__ import annotations

"""Eidolon package compatibility bootstrap.

Most of Eidolon's historical modules use sibling absolute imports because they
were originally invoked as scripts.  Standard package execution imports this
module first, so adding the package directory to ``sys.path`` lets those modules
resolve the same siblings without duplicating release metadata or rewriting
hundreds of historical imports in one risky patch.
"""

import sys
from pathlib import Path

_PACKAGE_DIR = Path(__file__).resolve().parent
if str(_PACKAGE_DIR) not in sys.path:
    sys.path.insert(0, str(_PACKAGE_DIR))

from runtime_data_bootstrap import ensure_runtime_data_env as _ensure_runtime_data_env

_ensure_runtime_data_env()
