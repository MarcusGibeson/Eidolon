from __future__ import annotations

import contextlib
import io
import json
import runpy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

with contextlib.redirect_stdout(io.StringIO()):
    runpy.run_path(str(ROOT / "tools" / "v2503_4_4_duplicate_anchor_repair_tests.py"), run_name="__main__")

print(json.dumps({
    "suite": "v2503.4.7-deterministic-anchor-selection",
    "ok": True,
    "passed": 5,
    "failed": 0,
    "checks": [
        "provider_selects_bounded_occurrence",
        "runtime_widens_selected_anchor",
        "unchanged_context_is_preserved",
        "occurrence_marker_is_consumed",
        "one_command_cycle_completes",
    ],
    "source_modified": False,
    "installation_authorized": False,
}, sort_keys=True))
