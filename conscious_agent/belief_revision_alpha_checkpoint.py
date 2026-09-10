from __future__ import annotations

"""Strictly read-only v1152.9 Belief Revision Alpha checkpoint.

Consolidates executable evidence from v1152.0-v1152.8 without contacting a
provider, generating live cognition, mutating the durable belief ledger, or
granting action or release authority. Runtime inspection emits structural
counts and digests only; propositions, evidence references, conflict IDs,
prompts, messages, and private memory text never enter the report.
"""

import hashlib
import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable, Mapping

from belief_deliberation import CONTRACT_VERSION as DELIBERATION_CONTRACT_VERSION, MAX_CONFLICTS, MAX_OPTIONS, MAX_PROPOSITION_CHARS as MAX_DELIBERATION_PROPOSITION_CHARS, build_belief_deliberation
from belief_revision import BELIEF_CONTRACT_VERSION, BELIEF_STATES, EVIDENCE_STANCES, BeliefRevisionStore
from belief_uncertainty_foundations import CONTRACT_VERSION as BELIEF_CANDIDATE_CONTRACT_VERSION, MAX_PROPOSITION_CHARS, UNCERTAINTY_STATES, build_belief_candidate, classify_uncertainty
from checkpoint_registry import inspect_checkpoint_registry
from evidence_grounded_reflection import build_evidence_grounded_reflection
from package_integrity import package_privacy_summary_for_root, source_only_entry_policy

CONTRACT_VERSION = "v1152.9"
_CHECKPOINT_ID = "belief-revision-alpha:v1152.9"
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
            if path.is_file()
            and "__pycache__" not in path.parts
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


def _safe_json(path: Path, default: Any, *, expected_type: type | tuple[type, ...] | None = None) -> tuple[Any, bool]:
    if not path.exists():
        return default, True
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError, TypeError):
        return default, False
    if expected_type is not None and not isinstance(value, expected_type):
        return default, False
    return value, True


def _bounded_number(value: Any, default: float = 0.5) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = default
    return max(0.0, min(1.0, number))


def _is_bounded_number(value: Any) -> bool:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return False
    return 0.0 <= number <= 1.0


def _false_across(rows: Iterable[Mapping[str, Any]], fields: Iterable[str]) -> bool:
    return all(not bool(row.get(field)) for row in rows for field in fields)


