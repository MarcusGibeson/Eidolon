from __future__ import annotations

"""v1245 cross-session project understanding.

This module stores content-free, project-scoped understanding snapshots and
reconciles them against evidence from later sessions.  It never treats memory
as current truth, reads project contents, modifies a project, writes cognition,
or creates execution authority.
"""

import html
import os
import re
import shutil
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterable, Mapping

from ordinary_chat_development_campaign import _atomic_json, _digest, _read_json, _store_root

SCHEMA_VERSION = "1"
CONTRACT_VERSION = "v1245.8"
MILESTONE_NAME = "Cross-Session Project Understanding"
ROADMAP_PATH = "Balanced Mind-and-Action Path 3"
MAX_RECORDS = 400

ITEM_TYPES = {
    "project_purpose", "operator_goal", "architecture_component", "component_relationship",
    "language_framework", "important_boundary", "design_decision", "limitation_risk",
    "completed_work", "pending_work", "open_question",
}
CONFIDENCE_LEVELS = {"low", "medium", "high", "verified"}
OBSERVATION_STATES = {"present", "changed", "contradictory", "missing", "unverified", "superseded"}
CLASSIFICATIONS = {"still_valid", "changed", "contradicted", "missing", "stale", "unverified", "superseded"}
REVIEW_DISPOSITIONS = {"accept_update", "hold", "reject", "request_changes"}

AUTHORITY_FLAGS = {
    "project_understanding_inspection_authorized": True,
    "project_understanding_snapshot_preparation_authorized": True,
    "project_understanding_reconciliation_preparation_authorized": True,
    "project_understanding_review_authorized": True,
    "project_understanding_revision_preparation_authorized": True,
    "project_understanding_current_truth_authorized": False,
    "project_understanding_automatic_update_authorized": False,
    "project_understanding_contradiction_resolution_authorized": False,
    "project_inspection_authorized": False,
    "project_mutation_authorized": False,
    "plan_revision_authorized": False,
    "queue_mutation_authorized": False,
    "schedule_mutation_authorized": False,
    "session_launch_authorized": False,
    "session_resume_authorized": False,
    "provider_contact_authorized": False,
    "prompt_transmission_authorized": False,
    "tool_invocation_authorized": False,
    "command_execution_authorized": False,
    "test_execution_authorized": False,
    "workspace_materialization_authorized": False,
    "cognition_write_authorized": False,
    "automatic_retry_authorized": False,
    "background_execution_authorized": False,
    "approval_creation_authorized": False,
    "approval_consumption_authorized": False,
    "installation_authorized": False,
    "promotion_authorized": False,
    "certification_authorized": False,
    "release_authorized": False,
    "model_management_authorized": False,
    "remembered_state_accepted_without_revalidation": False,
}

_TOKEN = re.compile(r"^[a-z][a-z0-9_\-]{1,96}$")
_PROJECT = re.compile(r"^project_[a-z0-9_\-]{2,64}$")
_SESSION = re.compile(r"^(?:session|launch|execution_session|prepared_session)_[a-z0-9_\-]{2,80}$")
_SNAPSHOT = re.compile(r"^project_understanding_snapshot_[a-f0-9]{24}$")
_RECONCILIATION = re.compile(r"^project_understanding_reconciliation_[a-f0-9]{24}$")
_REVIEW = re.compile(r"^project_understanding_review_[a-f0-9]{24}$")
_HEX64 = re.compile(r"^[a-f0-9]{64}$")
_PRIVATE = ("secret", "password", "credential", "prompt", "content", "endpoint", "private", "username", "email", "absolute_path")

_SHOW_REGISTRY = re.compile(r"^show cross session project understanding registry[.!?]*$", re.I)
_SHOW_SNAPSHOTS = re.compile(r"^show project understanding snapshots[.!?]*$", re.I)
_SHOW_RECONCILIATIONS = re.compile(r"^show project understanding reconciliations[.!?]*$", re.I)
_SHOW_REVIEWS = re.compile(r"^show project understanding reviews[.!?]*$", re.I)
_REVIEW_RECONCILIATION = re.compile(
    r"^review project understanding (?P<decision>accept_update|hold|reject|request_changes) "
    r"for reconciliation (?P<reconciliation>project_understanding_reconciliation_[a-f0-9]{24}) "
    r"digest (?P<digest>[a-f0-9]{64})[.!?]*$", re.I,
)


