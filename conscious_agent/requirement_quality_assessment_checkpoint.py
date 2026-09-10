from __future__ import annotations

"""Read-only v1234.9 Requirement and Quality Assessment checkpoint."""

import ast
import hashlib
from pathlib import Path
from typing import Any

from checkpoint_registry import inspect_checkpoint_registry
from checkpoint_progress import retained_checkpoint_progress
from requirement_quality_assessment import (
    AUTHORITY_FLAGS,
    CLASSIFICATIONS,
    CONTRACT_VERSION as RETAINED_CONTRACT_VERSION,
    CRITERION_STATES,
    EVIDENCE_STATES,
    EVIDENCE_TYPES,
    REQUIREMENT_CATEGORIES,
    REQUIREMENT_PRIORITIES,
    REVIEW_DISPOSITIONS,
    build_requirement_quality_assessment_contract,
)

CONTRACT_VERSION = "v1234.9"
CHECKPOINT_ID = "requirement-quality-assessment-checkpoint"
MILESTONE_NAME = "Requirement and Quality Assessment"
ROADMAP_PATH = "Balanced Mind-and-Action Path 3"


def _tree_signature(root: Path) -> tuple[str, int]:
    rows=[]
    count=0
    for path in sorted(root.rglob("*")):
        if not path.is_file() or "__pycache__" in path.parts or path.suffix in {".pyc", ".pyo"}:
            continue
        rows.append(f"{path.relative_to(root).as_posix()}:{hashlib.sha256(path.read_bytes()).hexdigest()}")
        count += 1
    return hashlib.sha256("\n".join(rows).encode()).hexdigest(), count


def _quick_stage_names(text: str) -> set[str]:
    names: set[str] = set()
    try:
        tree=ast.parse(text)
        for node in tree.body:
            if isinstance(node, ast.Assign) and any(isinstance(t,ast.Name) and t.id in {"QUICK_STAGE_NAMES","LEGACY_QUICK_STAGE_NAMES"} for t in node.targets):
                names.update(str(item) for item in ast.literal_eval(node.value))
    except Exception:
        pass
    return names


