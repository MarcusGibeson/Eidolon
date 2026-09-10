from __future__ import annotations

"""Read-only v1238.9 Broader Project and Language Adapters checkpoint."""

import ast
import hashlib
from pathlib import Path
from typing import Any

from checkpoint_registry import inspect_checkpoint_registry
from checkpoint_progress import retained_checkpoint_progress
from broader_project_language_adapters import (
    AUTHORITY_FLAGS,
    CONTRACT_VERSION as RETAINED_CONTRACT_VERSION,
    DETECTION_STATES,
    REVIEW_DISPOSITIONS,
    adapter_registry,
    build_broader_project_language_adapter_contract,
)

CONTRACT_VERSION = "v1238.9"
CHECKPOINT_ID = "broader-project-language-adapters-checkpoint"
MILESTONE_NAME = "Broader Project and Language Adapters"
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
                names.update(str(item) for item in ast.literal_eval(node.value))
    except Exception:
        pass
    return names


def build_broader_project_language_adapters_checkpoint(*, source_root: str | Path | None = None, runtime_root=None) -> dict[str, Any]:
    del runtime_root
    source = Path(source_root or Path(__file__).resolve().parents[1]).resolve()
    before, before_count = _tree_signature(source)
    contract = build_broader_project_language_adapter_contract()
    registry_contract = adapter_registry()
    registry = inspect_checkpoint_registry(source_root=source)
    descriptor = next((row for row in registry.get("checkpoints", []) if row.get("checkpoint_id") == CHECKPOINT_ID), {})
    module = (source / "conscious_agent/broader_project_language_adapters.py").read_text(encoding="utf-8")
    chat = (source / "conscious_agent/ordinary_chat_development_campaign.py").read_text(encoding="utf-8")
    api = (source / "conscious_agent/api_server.py").read_text(encoding="utf-8")
    cli = (source / "eidolon.py").read_text(encoding="utf-8")
    metadata = (source / "conscious_agent/release_metadata.py").read_text(encoding="utf-8")
    roadmap = (source / "README_NEXT_STEPS.md").read_text(encoding="utf-8")
    history = (source / "README_RELEASE_HISTORY.md").read_text(encoding="utf-8")
    verifier = (source / "tools/release_verify.py").read_text(encoding="utf-8")
    expected_stages = {
        "v1238.2-broader-project-language-adapter-foundations",
        "v1238.5-broader-project-language-adapter-integration",
        "v1238.8-broader-project-language-adapter-adversarial-reliability",
        "v1238.9-broader-project-language-adapters-checkpoint",
    }
    expected_docs = (
        "archive/docs/legacy_dependencies/bundle_reviews/BUNDLE_REVIEW_V1238_0_2.md", "archive/docs/legacy_dependencies/bundle_reviews/BUNDLE_REVIEW_V1238_3_5.md", "archive/docs/legacy_dependencies/bundle_reviews/BUNDLE_REVIEW_V1238_6_8.md",
        "archive/docs/legacy_dependencies/validation/Eidolon_v1238_9_FINAL_VALIDATION.md", "archive/docs/legacy_dependencies/handoffs/DESKTOP_CODEX_HANDOFF_V1238_9.md",
    )
    progress = retained_checkpoint_progress(source, checkpoint_version="1238.9", successor_version="1239.0", successor_surface="conscious_agent/adversarial_execution_cognitive_boundary.py")
    checks = {
        "contract_ok": contract.get("ok") is True,
        "retained_contract_version": contract.get("contract_version") == RETAINED_CONTRACT_VERSION,
        "roadmap_path": contract.get("roadmap_path") == ROADMAP_PATH,
        "six_adapters": registry_contract.get("adapter_count") == 6,
        "registry_content_free": registry_contract.get("content_free") is True,
        "java_supported": contract.get("java_maven_and_gradle_supported") is True,
        "broader_languages_supported": contract.get("dotnet_rust_go_php_supported") is True,
        "existing_delegated": contract.get("existing_javascript_web_python_delegated") is True,
        "fail_closed": contract.get("ambiguous_mixed_and_nested_projects_fail_closed") is True,
        "content_free_detection": contract.get("content_free_inventory_digests") is True,
        "manifest_contents_not_read": contract.get("manifest_contents_not_read") is True,
        "bounded_templates": contract.get("bounded_build_and_test_command_templates") is True,
        "v1237_blueprint": contract.get("v1237_compatible_orchestration_blueprint") is True,
        "fresh_plan_review": contract.get("fresh_v1237_plan_review_required_for_use") is True,
        "exact_chat": contract.get("ordinary_chat_exact_review_controls") is True,
        "get_only": contract.get("get_only_api_inspection") is True,
        "hardening": contract.get("restart_replay_stale_tamper_privacy_contradiction_hardening_required") is True,
        "no_acceptance_authority": contract.get("adapter_acceptance_does_not_authorize_execution") is True,
        "no_blueprint_authority": contract.get("blueprint_does_not_authorize_next_tool") is True,
        "unsupported_defer": contract.get("unsupported_layouts_defer_without_guessing") is True,
        "review_dispositions": REVIEW_DISPOSITIONS == {"accept_adapter", "hold", "reject", "request_changes"},
        "detection_states": len(DETECTION_STATES) == 5,
        "module_prepare": "def prepare_broader_project_adapter_assessment(" in module,
        "module_review": "def review_broader_project_adapter_assessment(" in module,
        "module_blueprint": "def prepare_adapter_orchestration_blueprint(" in module,
        "module_no_command": '"command_execution_authorized": False' in module,
        "module_no_install": '"dependency_installation_authorized": False' in module,
        "chat_route": "process_broader_project_language_adapter_control" in chat,
        "api_assessments": "broader-project-language-adapter-assessments" in api,
        "api_registry": "broader-project-language-adapter-registry" in api,
        "api_checkpoint": CHECKPOINT_ID in api,
        "cli_assessments": '"broader-project-language-adapter-assessments"' in cli,
        "cli_registry": '"broader-project-language-adapter-registry"' in cli,
        "cli_checkpoint": f'"{CHECKPOINT_ID}"' in cli,
        "metadata_version": progress.get("checkpoint_retained") is True,
        "metadata_milestone": progress.get("coherent") is True,
        "metadata_next": progress.get("started") is True,
        "retained_v1237_marker": "v1237.9 Multi-Tool Orchestration" in metadata,
        "roadmap_current": "v1238.9" in roadmap,
        "roadmap_next": "v1239" in roadmap,
        "history_current": "v1238.9" in history,
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
        "status": "broader_project_language_adapters_checkpoint_ready" if ok else "broader_project_language_adapters_checkpoint_blocked",
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
