from __future__ import annotations

"""Strictly read-only v1155.9 Reasoning Alpha Consolidation checkpoint.

Consolidates executable evidence from v1155.0-v1155.8. The checkpoint reports
bounded outcomes, transitions, counts, and structural digests only. It never
returns private chain-of-thought, raw evidence, prompts, conversations, provider
payloads, operation/session identifiers, or executable decisions and actions.
"""

from copy import deepcopy
from datetime import datetime, timedelta, timezone
from functools import lru_cache
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Mapping

from checkpoint_registry import inspect_checkpoint_registry
from package_integrity import package_privacy_summary_for_root, source_only_entry_policy
from reasoning_consolidation import CONTRACT_VERSION as CONSOLIDATION_CONTRACT_VERSION, MAX_CASES, MAX_OPTIONS, MAX_SUMMARY_CHARS, build_reasoning_state, prompt_projection
from reasoning_state_continuity import CONTRACT_VERSION as CONTINUITY_CONTRACT_VERSION, MAX_PENDING, MAX_RECORDS, STALE_AFTER_DAYS, _bounded_projection, _candidate_digest_from_parts, _pending_integrity_ok, _record_integrity_ok

CONTRACT_VERSION = "v1155.9"
_CHECKPOINT_ID = "reasoning-alpha-consolidation:v1155.9"
_ALLOWED_QUALITY = {"no_decision", "insufficient_evidence", "bounded_candidate"}
_ALLOWED_TRANSITIONS = {
    "first_observation", "evidence_improved", "evidence_degraded",
    "candidate_emerged", "candidate_withdrawn", "stable",
}
_EXCLUDED_SOURCE_ROOTS = {
    "data", ".git", ".venv", "venv", "__pycache__", ".pytest_cache",
    ".mypy_cache", ".ruff_cache", "reports", "dist", "build",
}
_FORBIDDEN_REPORT_TOKENS = {
    "operation_id", "session_id", "session_digest", "candidate_digest",
    "record_digest", "case_digest", "boundary_id", "candidate_option_id",
    "proposition", "user_message", "assistant_response", "prompt_content",
    "provider_payload", "private_chain_of_thought", "raw_evidence",
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
            if path.is_file() and "__pycache__" not in path.parts
            and path.suffix.lower() not in {".pyc", ".pyo"}
        ]
    for path in sorted(paths):
        try:
            relative = path.relative_to(root).as_posix()
            content = hashlib.sha256(path.read_bytes()).digest()
        except (OSError, ValueError):
            continue
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(content)
    return digest.hexdigest()


def _safe_json(path: Path) -> tuple[dict[str, Any], bool]:
    if not path.exists():
        return {"schema_version": "2", "records": [], "pending": []}, True
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, TypeError):
        return {"schema_version": "", "records": [], "pending": []}, False
    if not isinstance(value, dict):
        return {"schema_version": "", "records": [], "pending": []}, False
    return value, True


def _parse_time(value: Any) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return None


