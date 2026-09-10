from __future__ import annotations

"""v1090.5 explicit immutable supersession and replacement lineage."""

from datetime import datetime, timezone
from typing import Any, Mapping
import hashlib
import json
import re
import uuid

from conversation_evaluation_finding import EvaluationFindingError, load_evaluation_finding_private, mutate_evaluation_finding

REPAIR_CANDIDATE_LINEAGE_SCHEMA_VERSION = "1"
REPAIR_CANDIDATE_LINEAGE_KINDS = ("supersedes", "replaces")
MAX_REPAIR_CANDIDATE_LINEAGE_EDGES = 24
MAX_LINEAGE_NOTE_CHARS = 2000
_SHA256_RE = re.compile(r"^[a-fA-F0-9]{64}$")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    ).hexdigest()


def _note(value: str) -> str:
    token = str(value or "").strip()
    if len(token) > MAX_LINEAGE_NOTE_CHARS:
        raise EvaluationFindingError(
            f"Repair candidate lineage note exceeds the {MAX_LINEAGE_NOTE_CHARS}-character limit."
        )
    return token


def _evidence(value: str) -> str:
    token = str(value or "").strip().upper()
    if token and not _SHA256_RE.fullmatch(token):
        raise EvaluationFindingError("Repair candidate lineage evidence must be a SHA-256 hexadecimal digest.")
    return token


def _public_edge(edge: Mapping[str, Any]) -> dict[str, Any]:
    note = str(edge.get("private_note") or "")
    return {
        "lineage_id": str(edge.get("lineage_id") or ""),
        "relation_kind": str(edge.get("relation_kind") or ""),
        "predecessor_candidate_id": str(edge.get("predecessor_candidate_id") or ""),
        "successor_candidate_id": str(edge.get("successor_candidate_id") or ""),
        "predecessor_artifact_sha256": str(edge.get("predecessor_artifact_sha256") or ""),
        "successor_artifact_sha256": str(edge.get("successor_artifact_sha256") or ""),
        "evidence_digest": str(edge.get("evidence_digest") or ""),
        "recorded_at": str(edge.get("recorded_at") or ""),
        "private_note_present": bool(note),
        "private_note_digest": _digest(note) if note else "",
        "private_note_returned": False,
    }