def build_requirement_quality_assessment_checkpoint(*, source_root: str | Path | None = None, runtime_root=None) -> dict[str, Any]:
    del runtime_root
    source=Path(source_root or Path(__file__).resolve().parents[1]).resolve()
    before,before_count=_tree_signature(source)
    contract=build_requirement_quality_assessment_contract()
    registry=inspect_checkpoint_registry(source_root=source)
    descriptor=next((row for row in registry.get("checkpoints",[]) if row.get("checkpoint_id")==CHECKPOINT_ID),{})
    module=(source/"conscious_agent/requirement_quality_assessment.py").read_text(encoding="utf-8")
    chat=(source/"conscious_agent/ordinary_chat_development_campaign.py").read_text(encoding="utf-8")
    api=(source/"conscious_agent/api_server.py").read_text(encoding="utf-8")
    cli=(source/"eidolon.py").read_text(encoding="utf-8")
    metadata=(source/"conscious_agent/release_metadata.py").read_text(encoding="utf-8")
    roadmap=(source/"README_NEXT_STEPS.md").read_text(encoding="utf-8")
    history=(source/"README_RELEASE_HISTORY.md").read_text(encoding="utf-8")
    verifier=(source/"tools/release_verify.py").read_text(encoding="utf-8")
    expected_stages={
        "v1234.2-requirement-quality-assessment-foundations",
        "v1234.5-requirement-quality-assessment-operator-review",
        "v1234.8-requirement-quality-assessment-adversarial-reliability",
        "v1234.9-requirement-quality-assessment-checkpoint",
    }
    expected_docs=(
        "archive/docs/legacy_dependencies/bundle_reviews/BUNDLE_REVIEW_V1234_0_2.md","archive/docs/legacy_dependencies/bundle_reviews/BUNDLE_REVIEW_V1234_3_5.md","archive/docs/legacy_dependencies/bundle_reviews/BUNDLE_REVIEW_V1234_6_8.md",
        "archive/docs/legacy_dependencies/validation/Eidolon_v1234_9_FINAL_VALIDATION.md","archive/docs/legacy_dependencies/handoffs/DESKTOP_CODEX_HANDOFF_V1234_9.md",
    )
    progress=retained_checkpoint_progress(source,checkpoint_version="1234.9",successor_version="1235.0",successor_surface="conscious_agent/evidence_backed_development_outcome_lessons.py")
    checks={
        "contract_ok":contract.get("ok") is True,
        "retained_contract_version":contract.get("contract_version")==RETAINED_CONTRACT_VERSION,
        "roadmap_path":contract.get("roadmap_path")==ROADMAP_PATH,
        "exact_resource_binding":contract.get("exact_resource_assessment_and_review_binding") is True,
        "optional_outcome_binding":contract.get("optional_sealed_outcome_binding") is True,
        "structured_requirements":contract.get("structured_requirements_and_acceptance_criteria") is True,
        "evidence_digest_binding":contract.get("evidence_linkage_is_digest_bound") is True,
        "deterministic_classification":contract.get("deterministic_requirement_classification") is True,
        "quality_risk_uncertainty":contract.get("quality_risk_and_uncertainty_visible") is True,
        "rollback_goal_alignment":contract.get("rollback_and_goal_alignment_visible") is True,
        "remediation_proposal_only":contract.get("remediation_proposal_only") is True,
        "operator_review_required":contract.get("operator_review_required") is True,
        "exact_chat_controls":contract.get("ordinary_chat_exact_controls") is True,
        "hardening_required":contract.get("restart_replay_stale_tamper_privacy_contradiction_hardening_required") is True,
        "assessment_not_approval":contract.get("assessment_does_not_approve_work") is True,
        "evidence_does_not_run_tests":contract.get("evidence_does_not_run_tests") is True,
        "fresh_authority_required":contract.get("fresh_separate_authority_required") is True,
        "category_coverage":len(REQUIREMENT_CATEGORIES)>=10,
        "priority_coverage":REQUIREMENT_PRIORITIES=={"required","optional"},
        "criterion_state_coverage":CRITERION_STATES=={"defined","ambiguous"},
        "evidence_type_coverage":len(EVIDENCE_TYPES)>=6,
        "evidence_state_coverage":len(EVIDENCE_STATES)>=7,
        "classification_coverage":CLASSIFICATIONS=={"satisfied","partially_satisfied","unsatisfied","unverified","contradictory","out_of_scope","blocked_by_missing_evidence"},
        "review_disposition_coverage":len(REVIEW_DISPOSITIONS)>=5,
        "module_prepare":"def prepare_requirement_quality_assessment(" in module,
        "module_review":"def review_requirement_quality_assessment(" in module,
        "module_public_assessments":"def public_requirement_quality_assessments(" in module,
        "module_public_reviews":"def public_requirement_quality_assessment_reviews(" in module,
        "module_resource_binding":"def _resource_basis(" in module,
        "module_classification":"def _classify(" in module,
        "module_evaluation":"def _evaluate(" in module,
        "module_no_test_run":'"evidence_does_not_run_tests": True' in module,
        "module_no_work_approval":'"assessment_does_not_approve_work": True' in module,
        "module_no_requirement_mutation":'"requirement_mutation_authorized": False' in module,
        "module_no_acceptance_authority":'"acceptance_authorized": False' in module,
        "module_no_apply_authority":'"apply_authorized": False' in module,
        "chat_route":"process_requirement_quality_assessment_control" in chat,
        "api_assessments":"requirement-quality-assessments" in api,
        "api_reviews":"requirement-quality-assessment-reviews" in api,
        "api_checkpoint":CHECKPOINT_ID in api,
        "cli_assessments":'"requirement-quality-assessments"' in cli,
        "cli_reviews":'"requirement-quality-assessment-reviews"' in cli,
        "cli_checkpoint":f'"{CHECKPOINT_ID}"' in cli,
        "metadata_version":progress.get("checkpoint_retained") is True,
        "metadata_milestone":progress.get("coherent") is True,
        "metadata_next":progress.get("started") is True,
        "roadmap_current":"v1234.9" in roadmap,
        "roadmap_next":"v1235" in roadmap,
        "history_current":"v1234.9" in history,
        "release_stages_registered":expected_stages.issubset(_quick_stage_names(verifier)),
        "release_commands_registered":all(stage in verifier for stage in expected_stages),
        "docs_present":all((source/name).is_file() for name in expected_docs),
        "registry_present":bool(descriptor),
        "registry_version":descriptor.get("contract_version")==CONTRACT_VERSION,
        "registry_read_only":descriptor.get("read_only") is True,
        "registry_no_inputs":descriptor.get("required_input_count")==0,
    }
    for key,expected in AUTHORITY_FLAGS.items():
        checks[f"authority_{key}"]=contract.get(key) is expected
    after,after_count=_tree_signature(source)
    unchanged=before==after and before_count==after_count
    checks["source_signature_unchanged"]=unchanged
    passed=sum(bool(value) for value in checks.values()); total=len(checks); ok=passed==total
    return {
        "ok":ok,
        "status":"requirement_quality_assessment_checkpoint_ready" if ok else "requirement_quality_assessment_checkpoint_blocked",
        "checkpoint_id":CHECKPOINT_ID,
        "contract_version":CONTRACT_VERSION,
        "retained_contract_version":RETAINED_CONTRACT_VERSION,
        "milestone_name":MILESTONE_NAME,
        "roadmap_path":ROADMAP_PATH,
        "checks":checks,"passed":passed,"total":total,
        "read_only":True,"content_free":True,
        "source_signature_before":before,"source_signature_after":after,"source_signature_unchanged":unchanged,
        "source_file_count_before":before_count,"source_file_count_after":after_count,
        "runtime_data_read":False,"runtime_data_written":False,
        "provider_contacted":False,"commands_executed":False,"tests_executed":False,
        "project_modified":False,"requirements_modified":False,"queue_modified":False,"schedule_modified":False,
        "work_approved":False,"project_change_applied":False,"cognition_written":False,"source_modified":False,
        "authority_granted":False,
        **AUTHORITY_FLAGS,
    }