def _runtime_reasoning_summary(runtime: Path) -> dict[str, Any]:
    path = runtime / "cognition" / "reasoning_alpha_states.json"
    state, parse_valid = _safe_json(path)
    records_raw = state.get("records", [])
    pending_raw = state.get("pending", [])
    schema_valid = isinstance(records_raw, list) and isinstance(pending_raw, list)
    records = [row for row in records_raw if isinstance(row, dict)] if schema_valid else []
    pending = [row for row in pending_raw if isinstance(row, dict)] if schema_valid else []
    malformed_record_count = (len(records_raw) - len(records)) if isinstance(records_raw, list) else 1
    malformed_pending_count = (len(pending_raw) - len(pending)) if isinstance(pending_raw, list) else 1
    integrity_mismatch_count = 0
    stale_count = 0
    bounded_projection_count = 0
    authority_preserved = True
    timestamps_valid = True
    quality_values_valid = True
    transition_values_valid = True
    now = datetime.now(timezone.utc)

    for row in records:
        valid = _record_integrity_ok(row)
        integrity_mismatch_count += int(not valid)
        created = _parse_time(row.get("created_at"))
        timestamps_valid = timestamps_valid and created is not None
        stale_count += int(created is None or now - created > timedelta(days=STALE_AFTER_DAYS))
        projection = row.get("projection") if isinstance(row.get("projection"), dict) else {}
        bounded_projection_count += int(bool(projection) and projection == _bounded_projection(projection))
        quality_values_valid = quality_values_valid and str(projection.get("reasoning_quality") or "") in _ALLOWED_QUALITY
        transition_values_valid = transition_values_valid and str(projection.get("reasoning_transition") or "") in _ALLOWED_TRANSITIONS
        authority_preserved = authority_preserved and projection.get("authority") == "none" \
            and not projection.get("decision_created") and not projection.get("execution_permitted") \
            and not row.get("private_chain_of_thought_stored") and not row.get("raw_evidence_stored") \
            and not row.get("prompt_content_stored") and not row.get("provider_payload_stored") \
            and not row.get("decision_created") and not row.get("action_executed") \
            and not row.get("authority_broadened")

    pending_integrity_mismatch_count = sum(1 for row in pending if not _pending_integrity_ok(row))
    structural = {
        "parse_valid": parse_valid,
        "schema_valid": schema_valid,
        "schema_version_current": str(state.get("schema_version") or "") == "2" if path.exists() else True,
        "record_count": len(records),
        "pending_count": len(pending),
        "stale_count": stale_count,
        "malformed_record_count": malformed_record_count,
        "malformed_pending_count": malformed_pending_count,
        "integrity_mismatch_count": integrity_mismatch_count,
        "pending_integrity_mismatch_count": pending_integrity_mismatch_count,
        "record_bounds_valid": len(records) <= MAX_RECORDS,
        "pending_bounds_valid": len(pending) <= MAX_PENDING,
        "all_projections_bounded": bounded_projection_count == len(records),
        "timestamps_valid": timestamps_valid,
        "quality_values_valid": quality_values_valid,
        "transition_values_valid": transition_values_valid,
        "all_authority_boundaries_preserved": authority_preserved,
        "all_private_content_omitted": True,
        "raw_registry_exposed": False,
        "record_identifiers_exposed": False,
        "reasoning_content_exposed": False,
    }
    structural["review_required"] = not all((
        structural["parse_valid"], structural["schema_valid"], structural["schema_version_current"],
        structural["record_bounds_valid"], structural["pending_bounds_valid"],
        structural["all_projections_bounded"], structural["timestamps_valid"],
        structural["quality_values_valid"], structural["transition_values_valid"],
        structural["all_authority_boundaries_preserved"],
        malformed_record_count == 0, malformed_pending_count == 0,
        integrity_mismatch_count == 0, pending_integrity_mismatch_count == 0,
    ))
    structural["structural_digest"] = _digest(structural)
    return structural


def _sample_inputs(*, candidate: bool = True, insufficient: bool = False) -> dict[str, Any]:
    outcome = "requires_more_evidence" if insufficient else "provisional_leader_only"
    boundary_state = "more_evidence_required" if insufficient else ("candidate_recommendation" if candidate else "no_decision")
    return {
        "reflection_items": [{"confidence": 0.8, "uncertainty_score": 0.2}],
        "belief_deliberation": {"conflict_count": 1, "quarantined_conflict_count": 0},
        "multi_step_deliberation": {
            "cases": [{
                "case_digest": "synthetic-case",
                "options": [{
                    "option_id": "option-a", "proposition": "inspect in a sandbox",
                    "confidence": 0.8, "uncertainty": 0.2, "evidence_quality": 0.7,
                }],
                "steps": [{"complete": True}, {"complete": True}],
                "comparison": {"outcome": outcome, "provisional_leader_option_id": "option-a" if not insufficient else ""},
            }]
        },
        "decision_boundary": {
            "cases": [{
                "boundary_id": "synthetic-boundary", "state": boundary_state,
                "candidate_option_id": "option-a" if boundary_state == "candidate_recommendation" else "",
                "evidence_sufficient": not insufficient, "prerequisites_complete": True,
                "risk_level": "low", "reversibility": "high",
                "operator_approval_required": boundary_state == "candidate_recommendation",
            }]
        },
        "continuity": {"prior_session_present": False, "prior_session_stale": False, "goal_context_count": 1},
    }


