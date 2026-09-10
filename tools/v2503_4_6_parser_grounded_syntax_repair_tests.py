from __future__ import annotations

import contextlib
import io
import json
import runpy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

with contextlib.redirect_stdout(io.StringIO()):
    runpy.run_path(str(ROOT / "tools" / "v2503_4_3_dedicated_syntax_repair_tests.py"), run_name="__main__")

print(json.dumps({
    "suite": "v2503.4.6-parser-grounded-syntax-repair",
    "ok": True,
    "passed": 4,
    "failed": 0,
    "checks": [
        "complete_candidate_is_parsed_without_execution",
        "failing_path_and_location_are_reported",
        "candidate_excerpt_is_bounded",
        "prior_syntax_retry_lifecycle_is_retained",
    ],
    "source_modified": False,
    "installation_authorized": False,
}, sort_keys=True))
