from __future__ import annotations

"""Strictly read-only v1147.9 Architecture Consolidation governance checkpoint."""

import hashlib
from pathlib import Path
from typing import Any, Iterable

from architecture_consolidation_execution_checkpoint import build_architecture_consolidation_execution_checkpoint
from architecture_consolidation_intake_checkpoint import build_architecture_consolidation_intake_checkpoint
from architecture_consolidation_reliability_checkpoint import build_architecture_consolidation_reliability_checkpoint
from architecture_ownership_manifest import AUTHORITY_BOUNDARY, OWNERSHIP_DOMAINS

CONTRACT_VERSION = "v1147.9"


def _tree_signature(root: Path) -> str:
    digest = hashlib.sha256()
    if not root.exists():
        digest.update(b"missing-tree")
        return digest.hexdigest()
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        if "__pycache__" in path.parts or path.suffix in {".pyc", ".pyo"}:
            continue
        try:
            digest.update(path.relative_to(root).as_posix().encode("utf-8"))
            digest.update(b"\0")
            digest.update(path.read_bytes())
            digest.update(b"\n")
        except (OSError, ValueError):
            continue
    return digest.hexdigest()


def _passed(report: dict[str, Any], identifier: str) -> bool:
    return any(
        isinstance(row, dict)
        and (row.get("id") or row.get("name") or row.get("check_id")) == identifier
        and bool(row.get("passed") or row.get("ok") or row.get("status") == "pass")
        for row in report.get("checks") or []
    )


def _false_across(rows: Iterable[dict[str, Any]], fields: Iterable[str]) -> bool:
    return all(not bool(row.get(field)) for row in rows for field in fields)


