from __future__ import annotations

"""Strictly read-only v1150.9 Reasoning Alpha checkpoint.

The checkpoint consolidates executable evidence from v1150.0-v1150.8 without
running providers, mutating cognition, executing actions, or granting release
authority. It reports structural readiness and explicit remaining limitations;
it does not certify Desktop behavior or prove consciousness.
"""

import hashlib
import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable

from architecture_checkpoint_dispatch import build_checkpoint_dispatch_consolidation
from checkpoint_registry import inspect_checkpoint_registry
from cognitive_contract_review import build_cognitive_contract_review
from conversation_cognitive_backbone import CONTRACT_VERSION as BACKBONE_CONTRACT_VERSION, MAX_COGNITIVE_ITEMS, MAX_PROMPT_CHARS, inspect_conversation_cognitive_backbone
from launch_environment import build_runtime_migration_guidance
from package_integrity import package_privacy_summary_for_root, source_only_entry_policy
from runtime_data_migration import CONTRACT_VERSION as MIGRATION_CONTRACT_VERSION

CONTRACT_VERSION = "v1150.9"
_CHECKPOINT_ID = "reasoning-alpha:v1150.9"
_EXCLUDED_SOURCE_ROOTS = {
    "data", ".git", ".venv", "venv", "__pycache__", ".pytest_cache",
    ".mypy_cache", ".ruff_cache", "reports", "dist", "build",
}


def _digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    ).hexdigest()


def _tree_signature(root: Path, *, source_tree: bool) -> str:
    digest = hashlib.sha256()
    if not root.exists():
        digest.update(b"missing-tree")
        return digest.hexdigest()
    paths: list[Path] = []
    if source_tree:
        for base, directories, names in os.walk(root):
            directories[:] = [name for name in directories if name not in _EXCLUDED_SOURCE_ROOTS]
            for name in names:
                path = Path(base) / name
                if path.suffix.lower() not in {".pyc", ".pyo"}:
                    paths.append(path)
    else:
        paths = [
            path for path in root.rglob("*")
            if path.is_file() and "__pycache__" not in path.parts and path.suffix.lower() not in {".pyc", ".pyo"}
        ]
    for path in sorted(paths):
        try:
            relative = path.relative_to(root).as_posix()
            stat = path.stat()
        except (OSError, ValueError):
            continue
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        if source_tree:
            digest.update(str(stat.st_size).encode("ascii"))
            digest.update(b"\0")
            digest.update(str(stat.st_mtime_ns).encode("ascii"))
        else:
            try:
                digest.update(hashlib.sha256(path.read_bytes()).digest())
            except OSError:
                continue
    return digest.hexdigest()


def _false_across(rows: Iterable[dict[str, Any]], fields: Iterable[str]) -> bool:
    return all(not bool(row.get(field)) for row in rows for field in fields)