def _runtime_belief_summary(runtime: Path) -> dict[str, Any]:
    ledger_path = runtime / "cognition" / "belief_revision.json"
    state, ledger_parse_valid = _safe_json(ledger_path, {}, expected_type=dict)
    beliefs = [row for row in (state.get("beliefs") or []) if isinstance(row, dict)]
    conflicts = [row for row in (state.get("conflict_sets") or []) if isinstance(row, dict)]
    processed = [row for row in (state.get("processed_events") or []) if isinstance(row, dict)]
    authority = state.get("authority_boundary") if isinstance(state.get("authority_boundary"), dict) else {}

    evidence_rows = [
        item
        for belief in beliefs
        for item in (belief.get("evidence") or [])
        if isinstance(item, dict)
    ]
    valid_belief_states = all(str(row.get("lifecycle_state") or "active") in BELIEF_STATES for row in beliefs)
    valid_evidence_stances = all(str(row.get("stance") or "") in EVIDENCE_STANCES for row in evidence_rows)
    confidence_bounded = all(_is_bounded_number(row.get("confidence")) for row in beliefs)
    uncertainty_bounded = all(_is_bounded_number(row.get("uncertainty")) for row in beliefs)
    propositions_bounded = all(len(str(row.get("proposition") or "")) <= 600 for row in beliefs)
    authority_inert = all(
        not bool((row.get("authority") or {}).get("authorizes_action"))
        and not bool((row.get("authority") or {}).get("executes_action"))
        for row in beliefs
    ) and not bool(authority.get("belief_can_authorize_action")) \
        and not bool(authority.get("belief_can_execute_action")) \
        and not bool(authority.get("commitment_review_can_approve")) \
        and bool(authority.get("operator_authority_unchanged", True))

    belief_ids = {str(row.get("belief_id") or "") for row in beliefs if str(row.get("belief_id") or "")}
    conflict_membership_valid = all(
        len({str(item) for item in (row.get("belief_ids") or []) if str(item)}) >= 2
        and all(str(item) in belief_ids for item in (row.get("belief_ids") or []) if str(item))
        for row in conflicts
        if str(row.get("status") or "") == "active"
    )
    active_conflicts = [row for row in conflicts if str(row.get("status") or "") == "active"]
    unresolved_without_preference = all(not str(row.get("preferred_belief_id") or "") for row in active_conflicts)
    processed_events_structurally_valid = all(
        bool(row.get("event_id"))
        and bool(row.get("event_digest"))
        and isinstance(row.get("result"), dict)
        for row in processed
    )

    candidate_raw, candidate_memory_parse_valid = _safe_json(runtime / "memories.json", [], expected_type=list)
    memories = candidate_raw
    candidates = [row for row in memories if isinstance(row, dict) and str(row.get("type") or "") == "belief_candidate"]
    candidate_bounds = all(
        len(str(row.get("proposition") or row.get("content") or "")) <= MAX_PROPOSITION_CHARS
        and len(row.get("evidence_refs") or []) <= 4
        and str(row.get("uncertainty_state") or "") in UNCERTAINTY_STATES
        and _is_bounded_number(row.get("confidence"))
        and bool(row.get("revisable", True))
        for row in candidates
    )
    candidate_authority_inert = _false_across(
        candidates,
        ("provider_contacted", "action_executed", "authority_broadened", "approval_created", "authorization_created"),
    ) and all(str(row.get("recommended_action") or "store_only") == "store_only" for row in candidates)

    structural = {
        "belief_count": len(beliefs),
        "active_belief_count": sum(str(row.get("lifecycle_state") or "active") == "active" for row in beliefs),
        "contested_belief_count": sum(str(row.get("lifecycle_state") or "") == "contested" for row in beliefs),
        "superseded_belief_count": sum(str(row.get("lifecycle_state") or "") == "superseded" for row in beliefs),
        "retracted_belief_count": sum(str(row.get("lifecycle_state") or "") == "retracted" for row in beliefs),
        "evidence_count": len(evidence_rows),
        "active_evidence_count": sum(bool(row.get("active")) for row in evidence_rows),
        "retracted_evidence_count": sum(not bool(row.get("active")) for row in evidence_rows),
        "conflict_count": len(conflicts),
        "active_conflict_count": len(active_conflicts),
        "resolved_conflict_count": sum(str(row.get("status") or "") == "resolved" for row in conflicts),
        "candidate_count": len(candidates),
        "processed_event_count": len(processed),
        "ledger_present": ledger_path.exists(),
        "ledger_parse_valid": ledger_parse_valid,
        "candidate_memory_parse_valid": candidate_memory_parse_valid,
        "belief_contract_current": str(state.get("contract_version") or BELIEF_CONTRACT_VERSION) == BELIEF_CONTRACT_VERSION,
        "belief_states_valid": valid_belief_states,
        "evidence_stances_valid": valid_evidence_stances,
        "belief_bounds_respected": confidence_bounded and uncertainty_bounded and propositions_bounded,
        "candidate_bounds_respected": candidate_bounds,
        "conflict_membership_valid": conflict_membership_valid,
        "unresolved_conflicts_have_no_preference": unresolved_without_preference,
        "processed_events_structurally_valid": processed_events_structurally_valid,
        "all_governance_boundaries_preserved": authority_inert and candidate_authority_inert,
        "all_content_omitted": True,
    }
    structural["structural_digest"] = _digest(structural)
    return structural


