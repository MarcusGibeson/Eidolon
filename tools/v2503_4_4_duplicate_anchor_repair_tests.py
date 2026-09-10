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


with tempfile.TemporaryDirectory(prefix="eid-v2503-4-4-anchor-") as directory:
    base = Path(directory)
    source = base / "source"
    runtime = base / "runtime"
    (source / "conscious_agent").mkdir(parents=True)
    (source / "tools").mkdir()
    (source / "conscious_agent" / "discourse_response_planning.py").write_text(
        "def first():\n    return 'alpha'\n\ndef target():\n    return 'current'\n", encoding="utf-8"
    )
    (source / "conscious_agent" / "conversation_context.py").write_text("def context():\n    return []\n", encoding="utf-8")
    (source / "conscious_agent" / "context_assembly_architecture.py").write_text("def assemble():\n    return []\n", encoding="utf-8")
    (source / "tools" / "conversation_target_tests.py").write_text("print('ok')\n", encoding="utf-8")
    evidence = {
        "evidence_id": "initev_" + "e" * 24,
        "evidence_digest": "f" * 64,
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
    sentinel = "ambiguous repair candidate sentinel"

    def provider(prompt: str) -> str:
        payload = json.loads(prompt)
        provider_calls.append(payload)
        if len(provider_calls) == 1:
            return json.dumps({
                "edits": [{
                    "path": "conscious_agent/discourse_response_planning.py",
                    "replacements": [
                        {"old": "return 'alpha'", "new": "return 'current'"},
                        {"old": "return 'current'", "new": f"return '{sentinel}'"},
                    ],
                }],
                "creates": [],
            })
        require(payload.get("mode") == "replacement_anchor_repair", "duplicate_rejection_uses_anchor_repair_prompt")
        contexts = payload.get("duplicate_anchor_contexts") or []
        require(len(contexts) == 1 and contexts[0].get("occurrence_count") == 2, "both_duplicate_occurrences_are_exposed")
        require(len(contexts[0].get("occurrences") or []) == 2, "duplicate_context_excerpts_are_bounded_and_complete")
        require(payload.get("rejected_candidate_json") and sentinel in payload["rejected_candidate_json"], "rejected_candidate_is_carried_transiently")
        schema_replacement = payload.get("response_schema", {}).get("edits", [{}])[0].get("replacements", [{}])[0]
        require(schema_replacement.get("occurrence") == 1, "repair_schema_requests_occurrence_selection")
        return json.dumps({
            "edits": [{
                "path": "conscious_agent/discourse_response_planning.py",
                "replacements": [
                    {"old": "return 'alpha'", "new": "return 'current'"},
                    {
                        "old": "return 'current'",
                        "new": "return 'anchor repaired'",
                        "occurrence": 2,
                    },
                ],
            }],
            "creates": [{
                "path": f"tools/product_repair_{plan['candidate_plan_id'].removeprefix('devplan_')}_tests.py",
                "content": "assert True\n",
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
    require(result.get("ok") is True and result.get("status") == "product_repair_candidate_ready", "anchor_repair_cycle_completes")
    require(len(provider_calls) == 2, "anchor_repair_uses_one_bounded_retry")
    require(result.get("source_modified") is False, "active_source_remains_unchanged")
    persisted = "\n".join(path.read_text(encoding="utf-8", errors="ignore") for path in runtime.rglob("*.json"))
    require(sentinel not in persisted, "rejected_candidate_is_not_persisted")

print(json.dumps({
    "suite": "v2503.4.4-duplicate-anchor-repair",
    "ok": True,
    "passed": len(checks),
    "failed": 0,
    "checks": checks,
    "source_modified": False,
    "application_authorized": False,
    "installation_authorized": False,
}, sort_keys=True))
