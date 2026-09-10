from __future__ import annotations

"""v1090.1 immutable registration of operator-supplied repair candidates."""

from datetime import datetime, timezone
from typing import Any, Mapping
import hashlib
import json
import re
import uuid

from conversation_evaluation_finding import EvaluationFindingError, load_evaluation_finding_private, mutate_evaluation_finding
from conversation_evaluation_finding_reproducibility import build_finding_reproducibility
from repair_candidate_review_protocol import (
    MAX_CANDIDATE_LABEL_CHARS,
    MAX_CANDIDATE_REFERENCE_CHARS,
    MAX_REPAIR_CANDIDATES_PER_FINDING,
    REPAIR_CANDIDATE_KINDS,
)

REPAIR_CANDIDATE_REGISTRATION_SCHEMA_VERSION = "1"
_CANDIDATE_ID_RE = re.compile(r"^repair_candidate_[a-f0-9]{16}$")
_SHA256_RE = re.compile(r"^[a-fA-F0-9]{64}$")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()).hexdigest()


def _sha(value: str, label: str, *, required: bool = False) -> str:
    token = str(value or "").strip().upper()
    if required and not token:
        raise EvaluationFindingError(f"{label} is required.")
    if token and not _SHA256_RE.fullmatch(token):
        raise EvaluationFindingError(f"{label} must be a SHA-256 hexadecimal digest.")
    return token


def _bounded(value: str, maximum: int, label: str) -> str:
    token = str(value or "").strip()
    if len(token) > maximum:
        raise EvaluationFindingError(f"{label} exceeds the {maximum}-character limit.")
    return token


def _candidate_id(value: str) -> str:
    token = str(value or "").strip()
    if not _CANDIDATE_ID_RE.fullmatch(token):
        raise EvaluationFindingError("Invalid repair candidate identifier.")
    return token


def _rows(record: Mapping[str, Any]) -> list[dict[str, Any]]:
    return [dict(row) for row in list(record.get("repair_candidate_review_records") or ()) if isinstance(row, Mapping)]


def _public(row: Mapping[str, Any]) -> dict[str, Any]:
    label = str(row.get("private_label") or "")
    reference = str(row.get("private_reference") or "")
    events = [event for event in list(row.get("review_events") or ()) if isinstance(event, Mapping)]
    return {
        "candidate_id": str(row.get("candidate_id") or ""),
        "candidate_kind": str(row.get("candidate_kind") or ""),
        "artifact_sha256": str(row.get("artifact_sha256") or ""),
        "source_manifest_sha256": str(row.get("source_manifest_sha256") or ""),
        "evidence_digest": str(row.get("evidence_digest") or ""),
        "finding_id": str(row.get("finding_id") or ""),
        "review_state": str(row.get("review_state") or "registered"),
        "registered_at": str(row.get("registered_at") or ""),
        "updated_at": str(row.get("updated_at") or ""),
        "reproducibility_status_at_registration": str(row.get("reproducibility_status_at_registration") or "not_reviewed"),
        "private_label_present": bool(label),
        "private_label_digest": _digest(label) if label else "",
        "private_reference_present": bool(reference),
        "private_reference_digest": _digest(reference) if reference else "",
        "review_event_count": len(events),
        "review_events_digest": _digest(events),
        "private_label_returned": False,
        "private_reference_returned": False,
    }


def build_repair_candidate_registrations(finding_id: str) -> dict[str, Any]:
    finding = load_evaluation_finding_private(finding_id)
    public = [_public(row) for row in _rows(finding)]
    stable = {
        "finding_id": str(finding.get("finding_id") or ""),
        "finding_revision": max(0, int(finding.get("revision") or 0)),
        "candidate_count": len(public),
        "maximum_candidates": MAX_REPAIR_CANDIDATES_PER_FINDING,
        "candidates": public,
    }
    return {
        "ok": True,
        "type": "desktop_alpha_repair_candidate_registrations",
        "schema_version": REPAIR_CANDIDATE_REGISTRATION_SCHEMA_VERSION,
        **stable,
        "registrations_digest": _digest(stable),
        "immutable_artifact_identity": True,
        "operator_confirmation_required": True,
        "optimistic_revision_required": True,
        "private_labels_returned": False,
        "private_references_returned": False,
        "candidate_generated": False,
        "automatic_task_created": False,
        "automatic_work_item_created": False,
        "autonomous_prioritization": False,
        "patch_generated": False,
        "patch_applied": False,
        "approval_granted": False,
        "rollback_authorized": False,
        "installation_performed": False,
        "promotion_performed": False,
        "release_certified": False,
        "provider_invoked": False,
        "writes_state": False,
        "content_free": True,
        "redacted": True,
    }


