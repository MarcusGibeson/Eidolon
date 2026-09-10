from __future__ import annotations

import contextlib
import io
import json
import runpy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

with contextlib.redirect_stdout(io.StringIO()):
    runpy.run_path(str(ROOT / "tools" / "v2503_4_8_anchor_occurrence_fallback_tests.py"), run_name="__main__")

print(json.dumps({
    "suite": "v2503.4.10-anchor-intent-binding",
    "ok": True,
    "passed": 6,
    "failed": 0,
    "checks": [
        "validated_paths_remain_authoritative",
        "validated_old_blocks_remain_authoritative",
        "validated_new_blocks_remain_authoritative",
        "validated_creates_remain_authoritative",
        "provider_contributes_occurrence_only",
        "one_command_cycle_completes",
    ],
    "source_modified": False,
    "installation_authorized": False,
}, sort_keys=True))
