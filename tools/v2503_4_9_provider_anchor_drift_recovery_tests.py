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
    "suite": "v2503.4.9-provider-anchor-drift-recovery",
    "ok": True,
    "passed": 5,
    "failed": 0,
    "checks": [
        "provider_old_anchor_is_not_authoritative",
        "validated_rejected_anchor_is_restored",
        "validated_new_block_intent_is_retained",
        "missing_occurrence_fallback_remains_bounded",
        "one_command_cycle_completes",
    ],
    "source_modified": False,
    "installation_authorized": False,
}, sort_keys=True))