def _root(runtime_root=None) -> Path:
    return _store_root(runtime_root)


def _dir(name: str, runtime_root=None) -> Path:
    return _root(runtime_root) / name


def _path(name: str, record_id: str, runtime_root=None) -> Path:
    return _dir(name, runtime_root) / f"{str(record_id or '').lower()}.json"


@contextmanager
def _lock(runtime_root=None):
    path = _root(runtime_root) / "locks" / "cross-session-project-understanding.lock"
    path.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + 15.0
    while True:
        try:
            path.mkdir()
            (path / "owner").write_text(str(os.getpid()), encoding="ascii")
            break
        except FileExistsError:
            try:
                if time.time() - path.stat().st_mtime > 60:
                    shutil.rmtree(path, ignore_errors=True)
                    continue
            except FileNotFoundError:
                continue
            if time.monotonic() >= deadline:
                raise TimeoutError("Timed out waiting for project understanding lock")
            time.sleep(0.02)
    try:
        yield
    finally:
        shutil.rmtree(path, ignore_errors=True)


def _sealed(record: Mapping[str, Any], field: str) -> dict[str, Any]:
    row = dict(record)
    row[field] = _digest({key: value for key, value in row.items() if key != field})
    return row


def _valid(record: Mapping[str, Any], field: str) -> bool:
    supplied = str(record.get(field) or "")
    return bool(supplied and supplied == _digest({key: value for key, value in record.items() if key != field}))


def _hex(value: Any, reason: str, *, allow_empty: bool = False) -> str:
    text = str(value or "").lower().strip()
    if allow_empty and not text:
        return ""
    if not _HEX64.fullmatch(text):
        raise ValueError(reason)
    return text


def _token(value: Any, reason: str, *, pattern: re.Pattern[str] = _TOKEN) -> str:
    text = str(value or "").lower().strip()
    if not pattern.fullmatch(text) or any(part in text for part in _PRIVATE):
        raise ValueError(reason)
    return text


def _tokens(values: Iterable[Any], reason: str) -> list[str]:
    rows = sorted({_token(value, reason) for value in values or []})
    return rows


def _base() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "content_free": True,
        "runtime_records_external": True,
        "project_scoped": True,
        "historical_records_immutable": True,
        "exact_lineage_required": True,
        "current_evidence_revalidation_required": True,
        "remembered_state_is_not_current_truth": True,
        "uncertainty_preserved": True,
        "contradictions_preserved": True,
        "raw_project_content_read": False,
        "raw_project_content_exposed": False,
        "private_path_exposed": False,
        "private_content_exposed": False,
        "project_modified": False,
        "plan_revised": False,
        "queue_modified": False,
        "schedule_modified": False,
        "session_launched": False,
        "session_resumed": False,
        "provider_contacted": False,
        "prompt_transmitted": False,
        "tool_invoked": False,
        "commands_executed": False,
        "tests_executed": False,
        "workspace_materialized": False,
        "cognition_written": False,
        "automatic_retry_created": False,
        "background_execution_created": False,
        **AUTHORITY_FLAGS,
    }


def _failure(status: str, reason: str = "") -> dict[str, Any]:
    row = {"ok": False, "status": status, "reason": reason, **_base()}
    row["project_understanding_result_digest"] = _digest(row)
    return row


def cross_session_project_understanding_registry() -> dict[str, Any]:
    row = {
        "ok": True,
        "status": "cross_session_project_understanding_registry_ready",
        "item_types": sorted(ITEM_TYPES),
        "confidence_levels": sorted(CONFIDENCE_LEVELS),
        "observation_states": sorted(OBSERVATION_STATES),
        "classifications": sorted(CLASSIFICATIONS),
        "review_dispositions": sorted(REVIEW_DISPOSITIONS),
        "inspection_only": True,
        **_base(),
    }
    row["registry_digest"] = _digest(row)
    return row


