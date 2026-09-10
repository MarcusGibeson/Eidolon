from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT, ROOT / "conscious_agent", ROOT / "tools"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from v1273_fixture import prepared_ownership_chain
from environment_awareness_foundations import prepare_environment_awareness


def prepared_environment_chain(base: Path, **kwargs):
    chain = prepared_ownership_chain(base, **kwargs)
    environment = prepare_environment_awareness(chain["ownership"]["ownership_id"], runtime_root=chain["runtime"], now=kwargs.get("now"))
    return {**chain, "environment": environment}


def deterministic_windows_probes():
    return {
        "platform_system": lambda: "Windows",
        "os_name": lambda: "nt",
        "machine": lambda: "AMD64",
        "python_version": lambda: "3.11.9",
        "python_implementation": lambda: "CPython",
        "python_executable": lambda: r"C:\\Python311\\python.exe",
        "python_venv": lambda: True,
        "path_exists": lambda p: True,
        "path_is_dir": lambda p: True,
        "access": lambda p, mode: True,
    }
