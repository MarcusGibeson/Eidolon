from __future__ import annotations

"""Strictly read-only v1146.9 Understandable Cognitive Controls governance checkpoint."""

import hashlib
import os
from pathlib import Path
from typing import Any, Iterable

from understandable_cognitive_control_definitions import AUTHORITY_BOUNDARY, CONTROL_DOMAINS, SAFE_DEFAULTS
from understandable_cognitive_controls_execution_checkpoint import build_understandable_cognitive_controls_execution_checkpoint
from understandable_cognitive_controls_intake_checkpoint import build_understandable_cognitive_controls_intake_checkpoint
from understandable_cognitive_controls_reliability_checkpoint import build_understandable_cognitive_controls_reliability_checkpoint

CONTRACT_VERSION = "v1146.9"


def _runtime_root() -> Path:
    return (
        Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1] / "data")
        .expanduser()
        .resolve()
        / "cognition"
    )


def _tree_signature(root: Path) -> str:
    digest = hashlib.sha256()
    if not root.exists():
        digest.update(b"missing-tree")
        return digest.hexdigest()
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        if "__pycache__" in path.parts or path.suffix in {".pyc", ".pyo"}:
            continue
        try:
            relative = path.relative_to(root).as_posix()
            payload = path.read_bytes()
        except (OSError, ValueError):
            continue
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(payload)
        digest.update(b"\n")
    return digest.hexdigest()


def _passed(report: dict[str, Any], identifier: str) -> bool:
    return any(
        isinstance(row, dict)
        and (row.get("id") or row.get("name") or row.get("check_id")) == identifier
        and bool(row.get("passed") or row.get("ok") or row.get("status") == "pass")
        for row in report.get("checks") or []
    )


def _authority_inert(component: dict[str, Any]) -> bool:
    return not any(bool(value) for value in (component.get("authority_boundary") or {}).values())


def _false_across(rows: Iterable[dict[str, Any]], fields: Iterable[str]) -> bool:
    return all(not bool(row.get(field)) for row in rows for field in fields)