def _normalize_items(items: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in items or []:
        if not isinstance(raw, Mapping):
            raise ValueError("project_understanding_item_mapping_required")
        code = _token(raw.get("item_code"), "invalid_item_code")
        if code in seen:
            raise ValueError("duplicate_item_code")
        seen.add(code)
        item_type = _token(raw.get("item_type"), "invalid_item_type")
        if item_type not in ITEM_TYPES:
            raise ValueError("unsupported_item_type")
        confidence = _token(raw.get("confidence"), "invalid_confidence")
        if confidence not in CONFIDENCE_LEVELS:
            raise ValueError("unsupported_confidence")
        day = int(raw.get("last_verified_day", 0))
        window = int(raw.get("freshness_window_days", 30))
        if day < 0 or window < 0 or window > 3650:
            raise ValueError("invalid_item_freshness")
        evidence = sorted({_hex(value, "invalid_item_evidence_digest") for value in raw.get("evidence_digests") or []})
        if not evidence:
            raise ValueError("item_evidence_required")
        rows.append({
            "item_code": code,
            "item_type": item_type,
            "statement_digest": _hex(raw.get("statement_digest"), "invalid_statement_digest"),
            "evidence_digests": evidence,
            "evidence_count": len(evidence),
            "confidence": confidence,
            "last_verified_day": day,
            "freshness_window_days": window,
            "component_code": _token(raw.get("component_code"), "invalid_component_code") if raw.get("component_code") else "",
            "related_codes": _tokens(raw.get("related_codes") or [], "invalid_related_code"),
            "provenance_session_digest": _hex(raw.get("provenance_session_digest"), "invalid_provenance_session_digest"),
        })
    if not rows:
        raise ValueError("project_understanding_items_required")
    return sorted(rows, key=lambda row: row["item_code"])


def _normalize_relationships(relationships: Iterable[Mapping[str, Any]], item_codes: set[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for raw in relationships or []:
        if not isinstance(raw, Mapping):
            raise ValueError("relationship_mapping_required")
        source = _token(raw.get("source_code"), "invalid_relationship_source")
        target = _token(raw.get("target_code"), "invalid_relationship_target")
        if source not in item_codes or target not in item_codes or source == target:
            raise ValueError("relationship_endpoint_mismatch")
        rows.append({
            "source_code": source,
            "target_code": target,
            "relationship_code": _token(raw.get("relationship_code"), "invalid_relationship_code"),
            "evidence_digest": _hex(raw.get("evidence_digest"), "invalid_relationship_evidence_digest"),
        })
    unique = {(_digest(row), tuple(sorted(row.items()))): row for row in rows}
    return sorted(unique.values(), key=lambda row: (row["source_code"], row["target_code"], row["relationship_code"]))


def prepare_project_understanding_snapshot(
    project_id: str,
    *,
    project_identity_digest: str,
    repository_fingerprint_digest: str,
    source_session_id: str,
    source_session_digest: str,
    logical_day: int,
    generation: int,
    items: Iterable[Mapping[str, Any]],
    relationships: Iterable[Mapping[str, Any]] = (),
    continuity_manifest_id: str = "",
    continuity_manifest_digest: str = "",
    previous_snapshot_id: str = "",
    previous_snapshot_digest: str = "",
    accepted_review_id: str = "",
    accepted_review_digest: str = "",
    runtime_root=None,
) -> dict[str, Any]:
    try:
        project = _token(project_id, "invalid_project_id", pattern=_PROJECT)
        identity_digest = _hex(project_identity_digest, "invalid_project_identity_digest")
        fingerprint = _hex(repository_fingerprint_digest, "invalid_repository_fingerprint_digest")
        session = _token(source_session_id, "invalid_source_session_id", pattern=_SESSION)
        session_digest = _hex(source_session_digest, "invalid_source_session_digest")
        day = int(logical_day)
        gen = int(generation)
        if day < 0 or gen < 1:
            raise ValueError("invalid_snapshot_day_or_generation")
        normalized_items = _normalize_items(items)
        normalized_relationships = _normalize_relationships(relationships, {row["item_code"] for row in normalized_items})
        manifest_id = str(continuity_manifest_id or "").lower().strip()
        manifest_digest = str(continuity_manifest_digest or "").lower().strip()
        if bool(manifest_id) != bool(manifest_digest):
            raise ValueError("continuity_manifest_lineage_incomplete")
        if manifest_id:
            from long_running_multi_day_session_continuity import load_session_continuity_manifest
            manifest = load_session_continuity_manifest(manifest_id, runtime_root=runtime_root)
            if not manifest.get("ok") or manifest.get("continuity_manifest_record_digest") != _hex(manifest_digest, "invalid_continuity_manifest_digest"):
                raise ValueError("stale_or_mismatched_continuity_manifest")
            if manifest.get("project_id") != project:
                raise ValueError("cross_project_continuity_manifest")
        previous_id = str(previous_snapshot_id or "").lower().strip()
        previous_digest = str(previous_snapshot_digest or "").lower().strip()
        review_id = str(accepted_review_id or "").lower().strip()
        review_digest = str(accepted_review_digest or "").lower().strip()
        lineage_values = (previous_id, previous_digest, review_id, review_digest)
        if gen == 1:
            if any(lineage_values):
                raise ValueError("initial_snapshot_cannot_have_revision_lineage")
        else:
            if not all(lineage_values):
                raise ValueError("revised_snapshot_requires_exact_review_lineage")
            if not _SNAPSHOT.fullmatch(previous_id) or not _REVIEW.fullmatch(review_id):
                raise ValueError("invalid_revision_lineage_id")
            previous = load_project_understanding_snapshot(previous_id, runtime_root=runtime_root)
            review = load_project_understanding_review(review_id, runtime_root=runtime_root)
            if not previous.get("ok") or previous.get("project_understanding_snapshot_digest") != _hex(previous_digest, "invalid_previous_snapshot_digest"):
                raise ValueError("stale_or_mismatched_previous_snapshot")
            if previous.get("project_id") != project or previous.get("project_identity_digest") != identity_digest:
                raise ValueError("cross_project_snapshot_revision")
            if int(previous.get("generation") or 0) + 1 != gen:
                raise ValueError("nonsequential_snapshot_generation")
            if not review.get("ok") or review.get("project_understanding_review_digest") != _hex(review_digest, "invalid_review_digest"):
                raise ValueError("stale_or_mismatched_review")
            if review.get("project_id") != project or review.get("snapshot_id") != previous_id:
                raise ValueError("cross_project_review_lineage")
            if review.get("disposition") != "accept_update":
                raise ValueError("accepted_update_review_required")
        type_counts = {kind: 0 for kind in ITEM_TYPES}
        for item in normalized_items:
            type_counts[item["item_type"]] += 1
        identity = {
            "project_id": project,
            "project_identity_digest": identity_digest,
            "repository_fingerprint_digest": fingerprint,
            "source_session_id": session,
            "source_session_digest": session_digest,
            "logical_day": day,
            "generation": gen,
            "items": normalized_items,
            "relationships": normalized_relationships,
            "continuity_manifest_id": manifest_id,
            "continuity_manifest_digest": manifest_digest,
            "previous_snapshot_id": previous_id,
            "previous_snapshot_digest": previous_digest,
            "accepted_review_id": review_id,
            "accepted_review_digest": review_digest,
        }
        snapshot_id = "project_understanding_snapshot_" + _digest(identity)[:24]
        row = _sealed({
            "ok": True,
            "status": "project_understanding_snapshot_prepared",
            "snapshot_id": snapshot_id,
            **identity,
            "item_count": len(normalized_items),
            "relationship_count": len(normalized_relationships),
            "item_type_counts": type_counts,
            "initial_snapshot": gen == 1,
            "operator_review_bound_revision": gen > 1,
            "current_truth_not_asserted": True,
            **_base(),
        }, "project_understanding_snapshot_digest")
        with _lock(runtime_root):
            path = _path("project_understanding_snapshots", snapshot_id, runtime_root)
            current = _read_json(path)
            if current:
                return current if _valid(current, "project_understanding_snapshot_digest") else _failure("project_understanding_snapshot_tampered", "existing_snapshot_tampered")
            _atomic_json(path, row)
        return row
    except Exception as exc:
        return _failure("project_understanding_snapshot_blocked", str(exc))


def load_project_understanding_snapshot(snapshot_id: str, *, runtime_root=None) -> dict[str, Any]:
    token = str(snapshot_id or "").lower().strip()
    if not _SNAPSHOT.fullmatch(token):
        return _failure("project_understanding_snapshot_not_found", "invalid_snapshot_id")
    row = _read_json(_path("project_understanding_snapshots", token, runtime_root))
    if not row:
        return _failure("project_understanding_snapshot_not_found", "snapshot_missing")
    return row if _valid(row, "project_understanding_snapshot_digest") else _failure("project_understanding_snapshot_tampered", "snapshot_digest_mismatch")


def _normalize_observations(observations: Iterable[Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for raw in observations or []:
        if not isinstance(raw, Mapping):
            raise ValueError("observation_mapping_required")
        code = _token(raw.get("item_code"), "invalid_observation_item_code")
        if code in rows:
            raise ValueError("duplicate_observation_item_code")
        state = _token(raw.get("observation_state"), "invalid_observation_state")
        if state not in OBSERVATION_STATES:
            raise ValueError("unsupported_observation_state")
        rows[code] = {
            "item_code": code,
            "observation_state": state,
            "statement_digest": _hex(raw.get("statement_digest"), "invalid_observed_statement_digest", allow_empty=True),
            "evidence_digest": _hex(raw.get("evidence_digest"), "invalid_observed_evidence_digest", allow_empty=True),
            "confidence": _token(raw.get("confidence"), "invalid_observed_confidence") if raw.get("confidence") else "",
        }
        if rows[code]["confidence"] and rows[code]["confidence"] not in CONFIDENCE_LEVELS:
            raise ValueError("unsupported_observed_confidence")
    return rows


def prepare_project_understanding_reconciliation(
    snapshot_id: str,
    *,
    expected_snapshot_digest: str,
    project_id: str,
    project_identity_digest: str,
    repository_fingerprint_digest: str,
    current_session_id: str,
    current_session_digest: str,
    current_logical_day: int,
    scan_evidence_digest: str,
    observations: Iterable[Mapping[str, Any]],
    partial_scan: bool = False,
    runtime_root=None,
) -> dict[str, Any]:
    try:
        sid = str(snapshot_id or "").lower().strip()
        if not _SNAPSHOT.fullmatch(sid):
            raise ValueError("invalid_snapshot_id")
        snapshot = load_project_understanding_snapshot(sid, runtime_root=runtime_root)
        if not snapshot.get("ok") or snapshot.get("project_understanding_snapshot_digest") != _hex(expected_snapshot_digest, "invalid_expected_snapshot_digest"):
            raise ValueError("stale_or_mismatched_snapshot")
        project = _token(project_id, "invalid_project_id", pattern=_PROJECT)
        if snapshot.get("project_id") != project:
            raise ValueError("cross_project_snapshot")
        identity_digest = _hex(project_identity_digest, "invalid_project_identity_digest")
        fingerprint = _hex(repository_fingerprint_digest, "invalid_repository_fingerprint_digest")
        if snapshot.get("project_identity_digest") != identity_digest:
            raise ValueError("project_identity_mismatch")
        if snapshot.get("repository_fingerprint_digest") != fingerprint:
            raise ValueError("repository_fingerprint_mismatch")
        session = _token(current_session_id, "invalid_current_session_id", pattern=_SESSION)
        session_digest = _hex(current_session_digest, "invalid_current_session_digest")
        day = int(current_logical_day)
        if day < int(snapshot.get("logical_day") or 0):
            raise ValueError("logical_clock_reversal")
        scan_digest = _hex(scan_evidence_digest, "invalid_scan_evidence_digest")
        observed = _normalize_observations(observations)
        snapshot_items = {row["item_code"]: row for row in snapshot.get("items") or []}
        unknown = sorted(set(observed) - set(snapshot_items))
        if unknown:
            raise ValueError("observation_not_in_snapshot")
        classifications: list[dict[str, Any]] = []
        counts = {name: 0 for name in CLASSIFICATIONS}
        proposed_updates: list[str] = []
        unresolved: list[str] = []
        for code, item in sorted(snapshot_items.items()):
            obs = observed.get(code)
            if obs is None:
                classification = "unverified" if partial_scan else "missing"
                observed_state = "unverified" if partial_scan else "missing"
                observed_statement = ""
                observed_evidence = ""
                observed_confidence = ""
            else:
                observed_state = obs["observation_state"]
                observed_statement = obs["statement_digest"]
                observed_evidence = obs["evidence_digest"]
                observed_confidence = obs["confidence"]
                if observed_state == "present":
                    evidence_matches = not observed_evidence or observed_evidence in set(item.get("evidence_digests") or [])
                    statement_matches = not observed_statement or observed_statement == item.get("statement_digest")
                    expired = day - int(item.get("last_verified_day") or 0) > int(item.get("freshness_window_days") or 0)
                    classification = "stale" if expired else ("still_valid" if evidence_matches and statement_matches else "changed")
                elif observed_state == "changed":
                    classification = "changed"
                elif observed_state == "contradictory":
                    classification = "contradicted"
                else:
                    classification = observed_state
            counts[classification] += 1
            if classification in {"changed", "missing", "stale", "superseded"}:
                proposed_updates.append(code)
            if classification in {"contradicted", "unverified"}:
                unresolved.append(code)
            classifications.append({
                "item_code": code,
                "item_type": item.get("item_type"),
                "classification": classification,
                "prior_statement_digest": item.get("statement_digest"),
                "prior_evidence_digest": _digest(item.get("evidence_digests") or []),
                "observed_state": observed_state,
                "observed_statement_digest": observed_statement,
                "observed_evidence_digest": observed_evidence,
                "observed_confidence": observed_confidence,
                "prior_confidence": item.get("confidence"),
                "last_verified_day": item.get("last_verified_day"),
                "freshness_window_days": item.get("freshness_window_days"),
            })
        identity = {
            "snapshot_id": sid,
            "snapshot_digest": snapshot.get("project_understanding_snapshot_digest"),
            "project_id": project,
            "project_identity_digest": identity_digest,
            "repository_fingerprint_digest": fingerprint,
            "source_session_id": snapshot.get("source_session_id"),
            "current_session_id": session,
            "current_session_digest": session_digest,
            "current_logical_day": day,
            "scan_evidence_digest": scan_digest,
            "partial_scan": bool(partial_scan),
            "classifications": classifications,
        }
        reconciliation_id = "project_understanding_reconciliation_" + _digest(identity)[:24]
        row = _sealed({
            "ok": True,
            "status": "project_understanding_reconciliation_prepared",
            "reconciliation_id": reconciliation_id,
            **identity,
            "cross_session": session != snapshot.get("source_session_id"),
            "classification_counts": counts,
            "still_valid_count": counts["still_valid"],
            "changed_count": counts["changed"],
            "contradicted_count": counts["contradicted"],
            "missing_count": counts["missing"],
            "stale_count": counts["stale"],
            "unverified_count": counts["unverified"],
            "superseded_count": counts["superseded"],
            "proposed_update_codes": sorted(proposed_updates),
            "unresolved_codes": sorted(unresolved),
            "operator_review_required": bool(proposed_updates or unresolved),
            "prior_snapshot_unchanged": True,
            "current_truth_not_asserted": True,
            **_base(),
        }, "project_understanding_reconciliation_digest")
        with _lock(runtime_root):
            path = _path("project_understanding_reconciliations", reconciliation_id, runtime_root)
            current = _read_json(path)
            if current:
                return current if _valid(current, "project_understanding_reconciliation_digest") else _failure("project_understanding_reconciliation_tampered", "existing_reconciliation_tampered")
            _atomic_json(path, row)
        return row
    except Exception as exc:
        return _failure("project_understanding_reconciliation_blocked", str(exc))


def load_project_understanding_reconciliation(reconciliation_id: str, *, runtime_root=None) -> dict[str, Any]:
    token = str(reconciliation_id or "").lower().strip()
    if not _RECONCILIATION.fullmatch(token):
        return _failure("project_understanding_reconciliation_not_found", "invalid_reconciliation_id")
    row = _read_json(_path("project_understanding_reconciliations", token, runtime_root))
    if not row:
        return _failure("project_understanding_reconciliation_not_found", "reconciliation_missing")
    return row if _valid(row, "project_understanding_reconciliation_digest") else _failure("project_understanding_reconciliation_tampered", "reconciliation_digest_mismatch")


def review_project_understanding_reconciliation(
    reconciliation_id: str,
    *,
    expected_reconciliation_digest: str,
    disposition: str,
    exact_phrase: str,
    runtime_root=None,
) -> dict[str, Any]:
    try:
        rid = str(reconciliation_id or "").lower().strip()
        if not _RECONCILIATION.fullmatch(rid):
            raise ValueError("invalid_reconciliation_id")
        reconciliation = load_project_understanding_reconciliation(rid, runtime_root=runtime_root)
        expected = _hex(expected_reconciliation_digest, "invalid_expected_reconciliation_digest")
        if not reconciliation.get("ok") or reconciliation.get("project_understanding_reconciliation_digest") != expected:
            raise ValueError("stale_or_mismatched_reconciliation")
        decision = _token(disposition, "invalid_review_disposition")
        if decision not in REVIEW_DISPOSITIONS:
            raise ValueError("unsupported_review_disposition")
        phrase = str(exact_phrase or "").strip()
        required = f"review project understanding {decision} for reconciliation {rid} digest {expected}"
        if phrase.lower().rstrip(".!?") != required:
            raise ValueError("exact_review_phrase_required")
        accepted = decision == "accept_update"
        identity = {
            "reconciliation_id": rid,
            "reconciliation_digest": expected,
            "snapshot_id": reconciliation.get("snapshot_id"),
            "project_id": reconciliation.get("project_id"),
            "disposition": decision,
            "update_interpretation_accepted": accepted,
        }
        review_id = "project_understanding_review_" + _digest(identity)[:24]
        row = _sealed({
            "ok": True,
            "status": "project_understanding_review_recorded",
            "review_id": review_id,
            **identity,
            "operator_follow_up_required": decision in {"hold", "request_changes"},
            "new_snapshot_not_created": True,
            "project_understanding_not_current_truth": True,
            "contradictions_not_resolved": True,
            **_base(),
        }, "project_understanding_review_digest")
        with _lock(runtime_root):
            path = _path("project_understanding_reviews", review_id, runtime_root)
            current = _read_json(path)
            if current:
                return current if _valid(current, "project_understanding_review_digest") else _failure("project_understanding_review_tampered", "existing_review_tampered")
            _atomic_json(path, row)
        return row
    except Exception as exc:
        return _failure("project_understanding_review_blocked", str(exc))


def load_project_understanding_review(review_id: str, *, runtime_root=None) -> dict[str, Any]:
    token = str(review_id or "").lower().strip()
    if not _REVIEW.fullmatch(token):
        return _failure("project_understanding_review_not_found", "invalid_review_id")
    row = _read_json(_path("project_understanding_reviews", token, runtime_root))
    if not row:
        return _failure("project_understanding_review_not_found", "review_missing")
    return row if _valid(row, "project_understanding_review_digest") else _failure("project_understanding_review_tampered", "review_digest_mismatch")


def _public_list(directory: str, seal_field: str, keys: Iterable[str], plural: str, runtime_root=None) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    root = _dir(directory, runtime_root)
    for path in sorted(root.glob("*.json")) if root.exists() else []:
        row = _read_json(path)
        if row and _valid(row, seal_field):
            rows.append({key: row.get(key) for key in keys})
    rows = rows[-MAX_RECORDS:]
    result = {"ok": True, "status": f"{plural}_ready", plural: rows, "count": len(rows), "read_only": True, **_base()}
    result[f"{plural}_digest"] = _digest(rows)
    return result


def public_project_understanding_snapshots(*, runtime_root=None) -> dict[str, Any]:
    return _public_list("project_understanding_snapshots", "project_understanding_snapshot_digest", ("snapshot_id", "project_id", "source_session_id", "logical_day", "generation", "item_count", "relationship_count", "project_understanding_snapshot_digest"), "project_understanding_snapshots", runtime_root)


def public_project_understanding_reconciliations(*, runtime_root=None) -> dict[str, Any]:
    return _public_list("project_understanding_reconciliations", "project_understanding_reconciliation_digest", ("reconciliation_id", "snapshot_id", "project_id", "source_session_id", "current_session_id", "cross_session", "still_valid_count", "changed_count", "contradicted_count", "missing_count", "stale_count", "unverified_count", "superseded_count", "operator_review_required", "project_understanding_reconciliation_digest"), "project_understanding_reconciliations", runtime_root)


def public_project_understanding_reviews(*, runtime_root=None) -> dict[str, Any]:
    return _public_list("project_understanding_reviews", "project_understanding_review_digest", ("review_id", "reconciliation_id", "snapshot_id", "project_id", "disposition", "update_interpretation_accepted", "project_understanding_review_digest"), "project_understanding_reviews", runtime_root)


def project_understanding_dashboard_record(*, runtime_root=None) -> dict[str, Any]:
    snapshots = public_project_understanding_snapshots(runtime_root=runtime_root)
    reconciliations = public_project_understanding_reconciliations(runtime_root=runtime_root)
    reviews = public_project_understanding_reviews(runtime_root=runtime_root)
    row = {
        "ok": True,
        "status": "cross_session_project_understanding_dashboard_ready",
        "read_only": True,
        "get_only": True,
        "snapshot_count": snapshots["count"],
        "reconciliation_count": reconciliations["count"],
        "review_count": reviews["count"],
        "project_understanding_snapshots": snapshots["project_understanding_snapshots"],
        "project_understanding_reconciliations": reconciliations["project_understanding_reconciliations"],
        "project_understanding_reviews": reviews["project_understanding_reviews"],
        **_base(),
    }
    row["dashboard_digest"] = _digest({key: value for key, value in row.items() if key != "dashboard_digest"})
    return row


def render_project_understanding_dashboard_html(*, runtime_root=None) -> str:
    row = project_understanding_dashboard_record(runtime_root=runtime_root)
    return (
        "<!doctype html><html><head><meta charset='utf-8'><title>Cross-Session Project Understanding</title>"
        "<style>body{font-family:system-ui;background:#111827;color:#e5e7eb;margin:0;padding:28px}.card{background:#1f2937;border:1px solid #374151;border-radius:12px;padding:18px;max-width:980px;margin:auto}h1{margin-top:0}.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}.metric{background:#111827;padding:14px;border-radius:8px}.muted{color:#9ca3af}</style></head><body><div class='card'>"
        "<h1>Cross-Session Project Understanding</h1><p class='muted'>GET-only inspection. Remembered state is evidence to revalidate, never current truth or execution authority.</p>"
        f"<div class='grid'><div class='metric'>Snapshots<br><b>{html.escape(str(row['snapshot_count']))}</b></div>"
        f"<div class='metric'>Reconciliations<br><b>{html.escape(str(row['reconciliation_count']))}</b></div>"
        f"<div class='metric'>Reviews<br><b>{html.escape(str(row['review_count']))}</b></div></div>"
        "<p>Every later session must revalidate project identity, repository fingerprint, evidence freshness, contradictions, and missing components before relying on prior understanding.</p>"
        "</div></body></html>"
    )


def project_understanding_response(row: Mapping[str, Any]) -> str:
    status = str(row.get("status") or "")
    if not row.get("ok"):
        return f"Project understanding control was blocked: {row.get('reason') or status}. No project or cognition state changed and no authority was created."
    if status.endswith("registry_ready"):
        return "The cross-session project understanding registry is ready for read-only inspection."
    if status.endswith("review_recorded"):
        return f"Recorded project understanding review {row.get('review_id')} as {row.get('disposition')}. No snapshot, project, cognition, or execution authority was created."
    return "Project understanding evidence is ready for read-only inspection. Remembered state was not accepted as current truth."


def process_project_understanding_control(user_text: str, *, runtime_root=None) -> dict[str, Any]:
    text = str(user_text or "").strip()
    row: dict[str, Any] | None = None
    if _SHOW_REGISTRY.fullmatch(text):
        row = cross_session_project_understanding_registry()
    elif _SHOW_SNAPSHOTS.fullmatch(text):
        row = public_project_understanding_snapshots(runtime_root=runtime_root)
    elif _SHOW_RECONCILIATIONS.fullmatch(text):
        row = public_project_understanding_reconciliations(runtime_root=runtime_root)
    elif _SHOW_REVIEWS.fullmatch(text):
        row = public_project_understanding_reviews(runtime_root=runtime_root)
    else:
        match = _REVIEW_RECONCILIATION.fullmatch(text)
        if match:
            row = review_project_understanding_reconciliation(
                match.group("reconciliation"),
                expected_reconciliation_digest=match.group("digest"),
                disposition=match.group("decision").lower(),
                exact_phrase=text,
                runtime_root=runtime_root,
            )
    if row is None:
        return {"active": False}
    return {"active": True, "project_understanding": row, "response": project_understanding_response(row), "action_taken": False, "execution_started": False}


def build_cross_session_project_understanding_contract() -> dict[str, Any]:
    row = {
        "ok": True,
        "status": "cross_session_project_understanding_contract_ready",
        "milestone_name": MILESTONE_NAME,
        "roadmap_path": ROADMAP_PATH,
        "durable_project_summaries": True,
        "architecture_components_and_relationships": True,
        "decisions_risks_work_and_questions": True,
        "confidence_provenance_and_freshness": True,
        "immutable_revision_lineage": True,
        "cross_session_reconciliation": True,
        "seven_classification_states": True,
        "project_identity_and_repository_fingerprint_bound": True,
        "copied_repository_confusion_fails_closed": True,
        "partial_scan_preserves_unverified_state": True,
        "contradictions_remain_unresolved": True,
        "accepted_review_does_not_create_snapshot": True,
        "revised_snapshot_requires_exact_accepted_review": True,
        "remembered_state_never_current_without_revalidation": True,
        "operator_review_is_interpretation_only": True,
        "runtime_records_external": True,
        **_base(),
    }
    row["contract_digest"] = _digest(row)
    return row
