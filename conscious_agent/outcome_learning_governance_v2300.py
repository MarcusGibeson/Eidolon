from __future__ import annotations

"""Era 9 verified outcome learning and bounded policy adaptation.

This layer composes with the retained v1411-v1420 outcome-learning evidence model.
It persists only content-free outcome/lesson metadata outside source.  It cannot
train models, mutate source, execute tools, or grant authority.
"""

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

from json_storage import AtomicJsonWriteError, write_json_atomic
from metadata_mutation_coordination import MetadataMutationBusy, metadata_mutation_lock
from paths import DATA_DIR
from outcome_learning import record_outcome as retained_record_outcome

CONTRACT_VERSION = "v2325.9"
SCHEMA_VERSION = "1"
STATE_FILE = "era9_outcome_learning.json"
RESULTS = {"success", "failed", "reverted", "operator_rejected"}

_DENIED = {
    "model_training_performed": False,
    "model_weights_changed": False,
    "source_modified": False,
    "tool_executed": False,
    "provider_contacted": False,
    "installation_authorized": False,
    "promotion_authorized": False,
    "authority_expanded": False,
}


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()


def _is_digest(value: Any) -> bool:
    text = str(value or "").lower()
    return len(text) == 64 and all(c in "0123456789abcdef" for c in text)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _path(runtime_root: str | Path | None) -> Path:
    root = Path(runtime_root).expanduser().resolve() if runtime_root else DATA_DIR
    return root / "learning" / STATE_FILE


def _default() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "revision": 0,
        "outcomes": {},
        "lessons": {},
        "processed_events": [],
        "event_requests": {},
        "raw_content_persisted": False,
    }


def _valid_nonnegative_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _valid_outcome(key: str, row: Any) -> bool:
    if not isinstance(row, Mapping) or str(row.get("outcome_id") or "") != key:
        return False
    if not str(row.get("task_type") or "") or row.get("result") not in RESULTS:
        return False
    if not _is_digest(row.get("evidence_digest")) or not _is_digest(row.get("retained_receipt_digest")):
        return False
    applicability = row.get("applicability")
    if not isinstance(applicability, list) or len(applicability) > 12 or any(not isinstance(x, str) or not x or len(x) > 80 for x in applicability):
        return False
    expected = _digest({k: v for k, v in row.items() if k != "outcome_digest"})
    return _is_digest(row.get("outcome_digest")) and row.get("outcome_digest") == expected


def _lesson_digest_payload(row: Mapping[str, Any]) -> dict[str, Any]:
    keys = (
        "lesson_id", "task_type", "failure_class", "repair_class", "applicability",
        "sample_count", "result_counts", "observed_success_rate", "guidance", "confidence",
        "provenance_digests", "historical_evidence_preserved",
        "automatic_generalization_permitted", "authority_created",
    )
    return {key: row.get(key) for key in keys}


def _valid_lesson(key: str, row: Any) -> bool:
    if not isinstance(row, Mapping) or str(row.get("lesson_id") or "") != key:
        return False
    if row.get("state") not in {"active", "retracted", "rejected", "expired"}:
        return False
    confidence = row.get("confidence")
    if not isinstance(confidence, (int, float)) or isinstance(confidence, bool) or not math.isfinite(float(confidence)) or not 0 <= float(confidence) <= 1:
        return False
    provenance = row.get("provenance_digests")
    if not isinstance(provenance, list) or len(provenance) < 2 or not all(_is_digest(value) for value in provenance):
        return False
    if not _valid_nonnegative_int(row.get("sample_count")) or int(row.get("sample_count")) < 2:
        return False
    expected = _digest(_lesson_digest_payload(row))
    return _is_digest(row.get("lesson_digest")) and row.get("lesson_digest") == expected


