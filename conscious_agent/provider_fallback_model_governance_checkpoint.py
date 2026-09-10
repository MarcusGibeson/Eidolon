from __future__ import annotations

"""Read-only v1243.9 Provider Fallback and Model Governance checkpoint."""

import ast
import hashlib
from pathlib import Path

from checkpoint_registry import inspect_checkpoint_registry
from provider_fallback_model_governance import (
    AUTHORITY_FLAGS,
    CONTRACT_VERSION as RETAINED_CONTRACT_VERSION,
    MILESTONE_NAME,
    ROADMAP_PATH,
    build_provider_model_governance_contract,
    provider_model_governance_dashboard_record,
    provider_model_governance_registry,
    render_provider_model_governance_dashboard_html,
)

CONTRACT_VERSION = "v1243.9"
CHECKPOINT_ID = "provider-fallback-model-governance-checkpoint"


def _signature(root: Path) -> tuple[str, int]:
    rows: list[str] = []
    count = 0
    for path in sorted(root.rglob("*")):
        if path.is_file() and "__pycache__" not in path.parts and path.suffix not in {".pyc", ".pyo"}:
            rows.append(f"{path.relative_to(root).as_posix()}:{hashlib.sha256(path.read_bytes()).hexdigest()}")
            count += 1
    return hashlib.sha256("\n".join(rows).encode()).hexdigest(), count


def _quick_stage_names(text: str) -> set[str]:
    names: set[str] = set()
    try:
        tree = ast.parse(text)
        for node in tree.body:
            if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id in {"QUICK_STAGE_NAMES", "LEGACY_QUICK_STAGE_NAMES"} for target in node.targets):
                names.update(ast.literal_eval(node.value))
    except Exception:
        pass
    return names


