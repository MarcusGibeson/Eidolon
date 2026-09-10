from __future__ import annotations

"""Read-only v1233.9 Resource and Concurrency Governance checkpoint."""

import ast
import hashlib
from pathlib import Path
from typing import Any

from checkpoint_registry import inspect_checkpoint_registry
from checkpoint_progress import retained_checkpoint_progress
from resource_concurrency_governance import (
    ADMISSION_STATES,
    AUTHORITY_FLAGS,
    CLAIM_MODES,
    CONTRACT_VERSION as RETAINED_CONTRACT_VERSION,
    RESOURCE_STATES,
    RESOURCE_TYPES,
    REVIEW_DISPOSITIONS,
    build_resource_concurrency_governance_contract,
)

CONTRACT_VERSION = "v1233.9"
CHECKPOINT_ID = "resource-concurrency-governance-checkpoint"
MILESTONE_NAME = "Resource and Concurrency Governance"
ROADMAP_PATH = "Balanced Mind-and-Action Path 3"


def _tree_signature(root: Path) -> tuple[str, int]:
    rows: list[str] = []
    count = 0
    for path in sorted(root.rglob("*")):
        if not path.is_file() or "__pycache__" in path.parts or path.suffix in {".pyc", ".pyo"}:
            continue
        rows.append(f"{path.relative_to(root).as_posix()}:{hashlib.sha256(path.read_bytes()).hexdigest()}")
        count += 1
    return hashlib.sha256("\n".join(rows).encode()).hexdigest(), count


def _quick_stage_names(text: str) -> set[str]:
    names: set[str] = set()
    try:
        tree = ast.parse(text)
        for node in tree.body:
            if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id in {"QUICK_STAGE_NAMES", "LEGACY_QUICK_STAGE_NAMES"} for t in node.targets):
                names.update(str(item) for item in ast.literal_eval(node.value))
    except Exception:
        pass
    return names


