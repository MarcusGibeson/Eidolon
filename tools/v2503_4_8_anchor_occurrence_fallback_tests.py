from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
for value in (ROOT, ROOT / "conscious_agent"):
    if str(value) not in sys.path:
        sys.path.insert(0, str(value))

from evidence_to_candidate_planner import build_evidence_to_candidate_plans
from product_plan_lifecycle import process_product_plan_control, register_product_candidate_plan


checks: list[str] = []


def require(condition: bool, label: str) -> None:
    if not condition:
        raise AssertionError(label)
    checks.append(label)


with tempfile.TemporaryDirectory(prefix="eid-v2503-4-8-anchor-fallback-") as directory:
    base = Path(directory)
    source = base / "source"
    runtime = base / "runtime"
    (source / "conscious_agent").mkdir(parents=True)
    (source / "tools").mkdir()
    target = source / "conscious_agent" / "discourse_response_planning.py"
    target.write_text(
        "def first():\n    return 'alpha'\n\ndef target():\n    return 'current'\n",
        encoding="utf-8",
    )
    (source / "conscious_agent" / "conversation_context.py").write_text(
        "def context():\n    return []\n", encoding="utf-8"
    )
    (source / "conscious_agent" / "context_assembly_architecture.py").write_text(
        "def assemble():\n    return []\n", encoding="utf-8"
    )
    (source / "tools" / "conversation_target_tests.py").write_text("print('ok')\n", encoding="utf-8")
    evidence = {
        "evidence_id": "initev_" + "a" * 24,
        "evidence_digest": "b" * 64,
        "evidence_class": "conversation_quality_finding",
        "issue_domain": "model_quality",
        "impact_score": 0.8,
        "confidence": 0.9,
        "freshness": "current",
        "structural_only": False,
    }
    plan = build_evidence_to_candidate_plans({"records": [evidence]}, source_root=source)["plans"][0]
    require(register_product_candidate_plan(plan, source_root=source, runtime_root=runtime)["ok"], "plan_registered")
    provider_calls: list[dict] = []
    sentinel = "occurrence fallback candidate sentinel"

    def provider(prompt: str) -> str:
        payload = json.loads(prompt)
        provider_calls.append(payload)
        call = len(provider_calls)
        if call == 1:
            return json.dumps({
                "edits": [{
                    "path": "conscious_agent/discourse_response_planning.py",
                    "replacements": [{"old": "return 'current'", "new": "return ("}],
                }],
                "creates": [],
            })
        if call == 2:
            require(payload.get("mode") == "syntax_repair", "syntax_repair_precedes_anchor_repair")
            return json.dumps({
                "edits": [{
                    "path": "conscious_agent/discourse_response_planning.py",
                    "replacements": [
                        {"old": "return 'alpha'", "new": "return 'current'"},
                        {"old": "return 'current'", "new": "return 'anchor repaired'"},
                    ],
                }],
                "creates": [{
                    "path": f"tools/product_repair_{plan['candidate_plan_id'].removeprefix('devplan_')}_tests.py",
                    "content": "assert True\n",
                }],
            })
        if call == 3:
            require(payload.get("mode") == "replacement_anchor_repair", "duplicate_anchor_repair_requested")
            return json.dumps({
                "edits": [{
                    "path": "conscious_agent/discourse_response_planning.py",
                    "replacements": [
                        {"old": "return 'alpha'", "new": "return 'provider drift'"},
                        {"old": "return 'current'  # provider-copied context", "new": f"return '{sentinel}'"},
                    ],
                }],
                "creates": [],
            })
        require(payload.get("mode") == "replacement_anchor_occurrence_selection", "selection_only_fallback_requested")
        require("rejected_candidate_json" not in payload, "candidate_content_not_reexposed_in_selection_prompt")
        return json.dumps({
            "selections": [{
                "path": "conscious_agent/discourse_response_planning.py",
                "replacement_index": 1,
                "occurrence": 2,
            }],
        })

    phrase = f"Run one supervised product repair cycle for {plan['candidate_plan_id']} digest {plan['candidate_plan_digest'][:16]}."
    result = process_product_plan_control(
        phrase,
        source_root=source,
        runtime_root=runtime,
        provider_generate=provider,
        python_executable=sys.executable,
    )
    require(result.get("ok") is True and result.get("status") == "product_repair_candidate_ready", "fallback_cycle_completes")
    require(len(provider_calls) == 4, "one_implementation_and_three_bounded_repairs")
    require(result.get("source_modified") is False, "active_source_remains_unchanged")
    persisted = "\n".join(path.read_text(encoding="utf-8", errors="ignore") for path in runtime.rglob("*.json"))
    require(sentinel not in persisted, "transient_candidates_are_not_persisted")

print(json.dumps({
    "suite": "v2503.4.8-anchor-occurrence-fallback",
    "ok": True,
    "passed": len(checks),
    "failed": 0,
    "checks": checks,
    "source_modified": False,
    "application_authorized": False,
    "installation_authorized": False,
}, sort_keys=True))
