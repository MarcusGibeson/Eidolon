from __future__ import annotations

import json
import tempfile
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "conscious_agent")]

from conscious_agent import isolated_coding_execution as execution


def require(condition: bool, label: str) -> None:
    if not condition:
        raise AssertionError(label)


checks: list[str] = []
with tempfile.TemporaryDirectory() as temporary:
    root = Path(temporary)
    source = root / "reasoning.py"
    exact_old = "def summarize(report):\n    return report['evidence']\n"
    intended_new = "def summarize(report):\n    return report['evidence'].strip()\n"
    source.write_text(
        "def heading():\n    return 'Research'\n\n" + exact_old + "\ndef footer():\n    return 'Done'\n",
        encoding="utf-8",
    )
    rejected = json.dumps({
        "edits": [{
            "path": "reasoning.py",
            "replacements": [{
                "old": "def summarize(report):\n    return report.get('evidence')\n",
                "new": intended_new,
            }],
        }],
        "creates": [],
    })

    contexts = execution._missing_anchor_contexts(root, rejected)
    require(len(contexts) == 1, "missing_anchor_context_is_found")
    require(exact_old in contexts[0]["nearby_source"][0]["content"], "nearby_context_contains_exact_source")
    checks.extend(["missing_anchor_context_is_found", "nearby_context_contains_exact_source"])

    prompt = json.loads(execution._missing_anchor_repair_prompt(
        root=root,
        request_id="devc_test",
        execution_digest="digest",
        attempt_number=2,
        rejected_candidate_json=rejected,
    ))
    require(prompt["limits"]["old_anchors_only"] is True, "repair_is_old_anchor_only")
    checks.append("repair_is_old_anchor_only")

    repaired = json.dumps({
        "edits": [{
            "path": "reasoning.py",
            "replacements": [{"old": exact_old, "new": intended_new}],
        }],
        "creates": [],
    })
    bound = execution._restore_missing_anchor_repair_intent(rejected, repaired)
    validated = execution._validate_generation(
        bound,
        request_id="devc_test",
        execution_digest="digest",
        attempt_number=2,
        root=root,
    )
    require(len(validated) == 1 and validated[0]["content"].count(".strip()") == 1, "grounded_repair_validates")
    checks.append("grounded_repair_validates")

    changed_intent = json.loads(repaired)
    changed_intent["edits"][0]["replacements"][0]["new"] = "def summarize(report):\n    return 'unrelated'\n"
    try:
        execution._restore_missing_anchor_repair_intent(rejected, json.dumps(changed_intent))
    except ValueError as exc:
        require(str(exc) == "missing_anchor_intent_changed", "provider_cannot_change_new_intent")
    else:
        raise AssertionError("changed_new_intent_was_accepted")
    checks.append("provider_cannot_change_new_intent")

print(json.dumps({
    "suite": "v2503.4.12-grounded-missing-anchor-repair",
    "ok": True,
    "passed": len(checks),
    "failed": 0,
    "checks": checks,
    "source_modified": False,
    "installation_authorized": False,
}, sort_keys=True))
