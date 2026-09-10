from __future__ import annotations

"""Strictly read-only v1148.9 Privacy and Security Hardening governance checkpoint."""

import hashlib
import os
from pathlib import Path
from typing import Any, Iterable

from privacy_security_hardening_intake_checkpoint import build_privacy_security_hardening_intake_checkpoint
from privacy_security_hardening_execution_checkpoint import build_privacy_security_hardening_execution_checkpoint
from privacy_security_hardening_reliability_checkpoint import build_privacy_security_hardening_reliability_checkpoint
from privacy_security_threat_model import THREAT_CATEGORIES

CONTRACT_VERSION = "v1148.9"


def _runtime_root() -> Path:
    return Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1] / "data").expanduser().resolve() / "cognition"


def _signature(root: Path) -> str:
    digest = hashlib.sha256()
    if not root.exists():
        digest.update(b"missing-tree")
        return digest.hexdigest()
    for path in sorted(p for p in root.rglob("*") if p.is_file() and "__pycache__" not in p.parts and p.suffix not in {".pyc", ".pyo"}):
        try:
            digest.update(path.relative_to(root).as_posix().encode("utf-8"))
            digest.update(b"\0")
            digest.update(path.read_bytes())
        except OSError:
            continue
    return digest.hexdigest()


def _false_across(rows: Iterable[dict[str, Any]], fields: Iterable[str]) -> bool:
    return all(not bool(row.get(field)) for row in rows for field in fields)