def register_repair_candidate(
    finding_id: str,
    *,
    candidate_kind: str,
    artifact_sha256: str,
    source_manifest_sha256: str = "",
    evidence_digest: str = "",
    label: str = "",
    private_reference: str = "",
    expected_revision: int | None,
    operator_confirmed: bool,
) -> dict[str, Any]:
    kind = str(candidate_kind or "").strip().lower()
    if kind not in REPAIR_CANDIDATE_KINDS:
        raise EvaluationFindingError("Unsupported repair candidate kind.")
    artifact = _sha(artifact_sha256, "Artifact SHA-256", required=True)
    manifest = _sha(source_manifest_sha256, "Source manifest SHA-256")
    evidence = _sha(evidence_digest, "Evidence digest")
    private_label = _bounded(label, MAX_CANDIDATE_LABEL_CHARS, "Candidate label")
    reference = _bounded(private_reference, MAX_CANDIDATE_REFERENCE_CHARS, "Candidate reference")
    reproducibility = build_finding_reproducibility(finding_id)

    class _Idempotent(Exception):
        pass

    duplicate = {"value": False}

    def apply(record: dict[str, Any]) -> None:
        rows = _rows(record)
        for row in rows:
            if str(row.get("candidate_kind") or "") == kind and str(row.get("artifact_sha256") or "") == artifact:
                duplicate["value"] = True
                raise _Idempotent
        if len(rows) >= MAX_REPAIR_CANDIDATES_PER_FINDING:
            raise EvaluationFindingError("The finding has reached the repair-candidate registration limit.")
        now = _now()
        rows.append({
            "candidate_id": f"repair_candidate_{uuid.uuid4().hex[:16]}",
            "candidate_kind": kind,
            "artifact_sha256": artifact,
            "source_manifest_sha256": manifest,
            "evidence_digest": evidence,
            "finding_id": str(record.get("finding_id") or ""),
            "private_label": private_label,
            "private_reference": reference,
            "review_state": "registered",
            "registered_at": now,
            "updated_at": now,
            "reproducibility_status_at_registration": str(reproducibility.get("reproducibility_status") or "not_reviewed"),
            "review_events": [],
        })
        record["repair_candidate_review_records"] = rows

    try:
        mutate_evaluation_finding(
            finding_id,
            expected_revision=expected_revision,
            operator_confirmed=operator_confirmed,
            mutator=apply,
        )
    except _Idempotent:
        result = build_repair_candidate_registrations(finding_id)
        result["duplicate_registration"] = True
        return result
    result = build_repair_candidate_registrations(finding_id)
    result["duplicate_registration"] = False
    return result


def load_registered_repair_candidate_private(finding_id: str, candidate_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
    token = _candidate_id(candidate_id)
    finding = load_evaluation_finding_private(finding_id)
    candidate = next((row for row in _rows(finding) if str(row.get("candidate_id") or "") == token), None)
    if candidate is None:
        raise EvaluationFindingError("Repair candidate registration not found.")
    return finding, candidate


def repair_candidate_registration_contains_private_fields(value: Mapping[str, Any] | None) -> bool:
    forbidden = {"private_label", "private_reference", "content", "text", "transcript", "prompt", "private_note", "provider_payload", "credentials", "vectors", "hidden_reasoning", "chain_of_thought"}
    stack: list[Any] = [value]
    while stack:
        current = stack.pop()
        if isinstance(current, Mapping):
            if forbidden & {str(key) for key in current}:
                return True
            stack.extend(current.values())
        elif isinstance(current, (list, tuple)):
            stack.extend(current)
    return False