def build_repair_candidate_lineage(finding_id: str) -> dict[str, Any]:
    finding = load_evaluation_finding_private(finding_id)
    edges = [
        _public_edge(edge)
        for edge in list(finding.get("repair_candidate_lineage") or ())
        if isinstance(edge, Mapping)
    ]
    counts = {kind: 0 for kind in REPAIR_CANDIDATE_LINEAGE_KINDS}
    for edge in edges:
        counts[edge["relation_kind"]] = counts.get(edge["relation_kind"], 0) + 1
    stable = {
        "finding_id": str(finding.get("finding_id") or ""),
        "finding_revision": max(0, int(finding.get("revision") or 0)),
        "lineage_edge_count": len(edges),
        "maximum_lineage_edges": MAX_REPAIR_CANDIDATE_LINEAGE_EDGES,
        "relation_kind_counts": counts,
        "lineage_edges": edges,
    }
    return {
        "ok": True,
        "type": "desktop_alpha_repair_candidate_lineage",
        "schema_version": REPAIR_CANDIDATE_LINEAGE_SCHEMA_VERSION,
        **stable,
        "lineage_digest": _digest(stable),
        "historical_candidates_preserved": True,
        "lineage_edges_immutable": True,
        "operator_confirmation_required": True,
        "optimistic_revision_required": True,
        "private_notes_returned": False,
        "automatic_candidate_selection": False,
        "candidate_ranked": False,
        "winner_selected": False,
        "automatic_test_execution": False,
        "automatic_task_created": False,
        "automatic_work_item_created": False,
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


def _would_create_cycle(edges: list[dict[str, Any]], predecessor: str, successor: str) -> bool:
    adjacency: dict[str, set[str]] = {}
    for edge in edges:
        adjacency.setdefault(str(edge.get("predecessor_candidate_id") or ""), set()).add(
            str(edge.get("successor_candidate_id") or "")
        )
    adjacency.setdefault(predecessor, set()).add(successor)
    stack = [successor]
    seen: set[str] = set()
    while stack:
        current = stack.pop()
        if current == predecessor:
            return True
        if current in seen:
            continue
        seen.add(current)
        stack.extend(adjacency.get(current, set()))
    return False


def link_repair_candidate_lineage(
    finding_id: str,
    *,
    predecessor_candidate_id: str,
    successor_candidate_id: str,
    relation_kind: str,
    evidence_digest: str = "",
    note: str = "",
    expected_revision: int | None,
    operator_confirmed: bool,
) -> dict[str, Any]:
    predecessor = str(predecessor_candidate_id or "").strip()
    successor = str(successor_candidate_id or "").strip()
    relation = str(relation_kind or "").strip().lower()
    if not predecessor or not successor or predecessor == successor:
        raise EvaluationFindingError("Distinct predecessor and successor repair candidates are required.")
    if relation not in REPAIR_CANDIDATE_LINEAGE_KINDS:
        raise EvaluationFindingError("Unsupported repair candidate lineage kind.")
    evidence = _evidence(evidence_digest)
    private_note = _note(note)

    class _Idempotent(Exception):
        pass

    def apply(record: dict[str, Any]) -> None:
        candidates = [
            dict(row)
            for row in list(record.get("repair_candidate_review_records") or ())
            if isinstance(row, Mapping)
        ]
        by_id = {str(row.get("candidate_id") or ""): row for row in candidates}
        if predecessor not in by_id or successor not in by_id:
            raise EvaluationFindingError("Both repair candidates must be registered to the finding.")
        edges = [
            dict(edge)
            for edge in list(record.get("repair_candidate_lineage") or ())
            if isinstance(edge, Mapping)
        ]
        signature = (predecessor, successor, relation, evidence, private_note)
        for edge in edges:
            if (
                edge.get("predecessor_candidate_id"),
                edge.get("successor_candidate_id"),
                edge.get("relation_kind"),
                edge.get("evidence_digest"),
                edge.get("private_note"),
            ) == signature:
                raise _Idempotent
        existing_successors = {
            str(edge.get("successor_candidate_id") or "")
            for edge in edges
            if str(edge.get("predecessor_candidate_id") or "") == predecessor
        }
        if existing_successors and successor not in existing_successors:
            raise EvaluationFindingError("The predecessor already has an immutable successor lineage edge.")
        if _would_create_cycle(edges, predecessor, successor):
            raise EvaluationFindingError("Repair candidate lineage cannot contain a cycle.")
        if len(edges) >= MAX_REPAIR_CANDIDATE_LINEAGE_EDGES:
            raise EvaluationFindingError("The finding has reached the repair-candidate lineage limit.")
        predecessor_row = by_id[predecessor]
        successor_row = by_id[successor]
        if str(predecessor_row.get("review_state") or "registered") == "superseded":
            raise EvaluationFindingError("The predecessor repair candidate is already superseded.")
        now = _now()
        edges.append(
            {
                "lineage_id": f"candidate_lineage_{uuid.uuid4().hex[:16]}",
                "relation_kind": relation,
                "predecessor_candidate_id": predecessor,
                "successor_candidate_id": successor,
                "predecessor_artifact_sha256": str(predecessor_row.get("artifact_sha256") or ""),
                "successor_artifact_sha256": str(successor_row.get("artifact_sha256") or ""),
                "evidence_digest": evidence,
                "private_note": private_note,
                "recorded_at": now,
            }
        )
        predecessor_row["review_state"] = "superseded"
        predecessor_row["updated_at"] = now
        record["repair_candidate_review_records"] = candidates
        record["repair_candidate_lineage"] = edges

    try:
        mutate_evaluation_finding(
            finding_id,
            expected_revision=expected_revision,
            operator_confirmed=operator_confirmed,
            mutator=apply,
        )
    except _Idempotent:
        response = build_repair_candidate_lineage(finding_id)
        response["duplicate_lineage_edge"] = True
        return response
    response = build_repair_candidate_lineage(finding_id)
    response["duplicate_lineage_edge"] = False
    return response


def repair_candidate_lineage_contains_private_fields(value: Mapping[str, Any] | None) -> bool:
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