def _read_strict(path: Path) -> tuple[dict[str, Any] | None, str]:
    if not path.exists():
        return _default(), "missing"
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None, "corrupt"
    if not isinstance(value, dict) or value.get("schema_version") != SCHEMA_VERSION or value.get("contract_version") != CONTRACT_VERSION:
        return None, "invalid_shape"
    outcomes = value.get("outcomes")
    lessons = value.get("lessons")
    events = value.get("processed_events")
    requests = value.get("event_requests", {})
    if not isinstance(outcomes, dict) or not isinstance(lessons, dict) or not isinstance(events, list) or not isinstance(requests, dict) or not _valid_nonnegative_int(value.get("revision")):
        return None, "invalid_shape"
    if len(events) > 1024 or not all(_is_digest(event) for event in events):
        return None, "invalid_event_state"
    if set(requests) != set(events) or not all(_is_digest(value) for value in requests.values()):
        return None, "invalid_event_request_state"
    if any(not _valid_outcome(str(key), row) for key, row in outcomes.items()):
        return None, "invalid_outcome_record"
    if any(not _valid_lesson(str(key), row) for key, row in lessons.items()):
        return None, "invalid_lesson_record"
    value["raw_content_persisted"] = False
    return value, "valid"


def inspect_learning_state(*, runtime_root: str | Path | None = None) -> dict[str, Any]:
    state, status = _read_strict(_path(runtime_root))
    if state is None:
        return {"ok": False, "status": f"outcome_learning_store_{status}", "mutation_permitted": False, **_DENIED}
    lessons = list(state.get("lessons", {}).values())
    return {
        "ok": True,
        "status": "outcome_learning_state_ready",
        "revision": int(state.get("revision") or 0),
        "outcome_count": len(state.get("outcomes", {})),
        "lesson_count": len(lessons),
        "active_lesson_count": sum(1 for row in lessons if isinstance(row, Mapping) and row.get("state") == "active"),
        "retained_outcome_learning_owner": "outcome_learning:v1420.9",
        "content_free": True,
        "mutation_permitted": True,
        **_DENIED,
    }


def record_verified_outcome(
    *, outcome_id: str, task_type: str, result: str, evidence_digest: str,
    strategy_code: str = "none", failure_class: str = "none", repair_class: str = "none",
    applicability: Sequence[str] = (), event_id: str, runtime_root: str | Path | None = None,
) -> dict[str, Any]:
    oid = str(outcome_id or "").strip()
    event = str(event_id or "").strip()
    task = str(task_type or "").strip().lower()
    result_code = str(result or "").strip().lower()
    if not oid or not event or not task or result_code not in RESULTS or not _is_digest(evidence_digest):
        return {"ok": False, "status": "invalid_outcome_contract", **_DENIED}
    if any(len(str(x)) > 80 for x in applicability) or len(applicability) > 12:
        return {"ok": False, "status": "unbounded_applicability", **_DENIED}
    path = _path(runtime_root)
    event_digest = _digest(["outcome", event])
    request_digest = _digest([oid, task, result_code, evidence_digest.lower(), strategy_code, failure_class, repair_class, list(applicability)])
    try:
        with metadata_mutation_lock(path, timeout_seconds=15.0):
            state, state_status = _read_strict(path)
            if state is None:
                return {"ok": False, "status": f"outcome_learning_store_{state_status}", "store_preserved": True, **_DENIED}
            if event_digest in state["processed_events"]:
                if state["event_requests"].get(event_digest) != request_digest:
                    return {"ok": False, "status": "outcome_event_identity_conflict", **_DENIED}
                prior = state["outcomes"].get(oid)
                return {"ok": True, "status": "outcome_record_replayed", "outcome": deepcopy(prior), "idempotent": True, **_DENIED}
            if oid in state["outcomes"]:
                return {"ok": False, "status": "outcome_identity_conflict", **_DENIED}
            if any(str(row.get("evidence_digest") or "").lower() == evidence_digest.lower() for row in state["outcomes"].values() if isinstance(row, Mapping)):
                return {"ok": False, "status": "outcome_evidence_already_recorded", **_DENIED}
            retained = retained_record_outcome(
                task_type=task,
                prediction={"result": "unknown"},
                actual={"result": "success" if result_code == "success" else result_code},
                evidence_digest=evidence_digest,
                failure_class=failure_class,
                repair=repair_class,
                version="2301.0",
            )
            row = {
                "outcome_id": oid,
                "task_type": task,
                "result": result_code,
                "evidence_digest": evidence_digest.lower(),
                "strategy_code": str(strategy_code or "none")[:80],
                "failure_class": str(failure_class or "none")[:80],
                "repair_class": str(repair_class or "none")[:80],
                "applicability": sorted(set(str(x)[:80] for x in applicability if str(x).strip())),
                "retained_receipt_digest": str(retained.get("evidence_digest") or ""),
                "recorded_at": _now(),
            }
            row["outcome_digest"] = _digest(row)
            state["outcomes"][oid] = row
            state["processed_events"] = (state["processed_events"] + [event_digest])[-1024:]
            state["event_requests"][event_digest] = request_digest
            state["event_requests"] = {key: state["event_requests"][key] for key in state["processed_events"]}
            state["revision"] = int(state.get("revision") or 0) + 1
            write_json_atomic(path, state, expected_type=dict, sort_keys=True, coordinate=False, replace_retries=12, retry_delay_seconds=0.05)
            return {"ok": True, "status": "verified_outcome_recorded", "outcome": deepcopy(row), "idempotent": False, **_DENIED}
    except (MetadataMutationBusy, AtomicJsonWriteError, OSError) as error:
        return {"ok": False, "status": getattr(error, "status", "outcome_write_blocked"), **_DENIED}


