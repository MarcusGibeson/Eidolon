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

from initiative_evidence_intake import (
    EVIDENCE_CLASSES,
    build_initiative_evidence_intake,
    public_evidence_contains_private_fields,
)
from supervised_initiative_queue import (
    build_supervised_initiative_shortlist,
    inspect_supervised_initiative_queue,
    queue_supervised_initiative,
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
        relative = path.relative_to(ROOT).as_posix()
        parts = set(Path(relative).parts)
        if (
            relative.startswith("data/")
            or parts.intersection({"__pycache__", ".git", ".venv", "venv", "install_backups", "node_modules", "dist", "build"})
            or relative.endswith((".pyc", ".pyo", ".zip", ".log"))
        ):
            continue
        rows.append((relative, hashlib.sha256(path.read_bytes()).hexdigest()))
    return hashlib.sha256(json.dumps(rows, separators=(",", ":")).encode()).hexdigest()


before = source_signature()
structural = {
    "candidate_id": "discovery-" + "a" * 20,
    "evidence_digest": "b" * 64,
    "eligibility_digest": "c" * 64,
    "source_module": "conscious_agent/example.py",
    "proposed_destination_module": "conscious_agent/example_helpers.py",
    "source_symbols": ["build_example", "inspect_example"],
    "test_reference_file_count": 11,
    "estimated_dependency_count": 0,
    "confidence": 1.0,
    "reversibility_classification": "bounded_new_module_retained_wrapper_candidate",
}
operator_finding = {
    "finding_id": "eval_finding_20260822T120000_abcdef123456",
    "record_digest": "d" * 64,
    "state": "open",
    "issue_domain": "interface",
    "severity": "blocking",
    "attempt_count": 4,
    "operator_confirmed": True,
    "updated_at": "2026-08-22T12:00:00Z",
    "private_title": "must never leave intake",
    "private_details": "must never leave intake",
}
intake = build_initiative_evidence_intake(
    structural_candidates=[structural],
    conversation_findings=[operator_finding],
)
require(intake["ok"], "intake_ready")
require(set(intake["class_counts"]) == set(EVIDENCE_CLASSES), "all_evidence_classes_normalized")
require(intake["record_count"] == 2, "structural_and_operator_evidence_retained")
require(not public_evidence_contains_private_fields(intake), "private_finding_fields_excluded")
require(intake["records"][0]["evidence_class"] == "conversation_quality_finding", "observed_product_impact_orders_first")
require(intake["records"][0]["impact_score"] > intake["records"][1]["impact_score"], "impact_order_is_measurable")
require(intake["records"][1]["structural_only"], "mechanical_extraction_labeled_structural_only")
require(intake["records"][1]["impact_score"] <= 0.42, "structural_value_has_honest_ceiling")
require(intake["unbound_priority_evidence_count"] == 1, "unmapped_high_impact_finding_remains_visible")
require(intake["implementation_ready_count"] == 1, "only_bounded_candidate_is_implementation_ready")

inactive = build_initiative_evidence_intake(operator_findings=[{**operator_finding, "state": "resolved"}])
require(inactive["record_count"] == 0 and inactive["rejected_or_inactive_count"] == 1, "resolved_findings_do_not_drive_work")

hardening = {
    "eligible_candidates": [structural],
    "hardening_digest": "e" * 64,
}
comparison = {
    "ordered_comparison": [{
        "candidate_id": structural["candidate_id"],
        "quality_score": 0.99,
        "evidence_digest": structural["evidence_digest"],
        "eligibility_digest": structural["eligibility_digest"],
    }],
    "comparison_digest": "f" * 64,
}
shortlist = build_supervised_initiative_shortlist(hardening, comparison, evidence_intake=intake)
selected = shortlist["shortlist"][0]
require(shortlist["ok"] and shortlist["shortlist_count"] == 1, "shortlist_remains_compatible")
require(selected["evidence_class"] == "structural_debt", "candidate_binds_exact_evidence_class")
require(selected["practical_benefit"] == "maintainability_and_regression_risk_reduction", "practical_benefit_is_explicit")
require(len(selected["acceptance_criteria"]) == 3, "acceptance_criteria_are_explicit")
require(selected["impact_review_required"], "low_impact_work_is_not_mislabeled")
require(shortlist["unbound_priority_evidence_count"] == 1, "shortlist_preserves_unbound_priority_count")
require(not shortlist["observed_product_impact_present"], "shortlist_does_not_claim_product_impact")

with tempfile.TemporaryDirectory(prefix="eidolon-v1501-3-") as directory:
    queued = queue_supervised_initiative(
        shortlist,
        discovery_digest="1" * 64,
        comparison_digest=comparison["comparison_digest"],
        runtime_root=directory,
    )
    require(queued["ok"], "initiative_queued")
    record = queued["initiative"]
    require(record["evidence_intake_digest"] == intake["intake_digest"], "queue_binds_intake_digest")
    require(record["selected"]["acceptance_criteria"] == selected["acceptance_criteria"], "queue_persists_acceptance_criteria")
    require(record["unbound_priority_evidence_count"] == 1, "queue_preserves_unbound_evidence")
    restarted = inspect_supervised_initiative_queue(directory)
    require(restarted["recent_records"][-1]["selected"]["impact_score"] == selected["impact_score"], "impact_evidence_survives_restart")

require(not intake["provider_contacted"], "intake_contacts_no_provider")
require(not intake["proposal_created"] and not intake["workspace_prepared"], "intake_creates_no_development_state")
require(not intake["source_modified"] and not intake["authority_granted"], "intake_grants_no_authority")
require(source_signature() == before, "suite_preserves_authoritative_source")

print(json.dumps({
    "ok": True,
    "suite": "v1501.3-initiative-evidence-intake",
    "passed": len(CHECKS),
    "failed": 0,
    "checks": CHECKS,
    "provider_contacted": False,
    "source_modified": False,
    "authority_granted": False,
}, indent=2, sort_keys=True))
