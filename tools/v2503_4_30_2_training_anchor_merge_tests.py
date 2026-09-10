from __future__ import annotations

import contextlib
import io
import json
import runpy
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "conscious_agent")]

from conscious_agent import isolated_coding_execution as execution


def require(condition: bool, label: str) -> None:
    if not condition:
        raise AssertionError(label)


checks: list[str] = []
with contextlib.redirect_stdout(io.StringIO()):
    runpy.run_path(str(ROOT / "tools" / "v2503_4_30_1_training_provenance_benchmark_audit_tests.py"), run_name="__main__")
checks.append("training_provenance_benchmark_audit_retained")

with tempfile.TemporaryDirectory() as temporary:
    root = Path(temporary)
    source = root / "reasoning.py"
    valid_old = "def heading():\n    return 'Research'\n"
    exact_missing = "def summarize(report):\n    return report['evidence']\n"
    intended_new = "def summarize(report):\n    return report['evidence'].strip()\n"
    source.write_text(valid_old + "\n" + exact_missing, encoding="utf-8")
    rejected = json.dumps({
        "edits": [{
            "path": "reasoning.py",
            "replacements": [
                {"old": valid_old, "new": "def heading():\n    return 'Research report'\n"},
                {"old": "def summarize(report):\n    return report.get('evidence')\n", "new": intended_new},
            ],
        }],
        "creates": [],
    })
    repaired = json.dumps({
        "edits": [{
            "path": "reasoning.py",
            "replacements": [
                {"old": "def heading():\n    return 'provider drift'\n", "new": "def heading():\n    return 'Research report'\n"},
                {"old": exact_missing, "new": intended_new},
            ],
        }],
        "creates": [],
    })
    bound = json.loads(execution._restore_missing_anchor_repair_intent(rejected, repaired, root=root))
    require(bound["edits"][0]["replacements"][0]["old"] == valid_old, "valid_anchor_remains_authoritative")
    require(bound["edits"][0]["replacements"][1]["old"] == exact_missing, "missing_anchor_accepts_grounded_correction")
    checks.extend(["valid_anchor_remains_authoritative", "missing_anchor_accepts_grounded_correction"])
    validated = execution._validate_generation(
        json.dumps(bound),
        request_id="devc_merge_test",
        execution_digest="digest",
        attempt_number=2,
        root=root,
    )
    require(len(validated) == 1, "multi_replacement_candidate_validates")
    require("Research report" in validated[0]["content"] and ".strip()" in validated[0]["content"], "both_intended_changes_are_retained")
    checks.extend(["multi_replacement_candidate_validates", "both_intended_changes_are_retained"])

print(json.dumps({
    "suite": "v2503.4.30.2-training-anchor-merge",
    "ok": True,
    "passed": len(checks),
    "failed": 0,
    "checks": checks,
    "source_modified": False,
    "training_authorized": False,
    "installation_authorized": False,
}, sort_keys=True))