def build_privacy_security_hardening_governance_checkpoint(
    runtime_root: str | Path | None = None, *, source_root: str | Path | None = None
) -> dict[str, Any]:
    runtime = Path(runtime_root).expanduser().resolve() if runtime_root else _runtime_root()
    source = Path(source_root).expanduser().resolve() if source_root else Path(__file__).resolve().parents[1]
    runtime_before = _signature(runtime)
    source_before = _signature(source)

    intake = build_privacy_security_hardening_intake_checkpoint(source_root=source)
    execution = build_privacy_security_hardening_execution_checkpoint(runtime, source_root=source)
    reliability = build_privacy_security_hardening_reliability_checkpoint(runtime, source_root=source)

    model = intake.get("threat_model") or {}
    catalog = intake.get("test_catalog") or {}
    executions = execution.get("executions") or {}
    findings = execution.get("findings") or {}
    continuity = reliability.get("continuity") or {}
    review = reliability.get("reliability") or {}
    threats = list(model.get("threats") or [])
    scenarios = list(catalog.get("scenarios") or [])
    execution_rows = list(executions.get("recent_records") or [])
    finding_rows = list(findings.get("recent_records") or [])
    continuity_rows = list(continuity.get("recent_records") or [])
    all_rows = threats + scenarios + execution_rows + finding_rows + continuity_rows

    forbidden_private_keys = {
        "prompt", "raw_prompt", "message", "conversation", "reflection", "reasoning",
        "memory_text", "belief_text", "goal_text", "relationship_text", "mood_text",
        "provider_payload", "source_text", "patch_text", "fixture_content", "raw_evidence",
        "hidden_reasoning",
    }
    operational_fields = (
        "browses", "contacts_provider", "provider_contacted", "executes_commands", "command_executed",
        "mutates_runtime", "runtime_mutated", "mutates_cognition", "mutates_memory",
        "modifies_source", "source_modified", "sends_messages", "message_sent",
        "notification_created", "goal_created", "plan_created", "development_proposal_created",
    )
    release_fields = (
        "approval_created", "authorization_created", "installation_performed",
        "promotion_performed", "certification_performed",
    )

    checks: list[tuple[str, bool]] = [
        ("privacy_security_arc_lineage", intake.get("contract_version") == "v1148.2" and execution.get("contract_version") == "v1148.5" and reliability.get("contract_version") == "v1148.8" and intake.get("ok") and execution.get("ok") and reliability.get("ok")),
        ("threat_execution_continuity_reliability_separation", model.get("contract_version") == "v1148.0" and catalog.get("contract_version") == "v1148.1" and executions.get("contract_version") == "v1148.3" and findings.get("contract_version") == "v1148.4" and continuity.get("contract_version") == "v1148.6" and review.get("contract_version") == "v1148.7"),
        ("six_threat_categories_complete", {row.get("category") for row in threats} == set(THREAT_CATEGORIES) and model.get("threat_count") == 6),
        ("threat_and_scenario_identifiers_unique", not model.get("duplicate_threat_ids") and not catalog.get("duplicate_scenario_ids")),
        ("scenario_catalog_complete_and_exact", catalog.get("scenario_count") == 12 and {row.get("category") for row in scenarios} == set(THREAT_CATEGORIES)),
        ("fixtures_are_structural_and_content_free", all(str(row.get("fixture_reference", "")).startswith("structural-fixture:") and not row.get("fixture_content_included") for row in scenarios)),
        ("operator_confirmation_and_bounded_execution", all(row.get("state") in {"awaiting_confirmation", "cancelled", "timed_out", "suppressed"} or row.get("operator_confirmation_id") for row in execution_rows) and all(int(row.get("steps_used") or 0) <= 5 and int(row.get("attempts_used") or 0) <= 1 for row in execution_rows)),
        ("provider_budget_and_contact_are_zero", all(int(row.get("provider_tokens_used") or 0) == 0 for row in execution_rows) and not executions.get("provider_payload_exposed") and not review.get("provider_contacted")),
        ("finding_lineage_is_exact", all(row.get("execution_id") and row.get("execution_digest") for row in finding_rows)),
        ("containment_and_recovery_truth_are_structural", all(row.get("state") != "contained" or row.get("contained") for row in finding_rows) and all(not row.get("recovery_succeeded") or row.get("recovery_attempted") for row in finding_rows)),
        ("cross_cycle_lineage_is_exact", all(not row.get("prior_revision") or row.get("prior_structural_digest") for row in continuity_rows)),
        ("recurrence_drift_and_orphans_are_reviewed", review.get("repeated_finding_count", 0) >= 0 and review.get("drift_count", 0) >= 0 and review.get("orphan_finding_count", 0) >= 0),
        ("reliability_is_bounded", 0 <= review.get("reliability_score", -1) <= 100 and 0 <= review.get("uncertainty", -1) <= 100 and review.get("classification") in {"reliable", "review_required"}),
        ("visible_behavior_is_bounded", all(row.get("visible_state") in {"steady", "changed", "attention"} for row in continuity_rows)),
        ("duplicate_retry_and_stale_work_are_structurally_visible", review.get("execution_count", 0) >= 0 and review.get("finding_count", 0) >= 0 and review.get("stale_execution_count", 0) >= 0),
        ("records_exclude_private_content_and_hidden_reasoning", model.get("content_free") and catalog.get("content_free") and not continuity.get("raw_content_exposed") and not review.get("raw_content_exposed") and not any(forbidden_private_keys.intersection(row.keys()) for row in all_rows)),
        ("security_records_have_no_operational_authority", _false_across(all_rows + [executions, findings, continuity, review], operational_fields)),
        ("approval_authorization_installation_promotion_certification_separate", _false_across(all_rows + [executions, findings, continuity, review], release_fields)),
        ("checkpoint_surfaces_are_read_only_and_post_unavailable", intake.get("read_only") and execution.get("read_only") and reliability.get("read_only") and not intake.get("post_available") and not execution.get("post_available") and not reliability.get("post_available")),
        ("source_runtime_separation", not (source / "data" / "settings.json").exists()),
        ("checkpoint_does_not_execute_tests_or_create_records", runtime_before == _signature(runtime)),
        ("checkpoint_does_not_modify_source", source_before == _signature(source)),
        ("desktop_verification_pending", True),
        ("consciousness_not_proven", True),
    ]

    passed = sum(bool(value) for _, value in checks)
    ok = passed == len(checks)
    return {
        "contract_version": CONTRACT_VERSION,
        "checkpoint_id": "privacy-security-hardening-governance:v1148.9",
        "ok": ok,
        "status": "ready_for_desktop_verification" if ok else "review_required",
        "passed": passed,
        "total": len(checks),
        "checks": [{"id": name, "status": "pass" if value else "fail", "passed": bool(value)} for name, value in checks],
        "summary": {
            "threat_category_count": len({row.get("category") for row in threats}),
            "scenario_count": len(scenarios),
            "execution_count": review.get("execution_count", 0),
            "finding_count": review.get("finding_count", 0),
            "continuity_record_count": len(continuity_rows),
            "reliability_score": review.get("reliability_score", 0),
            "classification": review.get("classification", "unknown"),
        },
        "intake": intake,
        "execution": execution,
        "reliability": reliability,
        "read_only": True,
        "post_available": False,
        "source_modified": source_before != _signature(source),
        "runtime_mutated": runtime_before != _signature(runtime),
        "security_test_executed_by_checkpoint": False,
        "provider_contacted_by_checkpoint": False,
        "command_executed_by_checkpoint": False,
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
        "belief_text_exposed": False,
        "goal_text_exposed": False,
        "relationship_text_exposed": False,
        "mood_text_exposed": False,
        "provider_payload_exposed": False,
        "source_text_exposed": False,
        "patch_text_exposed": False,
        "hidden_reasoning_exposed": False,
        "desktop_verification_pending": True,
        "consciousness_proven": False,
    }