def extract_bounded_lessons(*, runtime_root: str | Path | None = None, min_samples: int = 2) -> dict[str, Any]:
    state, state_status = _read_strict(_path(runtime_root))
    if state is None:
        return {"ok": False, "status": f"outcome_learning_store_{state_status}", **_DENIED}
    try:
        minimum = int(min_samples)
    except (TypeError, ValueError, OverflowError):
        return {"ok": False, "status": "invalid_minimum_sample_count", **_DENIED}
    if minimum < 2 or minimum > 1000:
        return {"ok": False, "status": "invalid_minimum_sample_count", **_DENIED}
    groups: dict[tuple[str, str, str, tuple[str, ...]], list[Mapping[str, Any]]] = {}
    for row in state["outcomes"].values():
        if not isinstance(row, Mapping):
            continue
        key = (
            str(row.get("task_type") or ""), str(row.get("failure_class") or "none"),
            str(row.get("repair_class") or "none"), tuple(row.get("applicability") or ()),
        )
        groups.setdefault(key, []).append(row)
    candidates = []
    for (task, failure, repair, applicability), rows in groups.items():
        if len(rows) < minimum:
            continue
        counts = {code: sum(1 for r in rows if r.get("result") == code) for code in RESULTS}
        success_rate = counts["success"] / len(rows)
        guidance = "prefer_strategy" if success_rate >= 0.75 else "avoid_or_reassess_strategy" if counts["failed"] + counts["reverted"] + counts["operator_rejected"] >= 2 else "insufficient_direction"
        lesson = {
            "lesson_id": "era9-lesson-" + _digest([task, failure, repair, applicability])[:20],
            "task_type": task,
            "failure_class": failure,
            "repair_class": repair,
            "applicability": list(applicability),
            "sample_count": len(rows),
            "result_counts": counts,
            "observed_success_rate": round(success_rate, 4),
            "guidance": guidance,
            "confidence": round(min(0.95, 0.45 + 0.08 * len(rows)), 3),
            "provenance_digests": sorted(str(r.get("evidence_digest")) for r in rows),
            "historical_evidence_preserved": True,
            "automatic_generalization_permitted": False,
            "authority_created": False,
        }
        lesson["lesson_digest"] = _digest(lesson)
        candidates.append(lesson)
    return {"ok": True, "status": "bounded_outcome_lessons_extracted", "lessons": candidates, "lesson_count": len(candidates), "content_free": True, **_DENIED}