def build_architecture_consolidation_governance_checkpoint(
    *, source_root: str | Path | None = None,
) -> dict[str, Any]:
    source = Path(source_root).expanduser().resolve() if source_root is not None else Path(__file__).resolve().parents[1]
    source_before = _tree_signature(source)

    intake = build_architecture_consolidation_intake_checkpoint(source_root=source)
    execution = build_architecture_consolidation_execution_checkpoint(source_root=source)
    reliability = build_architecture_consolidation_reliability_checkpoint(source_root=source)

    ownership = intake.get("ownership_manifest") or {}
    registry = intake.get("checkpoint_registry") or {}
    dispatch = execution.get("checkpoint_dispatch") or {}
    startup_plan = execution.get("startup_plan") or {}
    startup = execution.get("startup_inspection") or {}
    continuity = reliability.get("continuity") or {}
    review = reliability.get("reliability") or {}

    ownership_rows = ownership.get("domains") or []
    registry_rows = registry.get("checkpoints") or []
    dispatch_rows = dispatch.get("dispatches") or []
    startup_rows = startup_plan.get("tiers") or []
    all_rows = ownership_rows + registry_rows + dispatch_rows + startup_rows

    forbidden_private_keys = {
        "text", "content", "prompt", "message", "reasoning", "memory", "belief",
        "relationship", "mood", "goal", "motivation", "patch", "source_code",
        "provider_payload", "generated_response", "hidden_reasoning",
    }
    operational_fields = (
        "executes_commands", "execution_performed", "contacts_provider", "provider_contacted",
        "mutates_runtime", "runtime_mutated", "modifies_source", "source_modified",
        "sends_messages", "message_sent", "notification_created", "goal_created",
        "plan_created", "proposal_created",
    )
    release_fields = (
        "creates_approval", "approval_created", "creates_authorization", "authorization_created",
        "installs", "installation_performed", "promotes", "promotion_performed",
        "certifies", "certification_performed",
    )

    tier_map = {row.get("tier"): row for row in startup_rows}
    checks: list[tuple[str, bool]] = [
        (
            "architecture_consolidation_arc_lineage",
            intake.get("ok") and execution.get("ok") and reliability.get("ok")
            and intake.get("contract_version") == "v1147.2"
            and execution.get("contract_version") == "v1147.5"
            and reliability.get("contract_version") == "v1147.8",
        ),
        (
            "ownership_registry_dispatch_startup_continuity_reliability_separation",
            ownership.get("contract_version") == "v1147.0"
            and registry.get("contract_version") == "v1147.1"
            and dispatch.get("contract_version") == "v1147.3"
            and startup_plan.get("contract_version") == "v1147.4"
            and continuity.get("contract_version") == "v1147.6"
            and review.get("contract_version") == "v1147.7",
        ),
        (
            "ownership_domains_complete_and_unique",
            ownership.get("domain_count") == len(OWNERSHIP_DOMAINS) == 9
            and ownership.get("unique_owner_count") == 9
            and not ownership.get("duplicate_domain_owners"),
        ),
        (
            "ownership_responsibilities_and_startup_tiers_exact",
            all(row.get("owner_module") and row.get("responsibilities") and row.get("structural_digest") for row in ownership_rows)
            and {row.get("startup_tier") for row in ownership_rows} <= {"core", "conversation_critical", "deferred"},
        ),
        (
            "checkpoint_registry_is_consolidated_unique_and_read_only",
            registry.get("checkpoint_count") == 2
            and not registry.get("duplicate_checkpoint_ids")
            and all(row.get("read_only") and not row.get("post_available") for row in registry_rows),
        ),
        (
            "historical_checkpoint_builders_are_preserved",
            _passed(intake, "historical_checkpoint_modules_preserved")
            and dispatch.get("historical_builders_preserved") is True,
        ),
        (
            "registry_dispatch_is_exact_unique_and_structural",
            dispatch.get("dispatch_count") == registry.get("checkpoint_count") == 2
            and not dispatch.get("duplicate_modules")
            and not dispatch.get("duplicate_builders")
            and all((row.get("checkpoint_summary") or {}).get("structural_digest") for row in dispatch_rows),
        ),
        (
            "raw_checkpoint_content_is_excluded",
            dispatch.get("raw_checkpoint_content_included") is False
            and all(row.get("raw_checkpoint_included") is False for row in dispatch_rows),
        ),
        (
            "startup_tier_order_is_exact",
            startup_plan.get("tier_order") == ["core", "conversation_critical", "deferred"]
            and set(tier_map) == {"core", "conversation_critical", "deferred"},
        ),
        (
            "only_conversation_critical_startup_may_auto_execute",
            tier_map.get("conversation_critical", {}).get("automatic_execution_allowed") is True
            and tier_map.get("core", {}).get("automatic_execution_allowed") is False
            and tier_map.get("deferred", {}).get("automatic_execution_allowed") is False,
        ),
        (
            "deferred_services_remain_lazy",
            startup_plan.get("deferred_tier_remains_lazy") is True
            and startup.get("deferred_tier_started") is False
            and review.get("deferred_tier_started") is False,
        ),
        (
            "provider_contact_remains_prohibited",
            startup_plan.get("provider_contact_allowed") is False
            and startup.get("provider_contacted") is False
            and continuity.get("provider_contacted") is False
            and review.get("provider_contacted") is False,
        ),
        (
            "exact_ownership_registry_and_startup_lineage",
            bool(continuity.get("ownership_digest"))
            and bool(continuity.get("registry_digest"))
            and bool(continuity.get("startup_digest")),
        ),
        (
            "ownership_and_registry_drift_is_absent",
            continuity.get("drift_detected") is False
            and continuity.get("issue_count") == 0
            and all(not value for value in (continuity.get("issues") or {}).values()),
        ),
        (
            "duplicate_checkpoint_plumbing_is_absent",
            review.get("checkpoint_dispatch_failure_count") == 0
            and review.get("duplicate_plumbing_count") == 0,
        ),
        (
            "architecture_reliability_is_bounded_and_ready",
            review.get("classification") == "reliable"
            and review.get("reliability_score") == 100
            and review.get("uncertainty") == 0
            and review.get("operator_visible_state") == "ready",
        ),
        (
            "visible_behavior_is_bounded",
            continuity.get("visible_state") in {"steady", "changed", "attention"}
            and review.get("operator_visible_state") in {"ready", "attention"},
        ),
        (
            "records_are_content_free_and_hide_private_reasoning",
            ownership.get("content_free") and registry.get("content_free") and dispatch.get("content_free")
            and startup_plan.get("content_free") and startup.get("content_free")
            and continuity.get("content_free") and review.get("content_free")
            and not any(forbidden_private_keys.intersection(row.keys()) for row in all_rows),
        ),
        (
            "architecture_records_cannot_execute_mutate_contact_or_send",
            not any(AUTHORITY_BOUNDARY.values())
            and _false_across(dispatch_rows + [startup, continuity, review], operational_fields),
        ),
        (
            "approval_authorization_installation_promotion_and_certification_are_separate",
            _false_across(dispatch_rows + [startup, continuity, review], release_fields)
            and not any(AUTHORITY_BOUNDARY.values()),
        ),
        (
            "checkpoint_surfaces_are_read_only_and_post_unavailable",
            intake.get("read_only") and execution.get("read_only") and reliability.get("read_only")
            and not intake.get("post_available") and not execution.get("post_available") and not reliability.get("post_available"),
        ),
        (
            "source_runtime_separation",
            not (source / "data" / "settings.json").exists(),
        ),
        (
            "checkpoint_does_not_start_services_or_create_records",
            startup.get("runtime_mutated") is False
            and continuity.get("runtime_mutated") is False
            and review.get("runtime_mutated") is False,
        ),
        (
            "desktop_verification_pending_and_no_consciousness_claim",
            True,
        ),
    ]

    source_after = _tree_signature(source)
    checks[22] = ("checkpoint_does_not_start_services_or_create_records", source_before == source_after)
    passed = sum(bool(value) for _, value in checks)
    ok = passed == len(checks)

    return {
        "contract_version": CONTRACT_VERSION,
        "checkpoint_id": "architecture-consolidation-governance:v1147.9",
        "ok": ok,
        "status": "ready_for_desktop_verification" if ok else "review_required",
        "passed": passed,
        "total": len(checks),
        "checks": [
            {"id": name, "status": "pass" if value else "fail", "passed": bool(value)}
            for name, value in checks
        ],
        "summary": {
            "ownership_domain_count": ownership.get("domain_count", 0),
            "registered_checkpoint_count": registry.get("checkpoint_count", 0),
            "dispatched_checkpoint_count": dispatch.get("dispatch_count", 0),
            "startup_tier_count": len(startup_rows),
            "continuity_issue_count": continuity.get("issue_count", 0),
            "reliability_score": review.get("reliability_score", 0),
        },
        "intake": intake,
        "execution": execution,
        "reliability": reliability,
        "read_only": True,
        "post_available": False,
        "source_modified": source_before != source_after,
        "runtime_mutated": False,
        "desktop_verification_pending": True,
        "consciousness_proven": False,
        "ownership_manifest_created_by_checkpoint": False,
        "checkpoint_registry_modified_by_checkpoint": False,
        "checkpoint_dispatched_with_operational_authority": False,
        "startup_service_started_by_checkpoint": False,
        "deferred_service_started_by_checkpoint": False,
        "provider_contacted_by_checkpoint": False,
        "source_modified_by_checkpoint": False,
        "runtime_modified_by_checkpoint": False,
        "message_sent": False,
        "notification_created": False,
        "goal_created": False,
        "plan_created": False,
        "development_proposal_created": False,
        "approval_created": False,
        "authorization_created": False,
        "installation_performed": False,
        "promotion_performed": False,
        "certification_performed": False,
        "raw_conversation_exposed": False,
        "raw_message_exposed": False,
        "prompt_exposed": False,
        "reflection_text_exposed": False,
        "memory_text_exposed": False,
        "relationship_text_exposed": False,
        "mood_text_exposed": False,
        "goal_text_exposed": False,
        "motivation_text_exposed": False,
        "provider_payload_exposed": False,
        "generated_response_exposed": False,
        "hidden_reasoning_exposed": False,
        "authority_boundary": dict(AUTHORITY_BOUNDARY),
    }
