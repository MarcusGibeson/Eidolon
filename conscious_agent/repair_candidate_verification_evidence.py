from __future__ import annotations

"""v1090.3 deterministic operator-supplied candidate verification evidence.

Evidence is recorded explicitly inside an existing immutable candidate record.
The module never executes a test, opens an artifact, invokes a provider, creates
work, applies a patch, or grants protected authority. Private notes remain in
external finding runtime data and public evidence exposes only digests.
"""

from datetime import datetime, timezone
from typing import Any, Mapping
import hashlib
import json
import re
import uuid

from conversation_evaluation_finding import EvaluationFindingError, mutate_evaluation_finding
from repair_candidate_registration import load_registered_repair_candidate_private

REPAIR_CANDIDATE_VERIFICATION_SCHEMA_VERSION = "1"
VERIFICATION_EVIDENCE_KINDS = (
    "focused_suite",
    "current_stack",
    "core_profile",
    "full_profile",
    "fresh_package",
    "preflight",
    "privacy_scan",
    "manual_review",
)
VERIFICATION_RESULTS = ("pass", "fail", "inconclusive")
MAX_VERIFICATION_EVIDENCE_PER_CANDIDATE = 32
MAX_VERIFICATION_NOTE_CHARS = 2000
_SHA256_RE = re.compile(r"^[a-fA-F0-9]{64}$")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    ).hexdigest()


def _sha(value: str, label: str, *, required: bool = False) -> str:
    token = str(value or "").strip().upper()
    if required and not token:
        raise EvaluationFindingError(f"{label} is required.")
    if token and not _SHA256_RE.fullmatch(token):
        raise EvaluationFindingError(f"{label} must be a SHA-256 hexadecimal digest.")
    return token


def _note(value: str) -> str:
    token = str(value or "").strip()
    if len(token) > MAX_VERIFICATION_NOTE_CHARS:
        raise EvaluationFindingError(
            f"Candidate verification note exceeds the {MAX_VERIFICATION_NOTE_CHARS}-character limit."
        )
    return token


def _count(value: int | str | None, label: str) -> int:
    try:
        result = int(value or 0)
    except (TypeError, ValueError) as error:
        raise EvaluationFindingError(f"{label} must be an integer.") from error
    if result < 0:
        raise EvaluationFindingError(f"{label} cannot be negative.")
    return result


def _public_evidence(row: Mapping[str, Any]) -> dict[str, Any]:
    note = str(row.get("private_note") or "")
    return {
        "verification_evidence_id": str(row.get("verification_evidence_id") or ""),
        "evidence_kind": str(row.get("evidence_kind") or ""),
        "result": str(row.get("result") or "inconclusive"),
        "evidence_digest": str(row.get("evidence_digest") or ""),
        "artifact_sha256": str(row.get("artifact_sha256") or ""),
        "source_manifest_sha256": str(row.get("source_manifest_sha256") or ""),
        "passed_checks": max(0, int(row.get("passed_checks") or 0)),
        "total_checks": max(0, int(row.get("total_checks") or 0)),
        "suite_count": max(0, int(row.get("suite_count") or 0)),
        "source_tree_unchanged": bool(row.get("source_tree_unchanged")),
        "recorded_at": str(row.get("recorded_at") or ""),
        "private_note_present": bool(note),
        "private_note_digest": _digest(note) if note else "",
        "private_note_returned": False,
    }


def build_repair_candidate_verification_evidence(finding_id: str, candidate_id: str) -> dict[str, Any]:
    finding, candidate = load_registered_repair_candidate_private(finding_id, candidate_id)
    rows = [
        _public_evidence(row)
        for row in list(candidate.get("verification_evidence") or ())
        if isinstance(row, Mapping)
    ]
    result_counts = {result: 0 for result in VERIFICATION_RESULTS}
    kind_counts = {kind: 0 for kind in VERIFICATION_EVIDENCE_KINDS}
    total_passed_checks = total_checks = total_suites = 0
    for row in rows:
        result_counts[row["result"]] = result_counts.get(row["result"], 0) + 1
        kind_counts[row["evidence_kind"]] = kind_counts.get(row["evidence_kind"], 0) + 1
        total_passed_checks += row["passed_checks"]
        total_checks += row["total_checks"]
        total_suites += row["suite_count"]
    stable = {
        "finding_id": str(finding.get("finding_id") or ""),
        "finding_revision": max(0, int(finding.get("revision") or 0)),
        "candidate_id": str(candidate.get("candidate_id") or ""),
        "candidate_kind": str(candidate.get("candidate_kind") or ""),
        "artifact_sha256": str(candidate.get("artifact_sha256") or ""),
        "source_manifest_sha256": str(candidate.get("source_manifest_sha256") or ""),
        "verification_evidence_count": len(rows),
        "maximum_verification_evidence": MAX_VERIFICATION_EVIDENCE_PER_CANDIDATE,
        "result_counts": result_counts,
        "evidence_kind_counts": kind_counts,
        "total_passed_checks": total_passed_checks,
        "total_checks": total_checks,
        "total_suite_count": total_suites,
        "verification_evidence": rows,
    }
    return {
        "ok": True,
        "type": "desktop_alpha_repair_candidate_verification_evidence",
        "schema_version": REPAIR_CANDIDATE_VERIFICATION_SCHEMA_VERSION,
        **stable,
        "verification_evidence_digest": _digest(stable),
        "artifact_identity_bound": True,
        "operator_confirmation_required": True,
        "optimistic_revision_required": True,
        "private_notes_returned": False,
        "automatic_test_execution": False,
        "automatic_task_created": False,
        "automatic_work_item_created": False,
        "autonomous_prioritization": False,
        "candidate_ranked": False,
        "winner_selected": False,
        "patch_generated": False,
        "patch_applied": False,
        "approval_granted": False,
        "rollback_authorized": False,
        "installation_performed": False,
        "promotion_performed": False,
        "release_recommendation_produced": False,
        "release_certified": False,
        "provider_invoked": False,
        "writes_state": False,
        "content_free": True,
        "redacted": True,
    }