def persist_lesson_candidates(*, event_id: str, runtime_root: str | Path | None = None) -> dict[str, Any]:
    extracted = extract_bounded_lessons(runtime_root=runtime_root)
    if not extracted.get("ok"):
        return extracted
    path = _path(runtime_root)
    event_digest = _digest(["lessons", str(event_id or "")])
    request_digest = _digest(["persist-lessons"])
    if not str(event_id or "").strip():
        return {"ok": False, "status": "event_id_required", **_DENIED}
    try:
        with metadata_mutation_lock(path, timeout_seconds=15.0):
            state, state_status = _read_strict(path)
            if state is None:
                return {"ok": False, "status": f"outcome_learning_store_{state_status}", "store_preserved": True, **_DENIED}
            if event_digest in state["processed_events"]:
                if state["event_requests"].get(event_digest) != request_digest:
                    return {"ok": False, "status": "lesson_event_identity_conflict", **_DENIED}
                return {"ok": True, "status": "lesson_persistence_replayed", "idempotent": True, **_DENIED}
            for lesson in extracted["lessons"]:
                old = state["lessons"].get(lesson["lesson_id"])
                if isinstance(old, Mapping) and old.get("state") in {"retracted", "rejected"}:
                    continue
                state["lessons"][lesson["lesson_id"]] = {**lesson, "state": "active", "updated_at": _now()}
            state["processed_events"] = (state["processed_events"] + [event_digest])[-1024:]
            state["event_requests"][event_digest] = request_digest
            state["event_requests"] = {key: state["event_requests"][key] for key in state["processed_events"]}
            state["revision"] = int(state.get("revision") or 0) + 1
            write_json_atomic(path, state, expected_type=dict, sort_keys=True, coordinate=False, replace_retries=12, retry_delay_seconds=0.05)
            return {"ok": True, "status": "lesson_candidates_persisted", "lesson_count": len(state["lessons"]), "idempotent": False, **_DENIED}
    except (MetadataMutationBusy, AtomicJsonWriteError, OSError) as error:
        return {"ok": False, "status": getattr(error, "status", "lesson_write_blocked"), **_DENIED}


def revise_lesson(*, lesson_id: str, expected_digest: str, action: str, event_id: str, runtime_root: str | Path | None = None) -> dict[str, Any]:
    if action not in {"retract", "reject", "expire", "retain"} or not _is_digest(expected_digest):
        return {"ok": False, "status": "invalid_lesson_revision", **_DENIED}
    path = _path(runtime_root)
    event_digest = _digest(["lesson-revision", event_id])
    request_digest = _digest([lesson_id, expected_digest, action])
    try:
        with metadata_mutation_lock(path, timeout_seconds=15.0):
            state, state_status = _read_strict(path)
            if state is None:
                return {"ok": False, "status": f"outcome_learning_store_{state_status}", "store_preserved": True, **_DENIED}
            if event_digest in state["processed_events"]:
                if state["event_requests"].get(event_digest) != request_digest:
                    return {"ok": False, "status": "lesson_revision_event_identity_conflict", **_DENIED}
                return {"ok": True, "status": "lesson_revision_replayed", "idempotent": True, **_DENIED}
            row = state["lessons"].get(lesson_id)
            if not isinstance(row, dict):
                return {"ok": False, "status": "lesson_not_found", **_DENIED}
            if str(row.get("lesson_digest")) != expected_digest:
                return {"ok": False, "status": "stale_lesson_digest", **_DENIED}
            row["state"] = {"retract": "retracted", "reject": "rejected", "expire": "expired", "retain": "active"}[action]
            row["updated_at"] = _now()
            state["processed_events"] = (state["processed_events"] + [event_digest])[-1024:]
            state["event_requests"][event_digest] = request_digest
            state["event_requests"] = {key: state["event_requests"][key] for key in state["processed_events"]}
            state["revision"] = int(state.get("revision") or 0) + 1
            write_json_atomic(path, state, expected_type=dict, sort_keys=True, coordinate=False, replace_retries=12, retry_delay_seconds=0.05)
            return {"ok": True, "status": "lesson_revised", "lesson_state": row["state"], "idempotent": False, **_DENIED}
    except (MetadataMutationBusy, AtomicJsonWriteError, OSError) as error:
        return {"ok": False, "status": getattr(error, "status", "lesson_revision_blocked"), **_DENIED}


