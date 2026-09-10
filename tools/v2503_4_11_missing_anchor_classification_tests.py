from __future__ import annotations

import json
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

import sys

sys.path[:0] = [str(ROOT), str(ROOT / "conscious_agent")]

from conscious_agent import isolated_coding_execution as execution


def require(condition: bool, label: str) -> None:
    if not condition:
        raise AssertionError(label)


checks: list[str] = []
with tempfile.TemporaryDirectory() as temporary:
    root = Path(temporary)
    source = root / "module.py"
    source.write_text("def value():\n    return 'present'\n", encoding="utf-8")
    missing_candidate = json.dumps({
        "edits": [{
            "path": "module.py",
            "replacements": [{"old": "    return 'missing'", "new": "    return 'updated'"}],
        }],
        "creates": [],
    })

    try:
        execution._validate_generation(
            missing_candidate,
            request_id="devc_test",
            execution_digest="digest",
            attempt_number=1,
            root=root,
        )
    except ValueError as exc:
        require(str(exc) == "compact_replacement_missing", "missing_anchor_has_distinct_rejection")
    else:
        raise AssertionError("missing_anchor_was_accepted")
    checks.append("missing_anchor_has_distinct_rejection")

    outcome = {
        "generation_rejection_code": "compact_replacement_missing",
        "rejected_candidate_json": missing_candidate,
    }
    prompt = execution._provider_prompt(
        request={"request_id": "devc_test"},
        plan={"context_paths": ["module.py"], "verification_plan": []},
        inspection={},
        root=root,
        execution_digest="digest",
        attempt_number=2,
        previous_outcome=outcome,
    )
    payload = json.loads(prompt)
    require(
        payload["previous_outcome"]["generation_rejection_code"] == "compact_replacement_missing",
        "missing_anchor_reaches_grounded_general_repair",
    )
    require(
        "Copy the old block exactly" in execution._generation_repair_guidance("compact_replacement_missing"),
        "missing_anchor_has_grounded_guidance",
    )
    checks.extend([
        "missing_anchor_reaches_grounded_general_repair",
        "missing_anchor_has_grounded_guidance",
    ])

    duplicate_candidate = json.dumps({
        "edits": [{
            "path": "module.py",
            "replacements": [{"old": "return", "new": "yield"}],
        }],
        "creates": [],
    })
    source.write_text("def one():\n    return 1\n\ndef two():\n    return 2\n", encoding="utf-8")
    contexts = execution._duplicate_anchor_contexts(root, duplicate_candidate)
    require(len(contexts) == 1 and contexts[0]["occurrence_count"] == 2, "duplicate_recovery_is_retained")
    checks.append("duplicate_recovery_is_retained")

print(json.dumps({
    "suite": "v2503.4.11-missing-anchor-classification",
    "ok": True,
    "passed": len(checks),
    "failed": 0,
    "checks": checks,
    "source_modified": False,
    "installation_authorized": False,
}, sort_keys=True))
