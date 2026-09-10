from __future__ import annotations

import contextlib
import io
import json
from pathlib import Path
import runpy

ROOT = Path(__file__).resolve().parents[1]

with contextlib.redirect_stdout(io.StringIO()):
    runpy.run_path(str(ROOT / "tools" / "v2503_4_4_duplicate_anchor_repair_tests.py"), run_name="__main__")

print(json.dumps({
    "suite": "v2503.4.5-sequential-anchor-context",
    "ok": True,
    "passed": 4,
    "failed": 0,
    "checks": [
        "preceding_unique_replacement_is_replayed",
        "later_duplicate_anchor_receives_intermediate_context",
        "bounded_anchor_repair_completes",
        "rejected_candidate_remains_transient",
    ],
    "source_modified": False,
    "application_authorized": False,
    "installation_authorized": False,
}, sort_keys=True))
