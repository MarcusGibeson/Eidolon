from __future__ import annotations

import hashlib
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
from initiative_evidence_intake import build_initiative_evidence_intake
from isolated_coding_execution import _provider_prompt, _validate_generation
from operator_development_findings import record_operator_development_finding


checks: list[str] = []


def require(value: object, label: str) -> None:
    if not value:
        raise AssertionError(label)
    checks.append(label)


tracked = [
    ROOT / "conscious_agent" / "operator_development_findings.py",
    ROOT / "conscious_agent" / "evidence_to_candidate_planner.py",
    ROOT / "conscious_agent" / "isolated_coding_execution.py",
]
before = hashlib.sha256(b"".join(path.read_bytes() for path in tracked)).hexdigest()

finding_text = (
    "Record development finding: Bounded research now calibrates recommendation language correctly, but "
    "candidate-specific source discovery often fails to obtain credible independent evidence for demand, "
    "competition, and free-tier feasibility. Evidence matrices are also repeated unnecessarily in the final report."
)

with tempfile.TemporaryDirectory(prefix="eid-v2503-4-1-finding-") as directory:
    result = record_operator_development_finding(finding_text, runtime_root=directory)
    finding = result["development_finding"]
    require(result["ok"] and result["runtime_mutated"], "exact_operator_finding_is_recorded")
    require(finding["evidence_class"] == "operator_reported_defect", "research_finding_uses_product_defect_class")
    require(finding["issue_domain"] == "bounded_research", "research_finding_routes_to_bounded_research")
    require(finding["evidence_class"] != "conversation_quality_finding", "repeated_is_not_repeat_substring")
    intake = build_initiative_evidence_intake(operator_findings=[finding])
    planning = build_evidence_to_candidate_plans(intake, source_root=ROOT)
    plan = planning["plans"][0]
    require(plan["implementation_ready"], "research_finding_is_implementation_bindable")
    require(plan["affected_surface"] == "bounded_research", "research_plan_preserves_surface")
    require(plan["target_files"] == [
        "conscious_agent/bounded_research_reasoning.py",
        "conscious_agent/bounded_autonomous_web_research.py",
    ], "research_plan_uses_correct_source_owners")
    require(len(plan["test_files"]) == 4, "research_plan_uses_four_attributable_suites")
    require(all(path.startswith("tools/v2503_") for path in plan["test_files"]), "research_plan_uses_current_research_tests")
    require(not planning["provider_contacted"] and not planning["source_modified"], "planning_remains_review_only")

with tempfile.TemporaryDirectory(prefix="eid-v2503-4-1-legacy-") as directory:
    runtime = Path(directory)
    path = runtime / "development" / "operator_development_findings.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    description = finding_text.split(":", 1)[1].strip()
    legacy = {
        "finding_id": "opfind_28ffe6617c2c1bddcf53790d",
        "private_description": description,
        "description_digest": hashlib.sha256(json.dumps(description, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest(),
        "evidence_class": "conversation_quality_finding",
        "issue_domain": "model_quality",
        "severity": "high",
        "impact_score": 0.88,
        "state": "open",
        "confidence": 0.9,
        "frequency": 1,
        "freshness": "current",
        "operator_confirmed": True,
        "created_at": "2026-08-30T00:00:00Z",
        "updated_at": "2026-08-30T00:00:00Z",
        "record_digest": "legacy",
    }
    path.write_text(json.dumps({
        "schema_version": "1", "contract_version": "v2503.4", "revision": 1,
        "updated_at": "2026-08-30T00:00:00Z", "findings": [legacy],
    }), encoding="utf-8")
    result = record_operator_development_finding(finding_text, runtime_root=runtime)
    finding = result["development_finding"]
    require(result["event"] == "operator_development_finding_reclassified", "legacy_finding_is_reclassified")
    require(result["runtime_mutated"], "legacy_reclassification_is_persisted")
    require(finding["finding_id"] == legacy["finding_id"], "legacy_finding_identity_is_preserved")
    require(finding["evidence_class"] == "operator_reported_defect", "legacy_finding_class_is_repaired")
    require(finding["issue_domain"] == "bounded_research", "legacy_finding_domain_is_repaired")
    persisted = json.loads(path.read_text(encoding="utf-8"))
    require(persisted["revision"] == 2, "legacy_reclassification_advances_revision_once")
    require(persisted["contract_version"] == "v2503.4.1", "legacy_reclassification_updates_contract")

with tempfile.TemporaryDirectory(prefix="eid-v2503-4-1-conversation-") as directory:
    result = record_operator_development_finding(
        "Record development finding: Chat responses repeat the prior conversational target.",
        runtime_root=directory,
    )
    require(result["development_finding"]["issue_domain"] == "model_quality", "genuine_conversation_finding_still_routes")

with tempfile.TemporaryDirectory(prefix="eid-v2503-4-1-coding-") as directory:
    root = Path(directory)
    (root / "main.py").write_text("def answer():\n    return 'general'\n", encoding="utf-8")
    (root / "focused_tests.py").write_text("FIXTURE = 'Private fixture prose must not be copied'\n", encoding="utf-8")
    prompt = json.loads(_provider_prompt(
        request={"request_id": "devc_" + "a" * 24, "user_objective": "Repair general behavior"},
        plan={"context_paths": ["main.py", "focused_tests.py"], "verification_plan": ["focused_tests.py"]},
        inspection={}, root=root, execution_digest="b" * 64, attempt_number=1, previous_outcome=None,
    ))
    require("focused tests are verification evidence" in prompt["task"], "initial_prompt_requires_general_behavior")
    require("Do not copy or special-case prose literals" in prompt["task"], "initial_prompt_forbids_fixture_overfit")
    raw = json.dumps({"edits": [{"path": "main.py", "replacements": [{
        "old": "return 'general'", "new": "return 'Private fixture prose must not be copied'",
    }]}], "creates": []})
    try:
        _validate_generation(
            raw, request_id="devc_" + "a" * 24, execution_digest="b" * 64,
            attempt_number=1, root=root, test_paths=["focused_tests.py"],
        )
    except ValueError as error:
        require(str(error) == "test_fixture_literal_leakage", "literal_leakage_guard_remains_fail_closed")
    else:
        raise AssertionError("literal_leakage_guard_remains_fail_closed")

after = hashlib.sha256(b"".join(path.read_bytes() for path in tracked)).hexdigest()
require(before == after, "focused_suite_preserves_source")

print(json.dumps({
    "ok": True,
    "suite": "v2503.4.1-research-finding-routing-anti-overfit",
    "passed": len(checks),
    "failed": 0,
    "checks": checks,
    "provider_request_count": 0,
    "network_request_count": 0,
    "source_modified": False,
    "authority_expanded": False,
}, sort_keys=True))