def record_repair_candidate_verification_evidence(
    finding_id: str,
    candidate_id: str,
    *,
    evidence_kind: str,
    result: str,
    evidence_digest: str,
    passed_checks: int | str = 0,
    total_checks: int | str = 0,
    suite_count: int | str = 0,
    source_tree_unchanged: bool = False,
    note: str = "",
    expected_revision: int | None,
    operator_confirmed: bool,
) -> dict[str, Any]:
    kind = str(evidence_kind or "").strip().lower()
    result_token = str(result or "").strip().lower()
    if kind not in VERIFICATION_EVIDENCE_KINDS:
        raise EvaluationFindingError("Unsupported repair candidate verification evidence kind.")
    if result_token not in VERIFICATION_RESULTS:
        raise EvaluationFindingError("Unsupported repair candidate verification result.")
    evidence = _sha(evidence_digest, "Verification evidence digest", required=True)
    passed = _count(passed_checks, "passed_checks")
    total = _count(total_checks, "total_checks")
    suites = _count(suite_count, "suite_count")
    if passed > total:
        raise EvaluationFindingError("passed_checks cannot exceed total_checks.")
    unchanged = bool(source_tree_unchanged)
    if result_token == "pass" and (total <= 0 or passed != total or not unchanged):
        raise EvaluationFindingError(
            "Passing verification evidence requires a positive all-pass check total and an unchanged source tree."
        )
    if result_token == "fail" and total > 0 and passed == total and unchanged:
        raise EvaluationFindingError("Failing verification evidence must contain a failed check or source mutation.")
    private_note = _note(note)

    class _Idempotent(Exception):
        pass

    def apply(record: dict[str, Any]) -> None:
        candidates = [
            dict(row)
            for row in list(record.get("repair_candidate_review_records") or ())
            if isinstance(row, Mapping)
        ]
        candidate = next(
            (row for row in candidates if str(row.get("candidate_id") or "") == str(candidate_id or "")),
            None,
        )
        if candidate is None:
            raise EvaluationFindingError("Repair candidate registration not found.")
        rows = [
            dict(row)
            for row in list(candidate.get("verification_evidence") or ())
            if isinstance(row, Mapping)
        ]
        signature = (kind, result_token, evidence, passed, total, suites, unchanged, private_note)
        for row in rows:
            if (
                row.get("evidence_kind"),
                row.get("result"),
                row.get("evidence_digest"),
                int(row.get("passed_checks") or 0),
                int(row.get("total_checks") or 0),
                int(row.get("suite_count") or 0),
                bool(row.get("source_tree_unchanged")),
                row.get("private_note"),
            ) == signature:
                raise _Idempotent
        if len(rows) >= MAX_VERIFICATION_EVIDENCE_PER_CANDIDATE:
            raise EvaluationFindingError("The repair candidate has reached the verification-evidence limit.")
        rows.append(
            {
                "verification_evidence_id": f"candidate_verification_{uuid.uuid4().hex[:16]}",
                "evidence_kind": kind,
                "result": result_token,
                "evidence_digest": evidence,
                "artifact_sha256": str(candidate.get("artifact_sha256") or ""),
                "source_manifest_sha256": str(candidate.get("source_manifest_sha256") or ""),
                "passed_checks": passed,
                "total_checks": total,
                "suite_count": suites,
                "source_tree_unchanged": unchanged,
                "private_note": private_note,
                "recorded_at": _now(),
            }
        )
        candidate["verification_evidence"] = rows
        candidate["updated_at"] = _now()
        record["repair_candidate_review_records"] = candidates

    try:
        mutate_evaluation_finding(
            finding_id,
            expected_revision=expected_revision,
            operator_confirmed=operator_confirmed,
            mutator=apply,
        )
    except _Idempotent:
        response = build_repair_candidate_verification_evidence(finding_id, candidate_id)
        response["duplicate_verification_evidence"] = True
        return response
    response = build_repair_candidate_verification_evidence(finding_id, candidate_id)
    response["duplicate_verification_evidence"] = False
    return response


def repair_candidate_verification_evidence_contains_private_fields(value: Mapping[str, Any] | None) -> bool:
    forbidden = {
        "private_note", "note", "notes", "private_label", "private_reference", "content", "text",
        "transcript", "prompt", "provider_payload", "credentials", "vectors", "hidden_reasoning",
        "chain_of_thought",
    }
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
