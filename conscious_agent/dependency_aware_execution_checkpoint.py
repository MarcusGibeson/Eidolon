from __future__ import annotations

"""Read-only v1232.9 Dependency-Aware Execution checkpoint."""

import ast
import hashlib
from pathlib import Path
from typing import Any

from checkpoint_registry import inspect_checkpoint_registry
from checkpoint_progress import retained_checkpoint_progress
from dependency_aware_execution import (
    AUTHORITY_FLAGS,
    CONTRACT_VERSION as RETAINED_CONTRACT_VERSION,
    DEPENDENCY_STATES,
    DEPENDENCY_TYPES,
    READINESS_STATES,
    build_dependency_aware_execution_contract,
)

CONTRACT_VERSION = "v1232.9"
CHECKPOINT_ID = "dependency-aware-execution-checkpoint"
MILESTONE_NAME = "Dependency-Aware Execution"
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


def build_dependency_aware_execution_checkpoint(*, source_root: str | Path | None = None, runtime_root=None) -> dict[str, Any]:
    del runtime_root
    source = Path(source_root or Path(__file__).resolve().parents[1]).resolve()
    before, before_count = _tree_signature(source)
    contract = build_dependency_aware_execution_contract()
    registry = inspect_checkpoint_registry(source_root=source)
    descriptor = next((row for row in registry.get("checkpoints", []) if row.get("checkpoint_id") == CHECKPOINT_ID), {})
    module = (source / "conscious_agent/dependency_aware_execution.py").read_text(encoding="utf-8")
    chat = (source / "conscious_agent/ordinary_chat_development_campaign.py").read_text(encoding="utf-8")
    api = (source / "conscious_agent/api_server.py").read_text(encoding="utf-8")
    cli = (source / "eidolon.py").read_text(encoding="utf-8")
    metadata = (source / "conscious_agent/release_metadata.py").read_text(encoding="utf-8")
    roadmap = (source / "README_NEXT_STEPS.md").read_text(encoding="utf-8")
    history = (source / "README_RELEASE_HISTORY.md").read_text(encoding="utf-8")
    verifier = (source / "tools/release_verify.py").read_text(encoding="utf-8")
    expected_stages = {
        "v1232.2-dependency-aware-execution-foundations",
        "v1232.5-dependency-aware-execution-operator-review",
        "v1232.8-dependency-aware-execution-adversarial-reliability",
        "v1232.9-dependency-aware-execution-checkpoint",
    }
    expected_docs = (
        "archive/docs/legacy_dependencies/bundle_reviews/BUNDLE_REVIEW_V1232_0_2.md",
        "archive/docs/legacy_dependencies/bundle_reviews/BUNDLE_REVIEW_V1232_3_5.md",
        "archive/docs/legacy_dependencies/bundle_reviews/BUNDLE_REVIEW_V1232_6_8.md",
        "archive/docs/legacy_dependencies/validation/Eidolon_v1232_9_FINAL_VALIDATION.md",
        "archive/docs/legacy_dependencies/handoffs/DESKTOP_CODEX_HANDOFF_V1232_9.md",
    )
    progress = retained_checkpoint_progress(source, checkpoint_version="1232.9", successor_version="1233.0", successor_surface="conscious_agent/resource_concurrency_governance.py")
    checks = {
        "contract_ok": contract.get("ok") is True,
        "retained_contract_version": contract.get("contract_version") == RETAINED_CONTRACT_VERSION,
        "roadmap_path": contract.get("roadmap_path") == ROADMAP_PATH,
        "active_or_paused_required": contract.get("active_or_paused_session_required") is True,
        "exact_dependency_evidence_required": contract.get("exact_dependency_evidence_required") is True,
        "operator_review_required": contract.get("operator_review_required") is True,
        "original_plan_immutable": contract.get("original_plan_immutable") is True,
        "historical_receipts_immutable": contract.get("historical_receipts_immutable") is True,
        "accepted_revision_binding": contract.get("accepted_plan_revision_binding") is True,
        "cycle_detection": contract.get("dependency_graph_cycle_detection") is True,
        "exact_chat_controls": contract.get("ordinary_chat_exact_controls") is True,
        "hardening_required": contract.get("restart_replay_stale_tamper_privacy_contradiction_hardening_required") is True,
        "type_coverage": len(DEPENDENCY_TYPES) >= 8,
        "state_coverage": len(DEPENDENCY_STATES) >= 7,
        "readiness_coverage": len(READINESS_STATES) >= 8,
        "module_prepare": "def prepare_dependency_aware_execution_assessment(" in module,
        "module_review": "def review_dependency_aware_execution_assessment(" in module,
        "module_public_list": "def public_dependency_aware_execution_assessments(" in module,
        "module_public_reviews": "def public_dependency_aware_execution_reviews(" in module,
        "module_cycle": "def _has_cycle(" in module,
        "module_revision_binding": "_current_plan_revision_basis" in module,
        "module_readiness_not_authority": '"dependency_readiness_is_execution_authority": False' in module,
        "module_fresh_execution": '"fresh_execution_authorization_required": True' in module,
        "module_fresh_resume": '"fresh_resume_authorization_required": True' in module,
        "chat_route": "process_dependency_aware_execution_control" in chat,
        "api_assessments": "dependency-aware-execution-assessments" in api,
        "api_reviews": "dependency-aware-execution-reviews" in api,
        "api_checkpoint": CHECKPOINT_ID in api,
        "cli_assessments": '"dependency-aware-execution-assessments"' in cli,
        "cli_reviews": '"dependency-aware-execution-reviews"' in cli,
        "cli_checkpoint": f'"{CHECKPOINT_ID}"' in cli,
        "metadata_version": progress.get("checkpoint_retained") is True,
        "metadata_milestone": progress.get("coherent") is True,
        "metadata_next": progress.get("started") is True,
        "roadmap_current": "v1232.9" in roadmap,
        "roadmap_next": "v1233" in roadmap,
        "history_current": "v1232.9" in history,
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
        "status": "dependency_aware_execution_checkpoint_ready" if ok else "dependency_aware_execution_checkpoint_blocked",
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
        "cognition_written": False,
        "source_modified": False,
        "authority_granted": False,
        **AUTHORITY_FLAGS,
    }