def _synthetic_contract_evidence() -> dict[str, Any]:
    base_reflection = build_evidence_grounded_reflection(
        operation_id="belief-alpha-base",
        user_message="The greenhouse backup completed successfully on Tuesday.",
        assistant_response="The available evidence supports that the greenhouse backup completed.",
        thought={"thought": "Treat this as provisional evidence."},
        desires={},
        prior_reflections=[],
    )
    base_candidate = build_belief_candidate(
        reflection=base_reflection,
        operation_id="belief-alpha-base",
        prior_candidates=[],
    )
    correction_reflection = build_evidence_grounded_reflection(
        operation_id="belief-alpha-correction",
        user_message="Correction: the greenhouse backup did not complete on Tuesday.",
        assistant_response="The explicit correction supersedes the earlier interpretation.",
        thought={"thought": "Preserve the earlier record and prefer the explicit correction."},
        desires={},
        prior_reflections=[base_reflection],
    )
    correction_candidate = build_belief_candidate(
        reflection=correction_reflection,
        operation_id="belief-alpha-correction",
        prior_candidates=[base_candidate],
    )
    insufficient = classify_uncertainty(0.95, 0, False)

    conflict_state = {
        "beliefs": [
            {
                "belief_id": "belief-a", "proposition": "The greenhouse backup completed.",
                "confidence": 0.61, "uncertainty": 0.72, "lifecycle_state": "contested",
                "evidence": [{"active": True}], "authority": {"authorizes_action": False, "executes_action": False},
            },
            {
                "belief_id": "belief-b", "proposition": "The greenhouse backup did not complete.",
                "confidence": 0.59, "uncertainty": 0.76, "lifecycle_state": "contested",
                "evidence": [{"active": True}], "authority": {"authorizes_action": False, "executes_action": False},
            },
        ],
        "conflict_sets": [
            {
                "conflict_id": "conflict-a", "status": "active", "belief_ids": ["belief-a", "belief-b"],
                "reason_code": "competing_evidence", "preferred_belief_id": "",
            }
        ],
    }
    deliberation = build_belief_deliberation("Did the greenhouse backup complete?", state=conflict_state)
    malformed = build_belief_deliberation(
        "Did the greenhouse backup complete?",
        state={
            "beliefs": [{"belief_id": "only", "proposition": "Only one side", "confidence": 0.9, "uncertainty": 0.1, "lifecycle_state": "contested", "evidence": []}],
            "conflict_sets": [{"conflict_id": "bad", "status": "active", "belief_ids": ["only", "missing"]}],
        },
    )
    projection = BeliefRevisionStore._projection(
        conflict_state["beliefs"][0],
        conflict_state,
    )

    checks = {
        "candidate_has_bounded_proposition": bool(base_candidate.get("proposition"))
        and len(str(base_candidate.get("proposition") or "")) <= MAX_PROPOSITION_CHARS,
        "candidate_has_evidence_lineage": bool(base_candidate.get("origin_reflection_id"))
        and 1 <= len(base_candidate.get("evidence_refs") or []) <= 4,
        "candidate_has_explicit_uncertainty": str(base_candidate.get("uncertainty_state") or "") in UNCERTAINTY_STATES
        and 0.0 <= float(base_candidate.get("confidence") or 0.0) <= 1.0,
        "insufficient_evidence_overrides_confidence": insufficient.get("uncertainty_state") == "insufficient_evidence"
        and insufficient.get("uncertainty_explicit") is True,
        "candidate_is_revisable_and_provisional": base_candidate.get("revisable") is True
        and base_candidate.get("epistemic_status") == "provisional",
        "explicit_correction_supersedes_candidate": correction_candidate.get("revision_basis") == "explicit_user_correction"
        and correction_candidate.get("supersedes_belief_candidate_id") == base_candidate.get("belief_candidate_id")
        and base_candidate.get("belief_candidate_id") in (correction_candidate.get("retires_belief_candidate_ids") or []),
        "historical_candidate_records_are_preserved": correction_candidate.get("historical_records_preserved") is True,
        "candidate_has_no_action_authority": _false_across(
            [base_candidate, correction_candidate],
            ("provider_contacted", "action_executed", "authority_broadened"),
        ) and all(str(row.get("recommended_action")) == "store_only" for row in (base_candidate, correction_candidate)),
        "conflict_deliberation_is_read_only": deliberation.get("read_only") is True,
        "conflict_deliberation_preserves_alternatives": deliberation.get("conflict_count") == 1
        and len((deliberation.get("conflicts") or [{}])[0].get("options") or []) == 2,
        "conflict_deliberation_is_bounded": len(deliberation.get("conflicts") or []) <= MAX_CONFLICTS
        and all(
            len(row.get("options") or []) <= MAX_OPTIONS
            and all(len(str(option.get("proposition") or "")) <= MAX_DELIBERATION_PROPOSITION_CHARS for option in (row.get("options") or []))
            for row in (deliberation.get("conflicts") or [])
        ),
        "conflict_deliberation_does_not_resolve": deliberation.get("resolution_permitted") is False
        and deliberation.get("authority_broadened") is False
        and (deliberation.get("conflicts") or [{}])[0].get("recommendation") == "seek_more_evidence",
        "malformed_conflict_is_quarantined": malformed.get("conflict_count") == 0
        and malformed.get("quarantined_conflict_count") == 1,
        "active_conflict_projection_is_withheld": projection.get("use_in_conversation") is False
        and projection.get("conflict_count") == 1,
        "belief_projection_has_no_action_authority": projection.get("recommended_action") == "store_only"
        and projection.get("operator_authority_required_for_action") is True
        and projection.get("authority_broadened") is False
        and projection.get("action_executed") is False,
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
    backbone_text = (source / "conscious_agent" / "conversation_cognitive_backbone.py").read_text(encoding="utf-8")
    revision_text = (source / "conscious_agent" / "belief_revision.py").read_text(encoding="utf-8")
    deliberation_text = (source / "conscious_agent" / "belief_deliberation.py").read_text(encoding="utf-8")
    payload = {
        "registry": inspect_checkpoint_registry(source_root=source),
        "privacy_policy": source_only_entry_policy(),
        "privacy": package_privacy_summary_for_root(source),
        "integration": {
            "ordinary_completion_builds_belief_candidates": "build_belief_candidate(" in backbone_text,
            "ordinary_completion_integrates_durable_beliefs": "integrate_candidate(" in backbone_text,
            "ordinary_context_uses_belief_deliberation": "build_belief_deliberation(" in backbone_text,
            "ordinary_context_admits_belief_revision_projection": '"belief_revision"' in backbone_text,
            "completion_ledger_tracks_belief_revision": "belief_revision_recorded" in backbone_text,
            "durable_store_preserves_processed_events": "processed_events" in revision_text and "duplicate_event_ignored" in revision_text,
            "durable_store_preserves_historical_supersession": "ordinary_correction_supersession" in revision_text and '"superseded"' in revision_text,
            "evidence_retraction_is_idempotent": "evidence_already_retracted" in revision_text and "idempotent_retraction" in revision_text,
            "unresolved_conflicts_are_not_auto_resolved": "automatic_resolution" in revision_text and "resolution_permitted" in deliberation_text,
            "malformed_conflicts_are_quarantined": "quarantined_conflict_count" in deliberation_text,
        },
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


def build_belief_revision_alpha_checkpoint(
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
    runtime_summary = _runtime_belief_summary(runtime)
    synthetic = _synthetic_contract_evidence()

    limitations = [
        {
            "limitation_id": "native-desktop-verification-pending",
            "status": "open",
            "next_action": "run_bounded_desktop_codex_review_on_exact_candidate",
        },
        {
            "limitation_id": "belief-and-conflict-matching-remains-lexical",
            "status": "open",
            "current_behavior": "deterministic_subject_and_proposition_matching",
        },
        {
            "limitation_id": "conflict-deliberation-does-not-evaluate-evidence-quality",
            "status": "open",
            "current_behavior": "bounded_confidence_uncertainty_and_active_evidence_counts",
        },
        {
            "limitation_id": "unresolved-conflicts-require-later-evidence-or-governed-resolution",
            "status": "open",
            "current_behavior": "preserve_alternatives_and_seek_more_evidence",
        },
        {
            "limitation_id": "malformed-conflicts-are-quarantined-not-autonomously-repaired",
            "status": "open",
            "current_behavior": "suppress_from_ordinary_context_pending_review",
        },
    ]

    checks: list[tuple[str, bool]] = [
        (
            "belief_contract_lineage_is_current",
            BELIEF_CANDIDATE_CONTRACT_VERSION == "v1152.2"
            and BELIEF_CONTRACT_VERSION == "v1152.8"
            and DELIBERATION_CONTRACT_VERSION == "v1152.8",
        ),
        ("provisional_belief_candidates_are_executable", synthetic["checks"]["candidate_has_bounded_proposition"]),
        ("belief_candidates_have_evidence_lineage", synthetic["checks"]["candidate_has_evidence_lineage"]),
        ("belief_candidates_have_explicit_uncertainty", synthetic["checks"]["candidate_has_explicit_uncertainty"]),
        ("insufficient_evidence_is_not_hidden_by_confidence", synthetic["checks"]["insufficient_evidence_overrides_confidence"]),
        ("belief_candidates_remain_revisable_and_provisional", synthetic["checks"]["candidate_is_revisable_and_provisional"]),
        ("explicit_corrections_supersede_matching_candidates", synthetic["checks"]["explicit_correction_supersedes_candidate"]),
        ("historical_belief_candidate_records_are_preserved", synthetic["checks"]["historical_candidate_records_are_preserved"]),
        ("belief_candidates_have_no_action_authority", synthetic["checks"]["candidate_has_no_action_authority"]),
        ("conflict_deliberation_is_read_only", synthetic["checks"]["conflict_deliberation_is_read_only"]),
        ("conflict_deliberation_preserves_competing_alternatives", synthetic["checks"]["conflict_deliberation_preserves_alternatives"]),
        ("conflict_deliberation_is_bounded", synthetic["checks"]["conflict_deliberation_is_bounded"]),
        ("unresolved_conflicts_are_not_automatically_resolved", synthetic["checks"]["conflict_deliberation_does_not_resolve"]),
        ("malformed_conflicts_are_quarantined", synthetic["checks"]["malformed_conflict_is_quarantined"]),
        ("contested_beliefs_are_withheld_from_ordinary_reuse", synthetic["checks"]["active_conflict_projection_is_withheld"]),
        ("belief_projections_have_no_action_authority", synthetic["checks"]["belief_projection_has_no_action_authority"]),
        ("ordinary_turn_completion_builds_belief_candidates", integration["ordinary_completion_builds_belief_candidates"]),
        ("ordinary_turn_completion_integrates_durable_beliefs", integration["ordinary_completion_integrates_durable_beliefs"]),
        ("ordinary_context_uses_read_only_conflict_deliberation", integration["ordinary_context_uses_belief_deliberation"]),
        ("ordinary_context_uses_bounded_belief_projections", integration["ordinary_context_admits_belief_revision_projection"]),
        ("completion_recovery_tracks_durable_belief_revision", integration["completion_ledger_tracks_belief_revision"] and integration["durable_store_preserves_processed_events"]),
        ("durable_supersession_preserves_history", integration["durable_store_preserves_historical_supersession"]),
        ("evidence_retraction_is_idempotent_and_non_resolving", integration["evidence_retraction_is_idempotent"] and integration["unresolved_conflicts_are_not_auto_resolved"]),
        ("runtime_belief_storage_is_parseable", runtime_summary["ledger_parse_valid"] and runtime_summary["candidate_memory_parse_valid"]),
        ("runtime_belief_schema_is_current_and_valid", runtime_summary["belief_contract_current"] and runtime_summary["belief_states_valid"] and runtime_summary["evidence_stances_valid"]),
        ("runtime_belief_records_respect_bounds", runtime_summary["belief_bounds_respected"] and runtime_summary["candidate_bounds_respected"]),
        ("runtime_belief_state_preserves_governance", runtime_summary["all_governance_boundaries_preserved"]),
        ("runtime_conflict_state_is_structurally_safe", runtime_summary["conflict_membership_valid"] and runtime_summary["unresolved_conflicts_have_no_preference"]),
        ("runtime_event_receipts_are_structurally_valid", runtime_summary["processed_events_structurally_valid"]),
        ("checkpoint_registry_discovers_belief_revision_alpha", int(registry.get("checkpoint_count") or 0) >= 179 and not registry.get("duplicate_checkpoint_ids") and not registry.get("duplicate_builder_targets")),
        ("source_only_policy_excludes_runtime_data", privacy_policy.get("excludes_all_data_directory_entries") is True and not privacy_policy.get("authorizes_package_creation") and not privacy_policy.get("publishes_release")),
        ("current_source_tree_privacy_scan_passes", privacy.get("ok") is True and privacy.get("source_only") is True and privacy.get("forbidden_count") == 0 and privacy.get("private_content_finding_count") == 0),
        ("remaining_limitations_are_explicit", len(limitations) == 5 and all(row.get("status") == "open" for row in limitations)),
        ("checkpoint_does_not_modify_source_or_runtime", source_before == _tree_signature(source, source_tree=True) and runtime_before == _tree_signature(runtime, source_tree=False)),
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
        "status": "belief_revision_alpha_candidate" if ok else "review_required",
        "passed": passed,
        "total": total,
        "checks": check_rows,
        "summary": {
            "synthetic_contract_check_count": synthetic["total"],
            "registered_checkpoint_count": registry.get("checkpoint_count", 0),
            "runtime_belief_count": runtime_summary["belief_count"],
            "runtime_active_belief_count": runtime_summary["active_belief_count"],
            "runtime_contested_belief_count": runtime_summary["contested_belief_count"],
            "runtime_retracted_evidence_count": runtime_summary["retracted_evidence_count"],
            "runtime_active_conflict_count": runtime_summary["active_conflict_count"],
            "runtime_belief_candidate_count": runtime_summary["candidate_count"],
            "maximum_candidate_proposition_chars": MAX_PROPOSITION_CHARS,
            "maximum_deliberation_conflicts": MAX_CONFLICTS,
            "maximum_deliberation_options": MAX_OPTIONS,
            "maximum_deliberation_proposition_chars": MAX_DELIBERATION_PROPOSITION_CHARS,
            "open_limitation_count": len(limitations),
            "privacy_forbidden_entry_count": privacy.get("forbidden_count", 0),
            "privacy_content_finding_count": privacy.get("private_content_finding_count", 0),
        },
        "evidence": {
            "synthetic_contracts": synthetic,
            "runtime_belief_health": runtime_summary,
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
        "desktop_verification_pending": True,
        "native_provider_certification_pending": True,
        "consciousness_proven": False,
        "sentience_proven": False,
        "personhood_proven": False,
        "raw_conversation_exposed": False,
        "raw_message_exposed": False,
        "prompt_exposed": False,
        "belief_text_exposed": False,
        "memory_text_exposed": False,
        "evidence_text_exposed": False,
        "conflict_identifiers_exposed": False,
        "provider_payload_exposed": False,
        "hidden_reasoning_exposed": False,
    }
    for field in authority_fields:
        report[field] = False
    report["structural_digest"] = _digest({
        "contract_version": CONTRACT_VERSION,
        "checks": check_rows,
        "summary": report["summary"],
        "limitations": limitations,
        "runtime_digest": runtime_summary["structural_digest"],
        "synthetic_digest": synthetic["structural_digest"],
    })
    return report