def build_provider_fallback_model_governance_checkpoint(*, source_root=None, runtime_root=None) -> dict:
    del runtime_root
    source = Path(source_root or Path(__file__).resolve().parents[1]).resolve()
    before, count_before = _signature(source)
    contract = build_provider_model_governance_contract()
    registry = provider_model_governance_registry()
    dashboard = provider_model_governance_dashboard_record()
    page = render_provider_model_governance_dashboard_html()
    descriptor = next((row for row in inspect_checkpoint_registry(source_root=source).get("checkpoints", []) if row.get("checkpoint_id") == CHECKPOINT_ID), {})
    names = (
        "conscious_agent/release_metadata.py",
        "README_NEXT_STEPS.md",
        "README_RELEASE_HISTORY.md",
        "tools/release_verify.py",
        "conscious_agent/api_server.py",
        "eidolon.py",
        "conscious_agent/ordinary_chat_development_campaign.py",
        "conscious_agent/dashboard.py",
    )
    files = {name: (source / name).read_text(encoding="utf-8") for name in names}
    stages = {
        "v1243.2-provider-fallback-model-governance-foundations",
        "v1243.5-provider-fallback-model-governance-operator-review",
        "v1243.8-provider-fallback-model-governance-adversarial-reliability",
        "v1243.9-provider-fallback-model-governance-checkpoint",
    }
    docs = (
        "archive/docs/legacy_dependencies/bundle_reviews/BUNDLE_REVIEW_V1243_0_2.md",
        "archive/docs/legacy_dependencies/bundle_reviews/BUNDLE_REVIEW_V1243_3_5.md",
        "archive/docs/legacy_dependencies/bundle_reviews/BUNDLE_REVIEW_V1243_6_8.md",
        "archive/docs/legacy_dependencies/validation/Eidolon_v1243_9_FINAL_VALIDATION.md",
        "archive/docs/legacy_dependencies/handoffs/DESKTOP_CODEX_HANDOFF_V1243_9.md",
    )
    checks = {
        "contract_ok": contract.get("ok") is True,
        "retained_modules": contract.get("retained_provider_model_module_count") == 7,
        "registry_ok": registry.get("ok") is True,
        "registry_inspection_only": registry.get("inspection_only") is True,
        "dashboard_read_only": dashboard.get("read_only") is True,
        "dashboard_no_provider_authority": dashboard.get("provider_contact_authorized") is False,
        "dashboard_page": "Provider Fallback and Model Governance" in page and "GET-only inspection" in page,
        "metadata": 'WORKING_SOURCE_VERSION = "1243.9"' in files["conscious_agent/release_metadata.py"] and "v1243.9 Provider Fallback and Model Governance Checkpoint" in files["conscious_agent/release_metadata.py"] and "v1244.0-v1244.2 Long-Running and Multi-Day Session Continuity Foundations" in files["conscious_agent/release_metadata.py"],
        "readmes": "v1243.9" in files["README_NEXT_STEPS.md"] and "v1243.9 Provider Fallback and Model Governance" in files["README_RELEASE_HISTORY.md"],
        "chat": "process_provider_model_governance_control" in files["conscious_agent/ordinary_chat_development_campaign.py"],
        "api": all(token in files["conscious_agent/api_server.py"] for token in ("provider-model-governance-registry", "provider-model-registry-snapshots", "provider-model-selection-proposals", "provider-fallback-assessments", CHECKPOINT_ID)),
        "cli": all(f'"{token}"' in files["eidolon.py"] for token in ("provider-model-governance-registry", "provider-model-registry-snapshots", "provider-model-selection-proposals", "provider-fallback-assessments", CHECKPOINT_ID)),
        "dashboard_routes": "/provider-model-governance" in files["conscious_agent/dashboard.py"] and "/api/provider-model-governance" in files["conscious_agent/dashboard.py"],
        "release_stages": stages.issubset(_quick_stage_names(files["tools/release_verify.py"])),
        "release_commands": all(stage in files["tools/release_verify.py"] for stage in stages),
        "docs": all((source / name).is_file() for name in docs),
        "registry_present": bool(descriptor),
        "registry_version": descriptor.get("contract_version") == CONTRACT_VERSION,
        "registry_read_only": descriptor.get("read_only") is True,
        "registry_no_inputs": descriptor.get("required_input_count") == 0,
        "local_remote_privacy": contract.get("local_remote_privacy_classification_required") is True,
        "compatibility_checks": contract.get("context_tool_streaming_compatibility_checked") is True,
        "tradeoffs": contract.get("quality_latency_cost_tradeoffs_recorded") is True,
        "no_auto_fallback": contract.get("provider_outage_never_triggers_automatic_fallback") is True,
        "fresh_contact_authority": contract.get("fresh_exact_provider_contact_authority_required") is True,
    }
    for key, expected in AUTHORITY_FLAGS.items():
        checks[f"authority_{key}"] = contract.get(key) is expected and registry.get(key) is expected and dashboard.get(key) is expected
    after, count_after = _signature(source)
    checks["source_unchanged"] = before == after and count_before == count_after
    passed = sum(map(bool, checks.values()))
    total = len(checks)
    ok = passed == total
    return {
        "ok": ok,
        "status": "provider_fallback_model_governance_checkpoint_ready" if ok else "provider_fallback_model_governance_checkpoint_blocked",
        "checkpoint_id": CHECKPOINT_ID,
        "contract_version": CONTRACT_VERSION,
        "retained_contract_version": RETAINED_CONTRACT_VERSION,
        "milestone_name": MILESTONE_NAME,
        "roadmap_path": ROADMAP_PATH,
        "passed": passed,
        "total": total,
        "checks": checks,
        "source_signature_before": before,
        "source_signature_after": after,
        "source_signature_unchanged": before == after,
        "source_file_count_before": count_before,
        "source_file_count_after": count_after,
        "read_only": True,
        "content_free": True,
        "runtime_data_read": False,
        "runtime_data_written": False,
        "provider_contacted": False,
        "commands_executed": False,
        "tests_executed": False,
        "project_modified": False,
        "source_modified": False,
        "cognition_written": False,
        "authority_granted": False,
        **AUTHORITY_FLAGS,
    }