def build_resource_concurrency_governance_checkpoint(*, source_root: str | Path | None = None, runtime_root=None) -> dict[str, Any]:
    del runtime_root
    source = Path(source_root or Path(__file__).resolve().parents[1]).resolve()
    before, before_count = _tree_signature(source)
    contract = build_resource_concurrency_governance_contract()
    registry = inspect_checkpoint_registry(source_root=source)
    descriptor = next((row for row in registry.get("checkpoints", []) if row.get("checkpoint_id") == CHECKPOINT_ID), {})
    module = (source / "conscious_agent/resource_concurrency_governance.py").read_text(encoding="utf-8")
    chat = (source / "conscious_agent/ordinary_chat_development_campaign.py").read_text(encoding="utf-8")
    api = (source / "conscious_agent/api_server.py").read_text(encoding="utf-8")
    cli = (source / "eidolon.py").read_text(encoding="utf-8")
    metadata = (source / "conscious_agent/release_metadata.py").read_text(encoding="utf-8")
    roadmap = (source / "README_NEXT_STEPS.md").read_text(encoding="utf-8")
    history = (source / "README_RELEASE_HISTORY.md").read_text(encoding="utf-8")
    verifier = (source / "tools/release_verify.py").read_text(encoding="utf-8")
    expected_stages = {
        "v1233.2-resource-concurrency-governance-foundations",
        "v1233.5-resource-concurrency-governance-operator-review",
        "v1233.8-resource-concurrency-governance-adversarial-reliability",
        "v1233.9-resource-concurrency-governance-checkpoint",
    }
    expected_docs = (
        "archive/docs/legacy_dependencies/bundle_reviews/BUNDLE_REVIEW_V1233_0_2.md",
        "archive/docs/legacy_dependencies/bundle_reviews/BUNDLE_REVIEW_V1233_3_5.md",
        "archive/docs/legacy_dependencies/bundle_reviews/BUNDLE_REVIEW_V1233_6_8.md",
        "archive/docs/legacy_dependencies/validation/Eidolon_v1233_9_FINAL_VALIDATION.md",
        "archive/docs/legacy_dependencies/handoffs/DESKTOP_CODEX_HANDOFF_V1233_9.md",
    )
    progress = retained_checkpoint_progress(source, checkpoint_version="1233.9", successor_version="1234.0", successor_surface="conscious_agent/requirement_quality_assessment.py")
    checks = {
        "contract_ok": contract.get("ok") is True,
        "retained_contract_version": contract.get("contract_version") == RETAINED_CONTRACT_VERSION,
        "roadmap_path": contract.get("roadmap_path") == ROADMAP_PATH,
        "active_or_paused_required": contract.get("active_or_paused_session_required") is True,
        "exact_resource_evidence_required": contract.get("exact_resource_evidence_required") is True,
        "exact_dependency_review_required": contract.get("exact_dependency_review_required") is True,
        "operator_review_required": contract.get("operator_review_required") is True,
        "queue_priority_binding": contract.get("queue_priority_binding") is True,
        "schedule_binding": contract.get("schedule_binding") is True,
        "dependency_binding": contract.get("dependency_readiness_binding") is True,
        "bounded_concurrency": contract.get("bounded_concurrency_limit") is True,
        "shared_exclusive_claims": contract.get("shared_and_exclusive_claims") is True,
        "capacity_detection": contract.get("capacity_conflict_detection") is True,
        "stale_abandoned_detection": contract.get("stale_and_abandoned_claim_detection") is True,
        "fairness_starvation": contract.get("fairness_and_starvation_evidence") is True,
        "preemption_proposal_only": contract.get("preemption_proposal_only") is True,
        "automatic_preemption_forbidden": contract.get("automatic_preemption_forbidden") is True,
        "exact_chat_controls": contract.get("ordinary_chat_exact_controls") is True,
        "hardening_required": contract.get("restart_replay_stale_tamper_privacy_conflict_hardening_required") is True,
        "resource_type_coverage": len(RESOURCE_TYPES) >= 12,
        "claim_mode_coverage": CLAIM_MODES == {"shared", "exclusive"},
        "resource_state_coverage": len(RESOURCE_STATES) >= 6,
        "admission_state_coverage": len(ADMISSION_STATES) >= 9,
        "review_disposition_coverage": len(REVIEW_DISPOSITIONS) >= 5,
        "module_prepare": "def prepare_resource_concurrency_governance_assessment(" in module,
        "module_review": "def review_resource_concurrency_governance_assessment(" in module,
        "module_public_list": "def public_resource_concurrency_governance_assessments(" in module,
        "module_public_reviews": "def public_resource_concurrency_governance_reviews(" in module,
        "module_dependency_binding": "def _dependency_basis(" in module,
        "module_conflict_evaluation": "def _evaluate(" in module,
        "module_no_os_lease_claim": '"resource_claims_are_not_os_leases": True' in module,
        "module_no_preemption": '"resource_preemption_authorized": False' in module,
        "module_fresh_execution": '"fresh_execution_authorization_required": True' in module,
        "module_fresh_resume": '"fresh_resume_authorization_required": True' in module,
        "chat_route": "process_resource_concurrency_governance_control" in chat,
        "api_assessments": "resource-concurrency-governance-assessments" in api,
        "api_reviews": "resource-concurrency-governance-reviews" in api,
        "api_checkpoint": CHECKPOINT_ID in api,
        "cli_assessments": '"resource-concurrency-governance-assessments"' in cli,
        "cli_reviews": '"resource-concurrency-governance-reviews"' in cli,
        "cli_checkpoint": f'"{CHECKPOINT_ID}"' in cli,
        "metadata_version": progress.get("checkpoint_retained") is True,
        "metadata_milestone": progress.get("coherent") is True,
        "metadata_next": progress.get("started") is True,
        "roadmap_current": "v1233.9" in roadmap,
        "roadmap_next": "v1234" in roadmap,
        "history_current": "v1233.9" in history,
        "release_stages_registered": expected_stages.issubset(_quick_stage_names(verifier)),
        "release_commands_registered": all(stage in verifier for stage in expected_stages),
        "docs_present": all((source / name).is_file() for name in expected_docs),
        "registry_present": bool(descriptor),
        "registry_version": descriptor.get("contract_version") == CONTRACT_VERSION,
        "registry_read_only": descriptor.get("read_only") is True,
        "registry_no_inputs": descriptor.get("required_input_count") == 0,
    }
    for key, expected in AUTHORITY_FLAGS.items():
        checks[f"authority_{key}"] = contract.get(key) is expected
    after, after_count = _tree_signature(source)
    unchanged = before == after and before_count == after_count
    checks["source_signature_unchanged"] = unchanged
    passed = sum(bool(value) for value in checks.values())
    total = len(checks)
    ok = passed == total
    return {
        "ok": ok,
        "status": "resource_concurrency_governance_checkpoint_ready" if ok else "resource_concurrency_governance_checkpoint_blocked",
        "checkpoint_id": CHECKPOINT_ID,
        "contract_version": CONTRACT_VERSION,
        "retained_contract_version": RETAINED_CONTRACT_VERSION,
        "milestone_name": MILESTONE_NAME,
        "roadmap_path": ROADMAP_PATH,
        "checks": checks,
        "passed": passed,
        "total": total,
        "read_only": True,
        "content_free": True,
        "source_signature_before": before,
        "source_signature_after": after,
        "source_signature_unchanged": unchanged,
        "source_file_count_before": before_count,
        "source_file_count_after": after_count,
        "runtime_data_read": False,
        "runtime_data_written": False,
        "provider_contacted": False,
        "commands_executed": False,
        "tests_executed": False,
        "project_modified": False,
        "queue_modified": False,
        "schedule_modified": False,
        "session_preempted": False,
        "resource_lease_created": False,
        "cognition_written": False,
        "source_modified": False,
        "authority_granted": False,
        **AUTHORITY_FLAGS,
    }
