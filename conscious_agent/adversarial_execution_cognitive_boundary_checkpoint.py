from __future__ import annotations

"""Read-only v1239.9 Adversarial Execution and Cognitive-Boundary checkpoint."""

import ast
import hashlib
from pathlib import Path
from typing import Any

from checkpoint_registry import inspect_checkpoint_registry
from checkpoint_progress import retained_checkpoint_progress
from adversarial_execution_cognitive_boundary import (
    ASSESSMENT_STATES,
    ATTACK_CATEGORIES,
    AUTHORITY_FLAGS,
    CONTRACT_VERSION as RETAINED_CONTRACT_VERSION,
    REVIEW_DISPOSITIONS,
    attack_registry,
    build_adversarial_execution_cognitive_boundary_contract,
    upstream_boundary_contracts,
)

CONTRACT_VERSION = "v1239.9"
CHECKPOINT_ID = "adversarial-execution-cognitive-boundary-checkpoint"
MILESTONE_NAME = "Adversarial Execution and Cognitive-Boundary Testing"
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
            if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id in {"QUICK_STAGE_NAMES", "LEGACY_QUICK_STAGE_NAMES"} for target in node.targets):
                value = ast.literal_eval(node.value)
                names.update(str(item) for item in value)
    except Exception:
        pass
    return names


def build_adversarial_execution_cognitive_boundary_checkpoint(*, source_root: str | Path | None = None, runtime_root=None) -> dict[str, Any]:
    del runtime_root
    source = Path(source_root or Path(__file__).resolve().parents[1]).resolve()
    before, before_count = _tree_signature(source)
    contract = build_adversarial_execution_cognitive_boundary_contract()
    attacks = attack_registry()
    upstream = upstream_boundary_contracts()
    registry = inspect_checkpoint_registry(source_root=source)
    descriptor = next((row for row in registry.get("checkpoints", []) if row.get("checkpoint_id") == CHECKPOINT_ID), {})
    module = (source / "conscious_agent/adversarial_execution_cognitive_boundary.py").read_text(encoding="utf-8")
    chat = (source / "conscious_agent/ordinary_chat_development_campaign.py").read_text(encoding="utf-8")
    api = (source / "conscious_agent/api_server.py").read_text(encoding="utf-8")
    cli = (source / "eidolon.py").read_text(encoding="utf-8")
    metadata = (source / "conscious_agent/release_metadata.py").read_text(encoding="utf-8")
    roadmap = (source / "README_NEXT_STEPS.md").read_text(encoding="utf-8")
    history = (source / "README_RELEASE_HISTORY.md").read_text(encoding="utf-8")
    verifier = (source / "tools/release_verify.py").read_text(encoding="utf-8")
    expected_stages = {
        "v1239.2-adversarial-execution-cognitive-boundary-foundations",
        "v1239.5-adversarial-execution-boundary-attacks",
        "v1239.8-adversarial-cognitive-compound-boundary-attacks",
        "v1239.9-adversarial-execution-cognitive-boundary-checkpoint",
    }
    expected_docs = (
        "archive/docs/legacy_dependencies/bundle_reviews/BUNDLE_REVIEW_V1239_0_2.md", "archive/docs/legacy_dependencies/bundle_reviews/BUNDLE_REVIEW_V1239_3_5.md", "archive/docs/legacy_dependencies/bundle_reviews/BUNDLE_REVIEW_V1239_6_8.md",
        "archive/docs/legacy_dependencies/validation/Eidolon_v1239_9_FINAL_VALIDATION.md", "archive/docs/legacy_dependencies/handoffs/DESKTOP_CODEX_HANDOFF_V1239_9.md",
    )
    progress = retained_checkpoint_progress(
        source,
        checkpoint_version="1239.9",
        successor_version="1240.0",
        successor_surface="conscious_agent/integrated_developer_beta.py",
    )
    counts = attacks.get("category_counts") or {}
    checks = {
        "contract_ok": contract.get("ok") is True,
        "retained_contract_version": contract.get("contract_version") == RETAINED_CONTRACT_VERSION,
        "roadmap_path": contract.get("roadmap_path") == ROADMAP_PATH,
        "attack_registry_ok": attacks.get("ok") is True,
        "attack_count": attacks.get("attack_case_count") == 28,
        "execution_attacks": counts.get("execution_boundary") == 12,
        "cognitive_attacks": counts.get("cognitive_boundary") == 8,
        "compound_attacks": counts.get("compound_boundary") == 8,
        "categories": ATTACK_CATEGORIES == {"execution_boundary", "cognitive_boundary", "compound_boundary"},
        "states": ASSESSMENT_STATES == {"attack_blocked", "evidence_incomplete", "lineage_rejected"},
        "review_dispositions": REVIEW_DISPOSITIONS == {"acknowledge_blocked", "hold", "reject_evidence", "request_changes"},
        "upstream_contracts": upstream.get("ok") is True and upstream.get("upstream_contract_count") == 8,
        "upstream_authority_false": contract.get("all_upstream_dangerous_authority_false") is True,
        "missing_never_passes": contract.get("missing_timeout_or_incomplete_evidence_never_passes") is True,
        "cognition_not_authority": contract.get("conversation_reflection_learning_goals_and_motivation_are_not_authority") is True,
        "records_do_not_compose": contract.get("advisory_records_never_compose_into_execution_authority") is True,
        "provider_untrusted": contract.get("provider_output_untrusted") is True,
        "sandbox_truth": contract.get("os_level_sandbox_not_claimed") is True,
        "module_prepare": "def prepare_adversarial_boundary_assessment(" in module,
        "module_review": "def review_adversarial_boundary_assessment(" in module,
        "module_registry": "def attack_registry(" in module,
        "module_no_attack": '"attack_execution_authorized": False' in module,
        "module_no_cognition": '"cognition_write_authorized": False' in module,
        "chat_route": "process_adversarial_execution_cognitive_boundary_control" in chat,
        "api_registry": "adversarial-boundary-attack-registry" in api,
        "api_assessments": "adversarial-boundary-assessments" in api,
        "api_reviews": "adversarial-boundary-reviews" in api,
        "api_checkpoint": CHECKPOINT_ID in api,
        "cli_registry": '"adversarial-boundary-attack-registry"' in cli,
        "cli_assessments": '"adversarial-boundary-assessments"' in cli,
        "cli_reviews": '"adversarial-boundary-reviews"' in cli,
        "cli_checkpoint": f'"{CHECKPOINT_ID}"' in cli,
        "metadata_version": progress.get("checkpoint_retained") is True,
        "metadata_milestone": progress.get("coherent") is True,
        "metadata_next": progress.get("started") is True,
        "retained_v1238_marker": "v1238.9 Broader Project and Language Adapters" in metadata,
        "roadmap_current": "v1239.9" in roadmap,
        "roadmap_next": "v1240" in roadmap,
        "history_current": "v1239.9" in history,
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
        "status": "adversarial_execution_cognitive_boundary_checkpoint_ready" if ok else "adversarial_execution_cognitive_boundary_checkpoint_blocked",
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
        "project_scoped": True,
        "source_signature_before": before,
        "source_signature_after": after,
        "source_signature_unchanged": unchanged,
        "source_file_count_before": before_count,
        "source_file_count_after": after_count,
        "runtime_data_read": False,
        "runtime_data_written": False,
        "attacks_executed": False,
        "private_state_fetched": False,
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
