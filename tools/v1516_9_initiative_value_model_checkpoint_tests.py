from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
for path in (ROOT, ROOT / "conscious_agent", ROOT / "tools"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from initiative_evidence_intake import build_initiative_evidence_intake
from initiative_evidence_review import build_initiative_evidence_review
from initiative_value_model import (
    FACTOR_NAMES,
    build_initiative_value_model,
    initiative_value_contract,
    score_initiative_value,
)

CHECKS: list[str] = []

def require(value: bool, label: str) -> None:
    if not value:
        raise AssertionError(label)
    CHECKS.append(label)


def source_signature() -> str:
    rows = []
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(ROOT).as_posix()
        parts = set(Path(rel).parts)
        if rel.startswith("data/") or parts.intersection({"__pycache__", ".git", ".venv", "venv", "install_backups", "node_modules", "dist", "build"}) or rel.endswith((".pyc", ".pyo", ".zip", ".log")):
            continue
        rows.append((rel, hashlib.sha256(path.read_bytes()).hexdigest()))
    return hashlib.sha256(json.dumps(rows, separators=(",", ":")).encode()).hexdigest()

before = source_signature()
contract = initiative_value_contract()
require(contract["contract_version"] == "v1516.9", "v1509_contract_version")
require(tuple(contract["factors"]) == FACTOR_NAMES, "v1509_contract_has_required_factors")
require(abs(sum(contract["weights"].values()) - 1.0) < 1e-9, "v1509_weights_are_normalized")
require(contract["score_is_authority"] is False, "v1509_score_is_not_authority")
require(contract["provider_contacted"] is False and contract["source_modified"] is False, "v1509_model_is_portable_and_inert")

structural = {
    "candidate_id": "discovery-structural",
    "evidence_digest": "1" * 64,
    "eligibility_digest": "2" * 64,
    "source_module": "conscious_agent/large_helper.py",
    "proposed_destination_module": "conscious_agent/large_helper_split.py",
    "source_symbols": ["build_helper", "inspect_helper"],
    "test_reference_file_count": 80,
    "estimated_dependency_count": 0,
    "confidence": 1.0,
    "reversibility_classification": "bounded_new_module_retained_wrapper_candidate",
}
visible_defect = {
    "finding_id": "finding-visible-chat-defect",
    "record_digest": "3" * 64,
    "candidate_id": "repair-visible-chat-defect",
    "source_module": "conscious_agent/chat_runtime.py",
    "issue_domain": "conversation",
    "state": "open",
    "severity": "blocking",
    "frequency": 5,
    "confidence": 0.92,
    "operator_confirmed": True,
    "freshness": "current",
    "acceptance_criteria": ["scenario_reproduced", "scenario_repaired", "regression_passes"],
}
defect_candidate = {
    "candidate_id": "repair-visible-chat-defect",
    "source_module": "conscious_agent/chat_runtime.py",
    "source_symbols": ["respond"],
    "estimated_dependency_count": 2,
    "test_reference_file_count": 4,
    "reversibility": 0.82,
}
intake = build_initiative_evidence_intake(
    structural_candidates=[structural],
    conversation_findings=[visible_defect],
)
review = build_initiative_evidence_review(intake, runtime_root=ROOT / "__nonexistent_value_model_runtime__")
model = build_initiative_value_model(review, candidates=[structural, defect_candidate])
require(model["ok"] and model["record_count"] == 2, "v1510_value_model_scores_current_evidence")
require(model["records"][0]["candidate_id"] == "repair-visible-chat-defect", "v1510_visible_product_defect_outranks_structural_helper")
require(model["records"][0]["value_score"] > model["records"][1]["value_score"], "v1510_ranking_has_measurable_margin")
require(model["records"][1]["value_score"] <= 0.48, "v1510_structural_only_value_has_ceiling")
require(any(p["code"] == "metric_gaming_guard" for p in model["records"][1]["penalties"]), "v1510_test_count_cannot_game_value")
require(model["busywork_resistance_active"] and model["metric_gaming_resistance_active"], "v1510_anti_busywork_contract_is_explicit")

# v1511 factor explainability and evidence quality.
for row in model["records"]:
    require(set(row["factors"]) == set(FACTOR_NAMES), f"v1511_all_factors_present_{row['candidate_id']}")
    require(all(0.0 <= float(value) <= 1.0 for value in row["factors"].values()), f"v1511_factors_bounded_{row['candidate_id']}")
require(model["records"][0]["factors"]["strategic_value"] > model["records"][1]["factors"]["strategic_value"], "v1511_strategic_value_distinguishes_product_defect")
require(model["records"][0]["acceptance_criteria"], "v1511_acceptance_criteria_survive_scoring")
require(len(model["records"][0]["value_digest"]) == 64, "v1511_score_is_digest_bound")

# v1512 duplicate/busywork/reversibility/effort/dependency behavior.
duplicate_model = build_initiative_value_model(review, candidates=[structural, defect_candidate], prior_candidate_ids=["repair-visible-chat-defect"])
dup = next(row for row in duplicate_model["records"] if row["candidate_id"] == "repair-visible-chat-defect")
require(any(p["code"] == "duplicate_lineage" for p in dup["penalties"]), "v1512_duplicate_lineage_is_penalized")
require(dup["value_score"] < model["records"][0]["value_score"], "v1512_duplicate_penalty_reduces_value")
struct = next(row for row in model["records"] if row["candidate_id"] == "discovery-structural")
require(struct["factors"]["effort_fit"] > 0.8 and struct["factors"]["dependency_readiness"] > 0.9, "v1512_easy_structural_work_is_recognized_without_overvaluing_it")
require(any(p["code"] == "easy_low_value_busywork" for p in struct["penalties"]), "v1512_easy_low_value_work_is_explicit_busywork_risk")

# v1513 integration-friendly handling of unbound meaningful evidence.
unbound_intake = build_initiative_evidence_intake(operator_findings=[{
    "finding_id": "operator-visible-defect-unmapped",
    "record_digest": "4" * 64,
    "issue_domain": "interface",
    "severity": "critical",
    "frequency": 8,
    "confidence": 1.0,
    "operator_confirmed": True,
    "freshness": "current",
}])
unbound_review = build_initiative_evidence_review(unbound_intake, runtime_root=ROOT / "__nonexistent_value_model_runtime2__")
unbound_model = build_initiative_value_model(unbound_review)
require(unbound_model["unbound_high_value_count"] == 1, "v1513_unbound_high_value_evidence_remains_visible")
require(unbound_model["selection_eligible_count"] == 0, "v1513_unbound_evidence_is_not_mislabeled_executable")
require(unbound_model["highest_value_score"] >= 0.55, "v1513_unbound_problem_still_has_priority_signal")

# v1514 operator states can suppress selection without erasing evidence.
review_deferred = {**review, "records": [dict(row) for row in review["records"]]}
defect_row = next(row for row in review_deferred["records"] if row["candidate_id"] == "repair-visible-chat-defect")
defect_row["review_state"] = "deferred"
deferred_model = build_initiative_value_model(review_deferred, candidates=[structural, defect_candidate])
deferred = next(row for row in deferred_model["records"] if row["candidate_id"] == "repair-visible-chat-defect")
require(not deferred["selection_eligible"] and deferred["value_score"] == 0.0, "v1514_operator_defer_removes_selection_eligibility")
require(deferred["evidence_id"] == defect_row["evidence_id"], "v1514_defer_preserves_evidence_identity")

# v1515 realistic scenarios: stale high-severity evidence, high-effort capability, malformed numeric hints.
stale = dict(defect_row)
stale["review_state"] = "unreviewed"
stale["freshness"] = "stale"
stale_score = score_initiative_value(stale, candidate=defect_candidate)
require(any(p["code"] == "stale_evidence" for p in stale_score["penalties"]), "v1515_stale_evidence_is_discounted")
high_effort_candidate = {**defect_candidate, "estimated_dependency_count": 99, "source_symbols": [f"s{i}" for i in range(20)]}
high_effort = score_initiative_value(next(row for row in review["records"] if row["candidate_id"] == "repair-visible-chat-defect"), candidate=high_effort_candidate)
require(high_effort["factors"]["effort_fit"] < 0.1 and high_effort["factors"]["dependency_readiness"] == 0.0, "v1515_high_effort_and_dependency_risk_are_visible")
malformed = dict(next(row for row in review["records"] if row["candidate_id"] == "repair-visible-chat-defect"))
malformed["confidence"] = "not-a-number"
malformed["frequency_score"] = 99
malformed_score = score_initiative_value(malformed, candidate={"candidate_id": malformed["candidate_id"], "dependency_risk": -10})
require(all(0.0 <= float(value) <= 1.0 for value in malformed_score["factors"].values()), "v1515_malformed_numeric_inputs_fail_bounded")

# v1516 deterministic reconciliation and authority boundary.
again = build_initiative_value_model(review, candidates=[structural, defect_candidate])
require(model["value_model_digest"] == again["value_model_digest"], "v1516_scoring_is_deterministic")
require(model["records"] == again["records"], "v1516_order_is_deterministic")
require(model["provider_contacted"] is False and model["source_modified"] is False and model["authority_granted"] is False, "v1516_model_preserves_authority_boundary")
require(model["score_is_authority"] is False, "v1516_value_score_never_becomes_authority")
require(model["content_free"], "v1516_public_value_projection_is_content_free")

require(before == source_signature(), "v1516_9_suite_preserves_authoritative_source")
print(json.dumps({
    "ok": True,
    "suite": "v1509-v1516.9-initiative-value-model-checkpoint",
    "passed": len(CHECKS),
    "failed": 0,
    "checks": CHECKS,
    "provider_contacted": False,
    "source_modified": False,
    "authority_granted": False,
}, indent=2))