def build_policy_adaptation(*, task_type: str, runtime_root: str | Path | None = None) -> dict[str, Any]:
    state, state_status = _read_strict(_path(runtime_root))
    if state is None:
        return {"ok": False, "status": f"outcome_learning_store_{state_status}", **_DENIED}
    selected = []
    for row in state["lessons"].values():
        if isinstance(row, Mapping) and row.get("state") == "active" and row.get("task_type") == task_type:
            selected.append({k: row.get(k) for k in ("lesson_id", "guidance", "confidence", "applicability", "lesson_digest")})
    selected.sort(key=lambda r: (-float(r.get("confidence") or 0), str(r.get("lesson_id"))))
    result = {
        "ok": True,
        "status": "bounded_policy_adaptation_prepared",
        "task_type": task_type,
        "selected_lessons": selected[:8],
        "adjust_estimates_permitted": bool(selected),
        "adjust_test_selection_permitted": bool(selected),
        "adjust_strategy_preference_permitted": bool(selected),
        "automatic_universalization_permitted": False,
        "historical_evidence_rewrite_permitted": False,
        "adaptation_is_advisory": True,
        "content_free": True,
        **_DENIED,
    }
    result["adaptation_digest"] = _digest(result)
    return result


def evaluate_policy_adaptation(
    *, baseline_trials: Sequence[Mapping[str, Any]], adapted_trials: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Compare held-out outcome evidence without learning from the evaluation rows."""
    def _summarize(rows: Sequence[Mapping[str, Any]]) -> tuple[bool, int, int, set[str]]:
        success = 0; total = 0; digests: set[str] = set()
        for row in rows:
            if not isinstance(row, Mapping) or not _is_digest(row.get("evidence_digest")) or not isinstance(row.get("success"), bool):
                return False, 0, 0, set()
            digest = str(row.get("evidence_digest")).lower()
            if digest in digests:
                return False, 0, 0, set()
            digests.add(digest); total += 1; success += int(row.get("success") is True)
        return bool(total), success, total, digests
    bok, bs, bt, bd = _summarize(baseline_trials); aok, ass, at, ad = _summarize(adapted_trials)
    if not bok or not aok or bd & ad:
        return {"ok": False, "status": "invalid_or_leaky_held_out_evaluation", **_DENIED}
    br = bs / bt; ar = ass / at
    result = {
        "ok": True, "status": "held_out_policy_adaptation_evaluated",
        "baseline_samples": bt, "adapted_samples": at,
        "baseline_success_rate": round(br, 4), "adapted_success_rate": round(ar, 4),
        "absolute_improvement": round(ar - br, 4), "measurable_improvement": ar > br,
        "evaluation_rows_not_added_to_learning_store": True, "held_out_evidence_disjoint": True,
        "content_free": True, **_DENIED,
    }
    result["evaluation_digest"] = _digest(result)
    return result


__all__ = [
    "CONTRACT_VERSION", "inspect_learning_state", "record_verified_outcome",
    "extract_bounded_lessons", "persist_lesson_candidates", "revise_lesson",
    "build_policy_adaptation", "evaluate_policy_adaptation",
]
