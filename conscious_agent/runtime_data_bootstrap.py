from __future__ import annotations

"""Minimal runtime-data bootstrap with no source-tree side effects.

Normal Eidolon execution must never default mutable runtime state into the
source checkout.  This helper is safe to import before the rest of the runtime
and establishes one external data root when the operator has not supplied
``EIDOLON_DATA_DIR`` explicitly.
"""

import os
from pathlib import Path

ENV_NAME = "EIDOLON_DATA_DIR"


def default_runtime_data_dir() -> Path:
    override = os.environ.get(ENV_NAME)
    if override:
        return Path(override).expanduser().resolve()
    home = Path.home()
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
        root = Path(base).expanduser() if base else home / "AppData" / "Local"
        return (root / "Eidolon" / "data").resolve()
    xdg = os.environ.get("XDG_DATA_HOME")
    root = Path(xdg).expanduser() if xdg else home / ".local" / "share"
    return (root / "eidolon").resolve()


def ensure_runtime_data_env() -> Path:
    path = default_runtime_data_dir()
    os.environ.setdefault(ENV_NAME, str(path))
    return path


__all__ = ["ENV_NAME", "default_runtime_data_dir", "ensure_runtime_data_env"]