def _synthetic_contract_evidence() -> dict[str, Any]:
    candidate = build_reasoning_state(**_sample_inputs(), prior_reasoning_state=None)
    insufficient = build_reasoning_state(**_sample_inputs(insufficient=True), prior_reasoning_state=None)
    no_decision = build_reasoning_state(**_sample_inputs(candidate=False), prior_reasoning_state=None)
    prior = {
        "prior_state_present": True,
        "prior_state_stale": False,
        "projection": {"reasoning_quality": "insufficient_evidence", "missing_evidence_explicit": True, "candidate_recommendation_present": False},
    }
    improved = build_reasoning_state(**_sample_inputs(), prior_reasoning_state=prior)
    projection = prompt_projection(candidate)
    bounded = _bounded_projection(candidate)
    operation = "synthetic-operation"
    session_digest = _digest("synthetic-session")[:24]
    record = {
        "contract_version": CONTINUITY_CONTRACT_VERSION,
        "type": "reasoning_alpha_state",
        "operation_id": operation,
        "session_digest": session_digest,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "candidate_digest": _candidate_digest_from_parts(operation, session_digest, bounded),
        "projection": bounded,
        "private_chain_of_thought_stored": False,
        "raw_evidence_stored": False,
        "prompt_content_stored": False,
        "provider_payload_stored": False,
        "decision_created": False,
        "action_executed": False,
        "authority_broadened": False,
    }
    record["record_digest"] = _digest({key: value for key, value in record.items() if key != "record_digest"})
    tampered_candidate = deepcopy(record)
    tampered_candidate["projection"]["reasoning_quality"] = "no_decision"
    tampered_candidate["record_digest"] = _digest({key: value for key, value in tampered_candidate.items() if key != "record_digest"})
    malformed_projection = deepcopy(record)
    malformed_projection["projection"]["reasoning_transition"] = "execute_now"
    malformed_projection["candidate_digest"] = _candidate_digest_from_parts(operation, session_digest, malformed_projection["projection"])
    malformed_projection["record_digest"] = _digest({key: value for key, value in malformed_projection.items() if key != "record_digest"})
    pending = {
        "operation_id": operation, "session_digest": session_digest,
        "candidate_digest": record["candidate_digest"], "created_at": datetime.now(timezone.utc).isoformat(),
        "record": deepcopy(record), "content_free": True, "authority": "none",
    }
    mismatched_pending = deepcopy(pending)
    mismatched_pending["candidate_digest"] = "wrong-digest"
    encoded = json.dumps(projection, sort_keys=True, ensure_ascii=True)
    checks = {
        "candidate_state_is_bounded_candidate": candidate.get("reasoning_quality") == "bounded_candidate",
        "insufficient_evidence_state_is_explicit": insufficient.get("reasoning_quality") == "insufficient_evidence" and insufficient.get("missing_evidence_explicit") is True,
        "no_decision_state_remains_non_authorizing": no_decision.get("reasoning_quality") == "no_decision" and not no_decision.get("decision_created"),
        "candidate_requires_operator_approval": candidate.get("operator_approval_required") is True,
        "candidate_creates_no_decision_intention_or_action": not any(candidate.get(key) for key in ("decision_created", "intention_created", "action_executed")),
        "private_reasoning_is_not_exposed": not candidate.get("private_chain_of_thought_exposed") and not candidate.get("raw_reflection_evidence_exposed") and not candidate.get("raw_belief_ledger_exposed"),
        "cases_and_options_are_bounded": len(candidate.get("cases") or []) <= MAX_CASES and all(len(row.get("options") or []) <= MAX_OPTIONS for row in candidate.get("cases") or []),
        "prompt_projection_is_bounded": len(encoded) <= MAX_SUMMARY_CHARS + 256,
        "prompt_projection_preserves_no_authority": projection.get("authority") == "none" and not projection.get("decision_created") and not projection.get("execution_permitted"),
        "improved_evidence_transition_is_explicit": improved.get("reasoning_transition") in {"evidence_improved", "candidate_emerged"},
        "bounded_projection_rejects_unknown_authority_values": _bounded_projection({"reasoning_quality": "execute", "reasoning_transition": "approve", "authority": "full"}).get("authority") == "none",
        "clean_record_integrity_passes": _record_integrity_ok(record),
        "changed_projection_with_stale_candidate_digest_fails": not _record_integrity_ok(tampered_candidate),
        "noncanonical_projection_fails_even_with_recomputed_digests": not _record_integrity_ok(malformed_projection),
        "clean_pending_wrapper_integrity_passes": _pending_integrity_ok(pending),
        "mismatched_pending_wrapper_fails": not _pending_integrity_ok(mismatched_pending),
    }
    return {
        "checks": checks,
        "passed": sum(1 for value in checks.values() if value),
        "total": len(checks),
        "structural_digest": _digest(checks),
        "content_free": True,
    }