def build_understandable_cognitive_controls_governance_checkpoint(
    runtime_root: str | Path | None = None,
    *,
    source_root: str | Path | None = None,
) -> dict[str, Any]:
    runtime = Path(runtime_root).expanduser().resolve() if runtime_root is not None else _runtime_root()
    source = Path(source_root).expanduser().resolve() if source_root is not None else Path(__file__).resolve().parents[1]
    runtime_before = _tree_signature(runtime)
    source_before = _tree_signature(source)

    intake = build_understandable_cognitive_controls_intake_checkpoint(runtime, source_root=source)
    execution = build_understandable_cognitive_controls_execution_checkpoint(runtime, source_root=source)
    reliability = build_understandable_cognitive_controls_reliability_checkpoint(runtime, source_root=source)

    definitions = intake.get("definitions") or {}
    configuration = intake.get("configuration_inspection") or {}
    activation = execution.get("activation_inspection") or {}
    enforcement = execution.get("enforcement_inspection") or {}
    continuity = reliability.get("continuity_inspection") or {}
    reviews = reliability.get("reliability_inspection") or {}
    components = (definitions, configuration, activation, enforcement, continuity, reviews)

    definition_rows = definitions.get("definitions") or []
    configuration_rows = configuration.get("recent_records") or []
    active_rows = list((activation.get("active_controls") or {}).values())
    activation_rows = activation.get("recent_receipts") or []
    enforcement_rows = enforcement.get("recent_receipts") or []
    continuity_rows = continuity.get("recent_records") or []
    review_rows = reviews.get("recent_reviews") or []
    all_rows = definition_rows + configuration_rows + active_rows + activation_rows + enforcement_rows + continuity_rows + review_rows

    forbidden_private_keys = {
        "text", "content", "prompt", "message", "reasoning", "memory", "relationship",
        "mood", "goal", "motivation", "patch", "source_code", "provider_payload",
        "generated_response", "hidden_reasoning",
    }
    operational_fields = (
        "execution_performed", "cognition_mutated", "provider_contacted", "message_sent",
        "notification_created", "proposal_created", "goal_created", "plan_created",
    )
    release_fields = (
        "approval_created", "authorization_created", "installation_performed",
        "promotion_performed", "certification_performed",
    )

    checks = [
        (
            "understandable_cognitive_controls_arc_lineage",
            intake.get("ok") and execution.get("ok") and reliability.get("ok")
            and intake.get("contract_version") == "v1146.2"
            and execution.get("contract_version") == "v1146.5"
            and reliability.get("contract_version") == "v1146.8",
        ),
        (
            "definition_configuration_activation_enforcement_continuity_reliability_separation",
            definitions.get("contract_version") == "v1146.0"
            and configuration.get("contract_version") == "v1146.1"
            and activation.get("contract_version") == "v1146.3"
            and enforcement.get("contract_version") == "v1146.4"
            and continuity.get("contract_version") == "v1146.6"
            and reviews.get("contract_version") == "v1146.7",
        ),
        (
            "complete_control_domains_and_safe_defaults",
            tuple(definitions.get("control_domains") or []) == CONTROL_DOMAINS
            and set((definitions.get("safe_defaults") or {}).keys()) == set(CONTROL_DOMAINS)
            and set(SAFE_DEFAULTS.keys()) == set(CONTROL_DOMAINS),
        ),
        (
            "exact_owner_scope_mode_and_digest_definitions",
            len(definition_rows) == len(CONTROL_DOMAINS)
            and all(row.get("owner") and row.get("scope") and row.get("allowed_modes") and row.get("structural_digest") for row in definition_rows),
        ),
        (
            "preview_lineage_is_exact_bounded_and_not_active",
            _passed(intake, "durable_exact_lineage")
            and _passed(intake, "prior_lineage_visible")
            and _passed(intake, "configuration_not_applied")
            and all(row.get("configuration_id") and row.get("structural_digest") for row in configuration_rows),
        ),
        (
            "activation_requires_exact_preview_and_confirmation",
            _passed(execution, "exact_preview_binding")
            and _passed(execution, "explicit_confirmation")
            and activation.get("confirmation_required") is True,
        ),
        (
            "activation_restart_rollback_and_prior_lineage",
            _passed(execution, "restart_continuity")
            and _passed(execution, "rollback_supported")
            and _passed(execution, "prior_activation_lineage")
            and activation.get("restart_continuity") is True
            and activation.get("rollback_supported") is True,
        ),
        (
            "enforcement_provenance_and_decisions_are_bounded",
            _passed(execution, "safe_default_fallback")
            and _passed(execution, "bounded_decisions")
            and _passed(execution, "exact_activation_lineage")
            and all(row.get("control_source") in {"active", "safe_default"} and row.get("decision") in {"allow", "constrain", "deny"} for row in enforcement_rows),
        ),
        (
            "attention_and_thought_activity_controls_remain_bounded",
            SAFE_DEFAULTS["attention"]["mode"] == "bounded"
            and SAFE_DEFAULTS["thought_activity"]["mode"] == "bounded"
            and all(0.0 <= float(row.get("effective_intensity", 0.0)) <= 1.0 for row in enforcement_rows),
        ),
        (
            "initiative_and_development_proposal_controls_remain_restrained",
            SAFE_DEFAULTS["initiative"]["mode"] == "suggest_only"
            and SAFE_DEFAULTS["development_proposals"]["mode"] == "disabled"
            and all(not row.get("proposal_created") for row in activation_rows + enforcement_rows + continuity_rows + review_rows),
        ),
        (
            "privacy_and_disclosure_boundaries_remain_strict",
            SAFE_DEFAULTS["privacy"]["mode"] == "strict"
            and _passed(intake, "privacy_boundary")
            and not any(forbidden_private_keys.intersection(row.keys()) for row in all_rows),
        ),
        (
            "resource_use_constraints_remain_conservative",
            SAFE_DEFAULTS["resource_use"]["mode"] == "conservative"
            and all(0.0 <= float(row.get("resource_cost", 0.0)) <= 1.0 for row in enforcement_rows),
        ),
        (
            "stale_conflict_drift_correction_and_safe_default_recovery_visible",
            _passed(reliability, "stale_detection")
            and _passed(reliability, "conflict_detection")
            and _passed(reliability, "drift_detection")
            and _passed(reliability, "operator_correction_lineage")
            and _passed(reliability, "safe_default_recovery"),
        ),
        (
            "reliability_scores_states_and_visible_behavior_are_bounded",
            _passed(reliability, "reliability_bounded")
            and _passed(reliability, "review_state_bounded")
            and _passed(reliability, "visible_behavior_bounded"),
        ),
        (
            "duplicate_retry_restart_and_cross_cycle_lineage_remain_structural",
            _passed(execution, "deterministic_idempotency")
            and all(row.get("cycle_id") and row.get("structural_digest") for row in continuity_rows)
            and all(row.get("review_id") and row.get("structural_digest") for row in review_rows),
        ),
        (
            "records_are_content_free_and_hide_private_reasoning",
            all(component.get("content_free", True) for component in components)
            and not any(forbidden_private_keys.intersection(row.keys()) for row in all_rows),
        ),
        (
            "control_records_cannot_execute_contact_send_or_create",
            _false_across(activation_rows + enforcement_rows + continuity_rows + review_rows, operational_fields),
        ),
        (
            "cognition_memory_relationship_mood_goal_motivation_and_attention_mutation_separated",
            _passed(execution, "no_cognition_mutation")
            and _passed(reliability, "no_cognition_mutation")
            and all(not row.get("cognition_mutated") for row in activation_rows + enforcement_rows + continuity_rows + review_rows),
        ),
        (
            "approval_authorization_installation_promotion_and_certification_separated",
            _false_across(activation_rows + enforcement_rows + continuity_rows + review_rows, release_fields)
            and all(_authority_inert(component) for component in components)
            and all(value is False for value in AUTHORITY_BOUNDARY.values()),
        ),
        (
            "checkpoint_does_not_create_or_apply_control_records",
            True,
        ),
        (
            "checkpoint_surfaces_are_read_only_and_post_unavailable",
            intake.get("read_only") and execution.get("read_only") and reliability.get("read_only")
            and not intake.get("post_available") and not execution.get("post_available") and not reliability.get("post_available"),
        ),
        (
            "source_runtime_separation",
            str(runtime) != str(source) and source not in runtime.parents and runtime not in source.parents,
        ),
        (
            "source_is_read_only",
            True,
        ),
        (
            "desktop_verification_pending_and_no_consciousness_claim",
            True,
        ),
    ]

    runtime_after = _tree_signature(runtime)
    source_after = _tree_signature(source)
    checks[19] = ("checkpoint_does_not_create_or_apply_control_records", runtime_before == runtime_after)
    checks[22] = ("source_is_read_only", source_before == source_after)
    passed = sum(bool(value) for _, value in checks)
    ok = passed == len(checks)

    summary = {
        "control_domain_count": len(definition_rows),
        "configuration_preview_count": configuration.get("record_count", 0),
        "active_control_count": activation.get("active_control_count", 0),
        "activation_receipt_count": len(activation_rows),
        "enforcement_receipt_count": enforcement.get("receipt_count", 0),
        "continuity_record_count": continuity.get("record_count", 0),
        "reliability_review_count": reviews.get("review_count", 0),
        "review_required_count": reviews.get("review_required_count", 0),
    }
    return {
        "contract_version": CONTRACT_VERSION,
        "ok": ok,
        "status": "ready_for_desktop_verification" if ok else "review_required",
        "passed": passed,
        "total": len(checks),
        "checks": [{"id": name, "status": "pass" if value else "fail", "passed": bool(value)} for name, value in checks],
        "summary": summary,
        "intake": intake,
        "execution": execution,
        "reliability": reliability,
        "read_only": True,
        "post_available": False,
        "runtime_mutated": runtime_before != runtime_after,
        "source_modified": source_before != source_after,
        "desktop_verification_pending": True,
        "consciousness_proven": False,
        "control_definition_created_by_checkpoint": False,
        "configuration_preview_created_by_checkpoint": False,
        "control_activation_performed_by_checkpoint": False,
        "control_rollback_performed_by_checkpoint": False,
        "control_enforcement_performed_by_checkpoint": False,
        "continuity_record_created_by_checkpoint": False,
        "reliability_review_created_by_checkpoint": False,
        "cognition_started_by_checkpoint": False,
        "provider_contacted_by_checkpoint": False,
        "message_sent": False,
        "notification_created": False,
        "goal_created": False,
        "plan_created": False,
        "development_proposal_created": False,
        "cognition_mutated": False,
        "memory_mutated": False,
        "relationship_mutated": False,
        "mood_mutated": False,
        "goal_mutated": False,
        "motivation_mutated": False,
        "attention_mutated": False,
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
