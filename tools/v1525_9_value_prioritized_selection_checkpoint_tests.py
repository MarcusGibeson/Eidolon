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
for path in (ROOT, ROOT / "conscious_agent", ROOT / "tools"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from initiative_evidence_intake import build_initiative_evidence_intake
from initiative_evidence_review import build_initiative_evidence_review, control_initiative_evidence_review
from initiative_value_prioritization import (
    build_value_prioritized_initiative_shortlist,
    value_prioritization_contract,
    value_prioritized_initiative_response,
    MAX_CONSECUTIVE_STRUCTURAL_INSTALLS,
)
from supervised_initiative_queue import inspect_supervised_initiative_queue, queue_supervised_initiative

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
contract = value_prioritization_contract()
require(contract["contract_version"] == "v1525.9", "v1517_selection_contract_version")
require(contract["selection_owner"] == "existing_supervised_initiative_queue", "v1517_reuses_existing_queue")
require(contract["value_owner"] == "initiative_value_model", "v1517_reuses_value_model")
require(not contract["provider_contacted"] and not contract["source_modified"] and not contract["authority_granted"], "v1517_selection_contract_is_authority_inert")
require(contract["max_consecutive_structural_installs"] == MAX_CONSECUTIVE_STRUCTURAL_INSTALLS, "portfolio_policy_structural_budget_is_explicit")

structural = {
    "candidate_id": "discovery-" + "1" * 20,
    "evidence_digest": "a" * 64,
    "eligibility_digest": "b" * 64,
    "source_module": "conscious_agent/mechanical.py",
    "proposed_destination_module": "conscious_agent/mechanical_helpers.py",
    "source_symbols": ["build_mechanical", "inspect_mechanical"],
    "test_reference_file_count": 60,
    "estimated_dependency_count": 0,
    "confidence": 1.0,
    "reversibility_classification": "bounded_new_module_retained_wrapper_candidate",
}
repair = {
    "candidate_id": "discovery-" + "2" * 20,
    "evidence_digest": "c" * 64,
    "eligibility_digest": "d" * 64,
    "source_module": "conscious_agent/chat_runtime.py",
    "proposed_destination_module": "conscious_agent/chat_runtime_repair.py",
    "source_symbols": ["respond_to_user"],
    "test_reference_file_count": 4,
    "estimated_dependency_count": 2,
    "confidence": 0.9,
    "reversibility_classification": "bounded_new_module_retained_wrapper_candidate",
}
hardening = {"eligible_candidates": [structural, repair], "hardening_digest": "e" * 64}
comparison = {
    "ordered_comparison": [
        {"candidate_id": structural["candidate_id"], "quality_score": 0.99, "evidence_digest": structural["evidence_digest"], "eligibility_digest": structural["eligibility_digest"]},
        {"candidate_id": repair["candidate_id"], "quality_score": 0.78, "evidence_digest": repair["evidence_digest"], "eligibility_digest": repair["eligibility_digest"]},
    ],
    "comparison_digest": "f" * 64,
}
defect = {
    "finding_id": "finding-repetition-visible",
    "record_digest": "9" * 64,
    "candidate_id": repair["candidate_id"],
    "source_module": repair["source_module"],
    "issue_domain": "conversation",
    "state": "open",
    "severity": "blocking",
    "frequency": 7,
    "confidence": 0.96,
    "operator_confirmed": True,
    "freshness": "current",
    "acceptance_criteria": ["repetition_reproduced", "repetition_removed", "conversation_regression_passes"],
}
intake = build_initiative_evidence_intake(structural_candidates=[structural, repair], conversation_findings=[defect])
with tempfile.TemporaryDirectory() as td:
    runtime = Path(td)
    shortlist = build_value_prioritized_initiative_shortlist(
        hardening,
        comparison,
        evidence_intake=intake,
        runtime_root=runtime,
    )
    require(shortlist["ok"] and shortlist["selection_made"], "v1518_value_prioritized_selection_is_ready")
    require(shortlist["selected_candidate_id"] == repair["candidate_id"], "v1518_visible_defect_candidate_outranks_easy_structural_candidate")
    selected = shortlist["shortlist"][0]
    require(selected["evidence_digest"] == repair["evidence_digest"], "v1518_dynamic_candidate_evidence_digest_remains_authority_lineage")
    require(selected["value_evidence_digest"] != selected["evidence_digest"], "v1518_value_evidence_is_separately_bound")
    require(selected["value_evidence_id"].startswith("initev_"), "v1518_value_evidence_identity_is_explicit")
    require(not selected["structural_only"], "v1518_product_evidence_is_not_mislabeled_structural")
    require(selected["title"].startswith("Repair conversation"), "v1519_operator_explanation_describes_product_repair")
    require("observable product behavior" in selected["reason"], "v1519_selection_reason_explains_practical_value")
    response = value_prioritized_initiative_response(shortlist)
    require("prioritized" in response and repair["candidate_id"] in response, "v1519_concise_operator_response_explains_lineage")
    require("creates no proposal" in response, "v1519_response_preserves_authority_boundary")

    queued = queue_supervised_initiative(shortlist, discovery_digest="7" * 64, comparison_digest=comparison["comparison_digest"], runtime_root=runtime)
    require(queued["ok"] and queued["status"] == "supervised_initiative_queued", "v1520_value_selected_candidate_enters_existing_queue")
    qrow = queued["initiative"]
    require(qrow["selected"]["value_evidence_id"] == selected["value_evidence_id"], "v1520_queue_persists_value_evidence_lineage")
    require(qrow["selected"]["value_digest"] == selected["value_digest"], "v1520_queue_persists_value_digest")
    require(not qrow["proposal_created"] and not qrow["workspace_prepared"], "v1520_queue_selection_still_creates_no_development_state")

    restarted = inspect_supervised_initiative_queue(runtime)
    require(restarted["active_count"] == 1, "v1521_value_selected_queue_survives_restart")
    persisted = restarted["recent_records"][-1]
    require(persisted["selected"]["priority_score"] == selected["priority_score"], "v1521_restart_preserves_priority_score")
    replay = queue_supervised_initiative(shortlist, discovery_digest="7" * 64, comparison_digest=comparison["comparison_digest"], runtime_root=runtime)
    require(replay["ok"] and replay["idempotent"] and not replay["runtime_mutated"], "v1521_queue_replay_is_exactly_once")

# v1522: high-value unbound evidence blocks structural busywork rather than pretending it is executable.
unbound = {
    "finding_id": "finding-unmapped-daily-use-breakage",
    "record_digest": "8" * 64,
    "issue_domain": "interface",
    "state": "open",
    "severity": "critical",
    "frequency": 9,
    "confidence": 1.0,
    "operator_confirmed": True,
    "freshness": "current",
}
unbound_intake = build_initiative_evidence_intake(structural_candidates=[structural], conversation_findings=[unbound])
unbound_hardening = {"eligible_candidates": [structural], "hardening_digest": "6" * 64}
unbound_comparison = {"ordered_comparison": [{"candidate_id": structural["candidate_id"], "quality_score": 1.0, "evidence_digest": structural["evidence_digest"], "eligibility_digest": structural["eligibility_digest"]}], "comparison_digest": "5" * 64}
with tempfile.TemporaryDirectory() as td:
    runtime = Path(td)
    blocked = build_value_prioritized_initiative_shortlist(unbound_hardening, unbound_comparison, evidence_intake=unbound_intake, runtime_root=runtime)
    require(not blocked["ok"] and not blocked["selection_made"], "v1522_unbound_higher_value_evidence_blocks_low_value_selection")
    require(blocked["status"] == "higher_value_evidence_requires_candidate_binding", "v1522_block_reason_is_explicit")
    require(blocked["blocking_evidence_id"].startswith("initev_"), "v1522_blocking_evidence_is_attributable")
    require(blocked["shortlist_count"] == 1, "v1522_lower_value_candidate_remains_reviewable_but_unselected")
    require("did not choose lower-value structural cleanup" in value_prioritized_initiative_response(blocked), "v1522_operator_guidance_resists_busywork")

    structural_history = [
        {"lifecycle_state": "operator_installed", "selected": {"structural_only": True}}
        for _ in range(MAX_CONSECUTIVE_STRUCTURAL_INSTALLS)
    ]
    budget_blocked = build_value_prioritized_initiative_shortlist(
        unbound_hardening,
        unbound_comparison,
        evidence_intake=build_initiative_evidence_intake(structural_candidates=[structural]),
        recent_initiatives=structural_history,
        runtime_root=runtime,
    )
    require(not budget_blocked["ok"] and budget_blocked["selection_blocked_by_maintenance_budget"], "portfolio_policy_blocks_unbounded_structural_run")
    require(budget_blocked["status"] == "structural_maintenance_budget_exhausted", "portfolio_policy_block_reason_is_explicit")
    require(budget_blocked["consecutive_structural_installs"] == MAX_CONSECUTIVE_STRUCTURAL_INSTALLS, "portfolio_policy_reports_structural_streak")
    require("product defect" in value_prioritized_initiative_response(budget_blocked), "portfolio_policy_requests_product_evidence_binding")

    product_after_history = build_value_prioritized_initiative_shortlist(
        hardening,
        comparison,
        evidence_intake=intake,
        recent_initiatives=structural_history,
        runtime_root=runtime,
    )
    require(product_after_history["ok"] and product_after_history["selected_candidate_id"] == repair["candidate_id"], "portfolio_policy_allows_product_work_after_structural_budget")

    # v1523 operator can explicitly defer the unbound evidence; that annotation, not a hidden heuristic, removes its block.
    review = build_initiative_evidence_review(unbound_intake, runtime_root=runtime)
    high = review["records"][0]
    deferred = control_initiative_evidence_review("defer", high["evidence_id"], high["review_digest"][:16], unbound_intake, runtime_root=runtime)
    require(deferred["ok"], "v1523_operator_can_defer_blocking_evidence")
    resumed = build_value_prioritized_initiative_shortlist(unbound_hardening, unbound_comparison, evidence_intake=unbound_intake, runtime_root=runtime)
    require(resumed["ok"] and resumed["selected_candidate_id"] == structural["candidate_id"], "v1523_explicit_defer_allows_next_value_eligible_work")
    require(not resumed["selection_blocked_by_unbound_value"], "v1523_deferred_evidence_no_longer_blocks_selection")

    # v1524 stale review digest cannot silently alter selection state.
    stale_attempt = control_initiative_evidence_review("cancel", high["evidence_id"], high["review_digest"][:16], unbound_intake, runtime_root=runtime)
    require(not stale_attempt["ok"] and stale_attempt["status"] == "initiative_evidence_review_digest_mismatch", "v1524_stale_review_control_is_rejected")
    same = build_value_prioritized_initiative_shortlist(unbound_hardening, unbound_comparison, evidence_intake=unbound_intake, runtime_root=runtime)
    require(same["selected_candidate_id"] == structural["candidate_id"], "v1524_stale_control_cannot_change_selection")

# v1525 reconciliation/determinism/no authority.
again = build_value_prioritized_initiative_shortlist(hardening, comparison, evidence_intake=intake, runtime_root=ROOT / "__nonexistent_selection_runtime__")
again2 = build_value_prioritized_initiative_shortlist(hardening, comparison, evidence_intake=intake, runtime_root=ROOT / "__nonexistent_selection_runtime__")
require(again["shortlist_digest"] == again2["shortlist_digest"], "v1525_prioritized_shortlist_is_deterministic")
require(again["selected_candidate_id"] == repair["candidate_id"], "v1525_checkpoint_preserves_visible_defect_priority")
require(not again["proposal_created"] and not again["workspace_prepared"], "v1525_checkpoint_selection_is_not_execution")
require(not again["provider_contacted"] and not again["source_modified"] and not again["authority_granted"], "v1525_checkpoint_preserves_authority_boundary")
require(again["content_free"], "v1525_checkpoint_projection_is_content_free")
require(before == source_signature(), "v1525_9_suite_preserves_authoritative_source")

print(json.dumps({
    "ok": True,
    "suite": "v1517-v1525.9-value-prioritized-selection-checkpoint",
    "passed": len(CHECKS),
    "failed": 0,
    "checks": CHECKS,
    "provider_contacted": False,
    "source_modified": False,
    "authority_granted": False,
}, indent=2))