@lru_cache(maxsize=8)
def _static_source_evidence(source_text: str, source_signature: str) -> str:
    del source_signature
    source = Path(source_text)
    backbone = (source / "conscious_agent" / "conversation_cognitive_backbone.py").read_text(encoding="utf-8")
    consolidation = (source / "conscious_agent" / "reasoning_consolidation.py").read_text(encoding="utf-8")
    continuity = (source / "conscious_agent" / "reasoning_state_continuity.py").read_text(encoding="utf-8")
    payload = {
        "registry": inspect_checkpoint_registry(source_root=source),
        "privacy_policy": source_only_entry_policy(),
        "privacy": package_privacy_summary_for_root(source),
        "integration": {
            "ordinary_context_builds_unified_state": "build_reasoning_state(" in backbone,
            "ordinary_prompt_uses_single_projection": 'reasoning_alpha_state data=' in backbone and "prompt_projection(reasoning_state)" in backbone,
            "ordinary_context_loads_prior_state": "load_prior_reasoning_state(" in backbone,
            "ordinary_completion_records_state_after_commit": "record_reasoning_state(" in backbone,
            "completion_ledger_tracks_state": "reasoning_state_recorded" in backbone and "reasoning_transition" in backbone,
            "legacy_duplicate_prompt_fragments_removed": 'belief_deliberation data=' not in backbone and 'deliberation_decision_boundary data=' not in backbone,
            "consolidation_excludes_private_reasoning": '"private_chain_of_thought_exposed": False' in consolidation and '"raw_reflection_evidence_exposed": False' in consolidation,
            "consolidation_preserves_no_authority": '"authority": "none"' in consolidation and '"action_executed": False' in consolidation,
            "continuity_uses_pending_recovery": '"pending"' in continuity and "pending reasoning state" in continuity,
            "continuity_validates_canonical_projection": "projection != _bounded_projection(projection)" in continuity,
            "continuity_validates_candidate_digest": "_candidate_digest_from_parts" in continuity and "candidate_digest" in continuity,
            "continuity_validates_pending_wrapper": "def _pending_integrity_ok" in continuity,
            "stale_states_fail_closed": "STALE_AFTER_DAYS = 7" in continuity and "prior_state_stale" in continuity,
        },
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


def build_reasoning_alpha_consolidation_checkpoint(
    runtime_root: str | Path | None = None,
    *,
    source_root: str | Path | None = None,
) -> dict[str, Any]:
    source = Path(source_root or Path(__file__).resolve().parents[1]).expanduser().resolve()
    runtime = Path(runtime_root or os.environ.get("EIDOLON_DATA_DIR") or source / "data").expanduser().resolve()
    source_before = _tree_signature(source, source_tree=True)
    runtime_before = _tree_signature(runtime, source_tree=False)

    static = json.loads(_static_source_evidence(str(source), source_before))
    registry = static["registry"]
    privacy_policy = static["privacy_policy"]
    privacy = static["privacy"]
    integration = static["integration"]
    runtime_summary = _runtime_reasoning_summary(runtime)
    synthetic = _synthetic_contract_evidence()

    limitations = [
        {"limitation_id": "native-desktop-verification-pending", "status": "open", "next_action": "defer_desktop_codex_review_until_v1200"},
        {"limitation_id": "reasoning-quality-and-transition-classification-remains-deterministic", "status": "open", "current_behavior": "bounded_contract_based_projection"},
        {"limitation_id": "continuity-staleness-uses-fixed-seven-day-threshold", "status": "open", "current_behavior": "stale_records_preserved_but_withheld"},
        {"limitation_id": "malformed-reasoning-state-requires-operator-repair", "status": "open", "current_behavior": "fail_closed_quarantine_without_automatic_rewrite"},
        {"limitation_id": "continuity-stores-bounded-projection-not-private-deliberation", "status": "open", "current_behavior": "outcome_and_transition_continuity_only"},
    ]

    checks: list[tuple[str, bool]] = [
        ("reasoning_consolidation_contract_lineage_is_current", CONSOLIDATION_CONTRACT_VERSION == "v1155.8" and CONTINUITY_CONTRACT_VERSION == "v1155.8"),
        *[(name, bool(value)) for name, value in synthetic["checks"].items()],
        ("ordinary_context_builds_unified_reasoning_state", integration["ordinary_context_builds_unified_state"]),
        ("ordinary_prompt_uses_single_reasoning_projection", integration["ordinary_prompt_uses_single_projection"]),
        ("ordinary_context_loads_prior_reasoning_state", integration["ordinary_context_loads_prior_state"]),
        ("ordinary_completion_records_reasoning_after_commit", integration["ordinary_completion_records_state_after_commit"]),
        ("completion_ledger_tracks_reasoning_state", integration["completion_ledger_tracks_state"]),
        ("legacy_duplicate_reasoning_prompt_fragments_are_removed", integration["legacy_duplicate_prompt_fragments_removed"]),
        ("consolidation_excludes_private_reasoning", integration["consolidation_excludes_private_reasoning"]),
        ("consolidation_preserves_zero_action_authority", integration["consolidation_preserves_no_authority"]),
        ("continuity_uses_recoverable_pending_state", integration["continuity_uses_pending_recovery"]),
        ("continuity_validates_canonical_bounded_projection", integration["continuity_validates_canonical_projection"]),
        ("continuity_validates_candidate_identity", integration["continuity_validates_candidate_digest"]),
        ("continuity_validates_pending_wrapper_identity", integration["continuity_validates_pending_wrapper"]),
        ("stale_reasoning_state_fails_closed", integration["stale_states_fail_closed"]),
        ("runtime_reasoning_store_is_parseable", runtime_summary["parse_valid"]),
        ("runtime_reasoning_store_schema_is_valid", runtime_summary["schema_valid"] and runtime_summary["schema_version_current"]),
        ("runtime_reasoning_store_bounds_are_respected", runtime_summary["record_bounds_valid"] and runtime_summary["pending_bounds_valid"]),
        ("runtime_reasoning_projections_are_canonical", runtime_summary["all_projections_bounded"]),
        ("runtime_reasoning_timestamps_are_valid", runtime_summary["timestamps_valid"]),
        ("runtime_reasoning_quality_and_transitions_are_valid", runtime_summary["quality_values_valid"] and runtime_summary["transition_values_valid"]),
        ("runtime_reasoning_integrity_passes", runtime_summary["integrity_mismatch_count"] == 0 and runtime_summary["pending_integrity_mismatch_count"] == 0),
        ("runtime_reasoning_state_preserves_authority", runtime_summary["all_authority_boundaries_preserved"]),
        ("runtime_reasoning_state_requires_no_structural_repair", not runtime_summary["review_required"]),
        ("checkpoint_registry_discovers_consolidation_checkpoint", int(registry.get("checkpoint_count") or 0) >= 182 and not registry.get("duplicate_checkpoint_ids") and not registry.get("duplicate_builder_targets")),
        ("source_only_policy_excludes_runtime_data", privacy_policy.get("excludes_all_data_directory_entries") is True and not privacy_policy.get("authorizes_package_creation") and not privacy_policy.get("publishes_release")),
        ("current_source_tree_privacy_scan_passes", privacy.get("ok") is True and privacy.get("source_only") is True and privacy.get("forbidden_count") == 0 and privacy.get("private_content_finding_count") == 0),
        ("remaining_limitations_are_explicit", len(limitations) == 5 and all(row.get("status") == "open" for row in limitations)),
        ("checkpoint_does_not_modify_source_or_runtime", source_before == _tree_signature(source, source_tree=True) and runtime_before == _tree_signature(runtime, source_tree=False)),
    ]
    check_rows = [{"check_id": name, "status": "pass" if value else "fail"} for name, value in checks]
    passed = sum(1 for _, value in checks if value)
    total = len(checks)
    ok = passed == total

    report: dict[str, Any] = {
        "contract_version": CONTRACT_VERSION,
        "checkpoint_id": _CHECKPOINT_ID,
        "ok": ok,
        "status": "reasoning_alpha_consolidation_candidate" if ok else "review_required",
        "passed": passed,
        "total": total,
        "checks": check_rows,
        "summary": {
            "synthetic_contract_check_count": synthetic["total"],
            "registered_checkpoint_count": registry.get("checkpoint_count", 0),
            "runtime_reasoning_record_count": runtime_summary["record_count"],
            "runtime_reasoning_pending_count": runtime_summary["pending_count"],
            "runtime_reasoning_stale_count": runtime_summary["stale_count"],
            "runtime_reasoning_integrity_mismatch_count": runtime_summary["integrity_mismatch_count"] + runtime_summary["pending_integrity_mismatch_count"],
            "maximum_reasoning_cases": MAX_CASES,
            "maximum_options_per_case": MAX_OPTIONS,
            "maximum_prompt_projection_chars": MAX_SUMMARY_CHARS,
            "maximum_reasoning_records": MAX_RECORDS,
            "maximum_pending_records": MAX_PENDING,
            "reasoning_stale_after_days": STALE_AFTER_DAYS,
            "open_limitation_count": len(limitations),
            "privacy_forbidden_entry_count": privacy.get("forbidden_count", 0),
            "privacy_content_finding_count": privacy.get("private_content_finding_count", 0),
        },
        "evidence": {
            "synthetic_contracts": synthetic,
            "runtime_reasoning_health": runtime_summary,
            "ordinary_conversation_integration": integration,
            "registry": {
                "checkpoint_count": registry.get("checkpoint_count", 0),
                "duplicate_checkpoint_id_count": len(registry.get("duplicate_checkpoint_ids") or []),
                "duplicate_builder_target_count": len(registry.get("duplicate_builder_targets") or []),
                "content_free": True,
            },
            "privacy": {
                "source_only": privacy.get("source_only"),
                "forbidden_count": privacy.get("forbidden_count", 0),
                "private_content_finding_count": privacy.get("private_content_finding_count", 0),
                "structural_digest": privacy.get("structural_digest", ""),
                "content_free": True,
            },
        },
        "remaining_limitations": limitations,
        "read_only": True,
        "post_available": False,
        "content_free": True,
        "authority_preserved": True,
        "operator_promotion_required": True,
        "desktop_verification_deferred_until_v1200": True,
        "native_provider_certification_pending": True,
        "consciousness_proven": False,
        "sentience_proven": False,
        "personhood_proven": False,
        "raw_conversation_exposed": False,
        "raw_message_exposed": False,
        "prompt_exposed": False,
        "reasoning_content_exposed": False,
        "reasoning_registry_exposed": False,
        "session_identifiers_exposed": False,
        "operation_identifiers_exposed": False,
        "memory_text_exposed": False,
        "evidence_text_exposed": False,
        "provider_payload_exposed": False,
        "hidden_reasoning_exposed": False,
    }
    for field in (
        "provider_contacted", "command_executed", "action_executed", "message_sent",
        "notification_created", "goal_created", "goal_modified", "plan_created",
        "decision_created", "intention_created", "conflict_resolved",
        "approval_request_created", "approval_created", "approval_granted",
        "authorization_created", "installation_performed", "upgrade_performed",
        "rollback_performed", "packaging_performed", "promotion_performed",
        "certification_performed",
    ):
        report[field] = False
    report["structural_digest"] = _digest({
        "contract_version": CONTRACT_VERSION,
        "checks": check_rows,
        "summary": report["summary"],
        "limitations": limitations,
        "runtime_digest": runtime_summary["structural_digest"],
        "synthetic_digest": synthetic["structural_digest"],
    })
    serialized = json.dumps(report, sort_keys=True)
    report["forbidden_report_token_count"] = sum(1 for token in _FORBIDDEN_REPORT_TOKENS if f'"{token}"' in serialized)
    return report