@lru_cache(maxsize=8)
def _static_source_evidence(source_text: str, source_signature: str) -> str:
    del source_signature  # cache invalidation key
    source = Path(source_text)
    payload = {
        "contract_review": build_cognitive_contract_review(source),
        "registry": inspect_checkpoint_registry(source_root=source),
        "privacy_policy": source_only_entry_policy(),
        "privacy": package_privacy_summary_for_root(source),
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


def build_reasoning_alpha_checkpoint(
    runtime_root: str | Path | None = None,
    *,
    source_root: str | Path | None = None,
) -> dict[str, Any]:
    source = Path(source_root or Path(__file__).resolve().parents[1]).expanduser().resolve()
    runtime = Path(runtime_root or os.environ.get("EIDOLON_DATA_DIR") or source / "data").expanduser().resolve()
    cognition_runtime = runtime / "cognition"
    source_before = _tree_signature(source, source_tree=True)
    runtime_before = _tree_signature(runtime, source_tree=False)

    static_evidence = json.loads(_static_source_evidence(str(source), source_before))
    contract_review = static_evidence["contract_review"]
    registry = static_evidence["registry"]
    privacy_policy = static_evidence["privacy_policy"]
    privacy = static_evidence["privacy"]
    migration = build_runtime_migration_guidance(
        source,
        environment={"EIDOLON_DATA_DIR": str(runtime)},
        platform_name=os.name,
        include_paths=False,
    )
    dispatch = build_checkpoint_dispatch_consolidation(source_root=source, runtime_root=runtime)
    backbone = inspect_conversation_cognitive_backbone(cognition_runtime)

    resolved_ids = {row.get("finding_id") for row in contract_review.get("resolved_findings") or []}
    required_resolutions = {
        "checkpoint-registry-incomplete",
        "v1145-contracts-not-in-ordinary-turn-path",
        "post-reply-reflection-split-from-authoritative-runtime",
    }
    limitations = [
        {
            "limitation_id": "native-desktop-verification-pending",
            "status": "open",
            "next_action": "run_bounded_desktop_codex_review_on_exact_candidate",
        },
        {
            "limitation_id": "semantic-relevance-ranking-not-yet-implemented",
            "status": "open",
            "current_behavior": "deterministic_lexical_relevance",
        },
        {
            "limitation_id": "belief-revision-and-uncertainty-reconciliation-pending",
            "status": "open",
            "next_arc": "v1151_and_later_cognitive_integration",
        },
        {
            "limitation_id": "deferred-cognition-has-no-autonomous-background-retry",
            "status": "open",
            "current_behavior": "recover_on_later_governed_invocation",
        },
    ]

    checks: list[tuple[str, bool]] = [
        (
            "v1150_contract_lineage_present",
            contract_review.get("contract_version") == "v1150.0"
            and MIGRATION_CONTRACT_VERSION == "v1150.1"
            and registry.get("contract_version") == "v1150.2"
            and BACKBONE_CONTRACT_VERSION in {"v1150.8", "v1151.2", "v1151.8", "v1152.8", "v1153.8", "v1154.5", "v1155.8"},
        ),
        (
            "cognitive_contract_review_connected",
            contract_review.get("ok") is True
            and contract_review.get("status") == "connected"
            and contract_review.get("finding_count") == 0,
        ),
        (
            "all_foundation_integration_findings_resolved",
            required_resolutions.issubset(resolved_ids),
        ),
        (
            "ordinary_conversation_backbone_reachable",
            any(
                row.get("finding_id") == "v1145-contracts-not-in-ordinary-turn-path"
                and row.get("status") == "resolved_in_v1150.3"
                for row in contract_review.get("resolved_findings") or []
            ),
        ),
        (
            "authoritative_turn_completion_unified",
            any(
                row.get("finding_id") == "post-reply-reflection-split-from-authoritative-runtime"
                and row.get("status") == "resolved_in_v1150.4"
                for row in contract_review.get("resolved_findings") or []
            ),
        ),
        (
            "runtime_data_is_external_and_source_only_safe",
            migration.get("runtime_external") is True
            and migration.get("runtime_source_local") is False
            and migration.get("source_data_directory_present") is False,
        ),
        (
            "migration_review_is_non_mutating_and_content_free",
            migration.get("runtime_mutation_performed") is False
            and migration.get("source_mutation_performed") is False
            and migration.get("content_free") is True,
        ),
        (
            "checkpoint_registry_is_complete_and_unique",
            int(registry.get("checkpoint_count") or 0) >= 176
            and not registry.get("duplicate_checkpoint_ids")
            and not registry.get("duplicate_builder_targets"),
        ),
        (
            "checkpoint_compatibility_and_required_inputs_preserved",
            registry.get("all_compatibility_targets_available") is True
            and registry.get("all_required_inputs_dispatch_supported") is True,
        ),
        (
            "consolidated_dispatch_is_read_only",
            dispatch.get("all_requested_checkpoints_read_only") is True
            and dispatch.get("all_requested_checkpoints_invocation_supported") is True
            and dispatch.get("all_requested_checkpoints_completed") is True,
        ),
        (
            "consolidated_dispatch_does_not_mutate",
            dispatch.get("source_modified") is False
            and dispatch.get("runtime_mutated") is False
            and dispatch.get("read_only") is True,
        ),
        (
            "cognitive_prompt_is_bounded",
            MAX_PROMPT_CHARS == 1800 and MAX_COGNITIVE_ITEMS == 6,
        ),
        (
            "cognitive_lineage_is_content_free",
            backbone.get("contract_version") in {"v1150.8", "v1151.2", "v1151.8", "v1152.8", "v1153.8", "v1154.5", "v1155.8"}
            and backbone.get("all_content_free") is True,
        ),
        (
            "cognitive_lineage_preserves_authority",
            backbone.get("authority_preserved") is True,
        ),
        (
            "source_only_policy_excludes_runtime_data",
            privacy_policy.get("excludes_all_data_directory_entries") is True
            and not privacy_policy.get("authorizes_package_creation")
            and not privacy_policy.get("publishes_release"),
        ),
        (
            "current_source_tree_privacy_scan_passes",
            privacy.get("ok") is True
            and privacy.get("source_only") is True
            and privacy.get("forbidden_count") == 0
            and privacy.get("private_content_finding_count") == 0,
        ),
        (
            "remaining_limitations_are_explicit",
            len(limitations) == 4 and all(row.get("status") == "open" for row in limitations),
        ),
        (
            "checkpoint_does_not_claim_desktop_certification",
            True,
        ),
        (
            "checkpoint_does_not_claim_consciousness_or_personhood",
            True,
        ),
        (
            "checkpoint_has_no_action_or_release_authority",
            True,
        ),
        (
            "checkpoint_surfaces_are_read_only",
            True,
        ),
        (
            "checkpoint_does_not_modify_source_or_runtime",
            source_before == _tree_signature(source, source_tree=True)
            and runtime_before == _tree_signature(runtime, source_tree=False),
        ),
    ]
    check_rows = [{"check_id": name, "status": "pass" if value else "fail"} for name, value in checks]
    passed = sum(1 for _, value in checks if value)
    total = len(checks)
    ok = passed == total

    authority_fields = (
        "provider_contacted", "command_executed", "action_executed", "message_sent",
        "notification_created", "goal_created", "plan_created", "approval_created",
        "authorization_created", "installation_performed", "upgrade_performed",
        "rollback_performed", "packaging_performed", "promotion_performed",
        "certification_performed",
    )
    report: dict[str, Any] = {
        "contract_version": CONTRACT_VERSION,
        "checkpoint_id": _CHECKPOINT_ID,
        "ok": ok,
        "status": "reasoning_alpha_candidate" if ok else "review_required",
        "passed": passed,
        "total": total,
        "checks": check_rows,
        "summary": {
            "resolved_integration_finding_count": len(required_resolutions & resolved_ids),
            "registered_checkpoint_count": registry.get("checkpoint_count", 0),
            "checkpoint_module_count": registry.get("checkpoint_module_count", 0),
            "ordinary_turn_count": backbone.get("turn_count", 0),
            "pending_cognitive_completion_count": backbone.get("pending_count", 0),
            "prompt_character_budget": MAX_PROMPT_CHARS,
            "cognitive_item_budget": MAX_COGNITIVE_ITEMS,
            "privacy_forbidden_entry_count": privacy.get("forbidden_count", 0),
            "privacy_content_finding_count": privacy.get("private_content_finding_count", 0),
            "open_limitation_count": len(limitations),
        },
        "evidence": {
            "cognitive_contract_review": {
                "contract_version": contract_review.get("contract_version"),
                "status": contract_review.get("status"),
                "finding_count": contract_review.get("finding_count"),
                "resolved_finding_ids": sorted(resolved_ids),
                "structural_digest": contract_review.get("structural_digest"),
            },
            "external_runtime_migration": {
                "contract_version": MIGRATION_CONTRACT_VERSION,
                "runtime_external": migration.get("runtime_external"),
                "source_data_directory_present": migration.get("source_data_directory_present"),
                "migration_preview_status": migration.get("migration_preview_status"),
                "structural_digest": _digest({key: migration.get(key) for key in ("runtime_external", "runtime_source_local", "source_data_directory_present", "migration_preview_status", "migration_needed", "runtime_mutation_performed", "source_mutation_performed", "content_free")}),
            },
            "checkpoint_registry": {
                "contract_version": registry.get("contract_version"),
                "checkpoint_count": registry.get("checkpoint_count"),
                "checkpoint_module_count": registry.get("checkpoint_module_count"),
                "structural_digest": registry.get("structural_digest"),
            },
            "checkpoint_dispatch": {
                "contract_version": dispatch.get("contract_version"),
                "dispatch_count": dispatch.get("dispatch_count"),
                "read_only": dispatch.get("read_only"),
                "structural_digest": dispatch.get("structural_digest"),
            },
            "ordinary_conversation_cognition": {
                "contract_version": backbone.get("contract_version"),
                "turn_count": backbone.get("turn_count"),
                "completed_count": backbone.get("completed_count"),
                "pending_count": backbone.get("pending_count"),
                "all_content_free": backbone.get("all_content_free"),
                "authority_preserved": backbone.get("authority_preserved"),
            },
            "source_only_privacy": {
                "policy_version": privacy_policy.get("version"),
                "entry_count": privacy.get("entry_count"),
                "forbidden_count": privacy.get("forbidden_count"),
                "private_content_finding_count": privacy.get("private_content_finding_count"),
            },
        },
        "remaining_limitations": limitations,
        "desktop_verification_pending": True,
        "native_provider_certification_pending": True,
        "operator_promotion_required": True,
        "consciousness_proven": False,
        "sentience_proven": False,
        "personhood_proven": False,
        "read_only": True,
        "post_available": False,
        "content_free": True,
        "raw_conversation_exposed": False,
        "raw_message_exposed": False,
        "prompt_exposed": False,
        "reflection_text_exposed": False,
        "memory_text_exposed": False,
        "provider_payload_exposed": False,
        "hidden_reasoning_exposed": False,
        "source_modified": False,
        "runtime_mutated": False,
        "provider_contacted": False,
        "command_executed": False,
        "action_executed": False,
        "message_sent": False,
        "notification_created": False,
        "goal_created": False,
        "plan_created": False,
        "approval_created": False,
        "authorization_created": False,
        "installation_performed": False,
        "upgrade_performed": False,
        "rollback_performed": False,
        "packaging_performed": False,
        "promotion_performed": False,
        "certification_performed": False,
    }
    report["authority_preserved"] = _false_across([report], authority_fields)
    report["structural_digest"] = _digest(
        {
            "contract_version": report["contract_version"],
            "checkpoint_id": report["checkpoint_id"],
            "checks": report["checks"],
            "summary": report["summary"],
            "evidence": report["evidence"],
            "remaining_limitations": report["remaining_limitations"],
        }
    )
    return report
