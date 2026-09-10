from __future__ import annotations

"""Private runtime storage for v1087.1 operator-guided daily evaluations.

Evaluations store explicit operator ratings and optional private notes beneath
EIDOLON_DATA_DIR. Public summaries expose only bounded counts, selected issue
labels, states, and digests. The module never calls a provider, reads transcript
content, grants authority, or promotes a release.
"""

from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import threading
import time
from typing import Any, Iterator, Mapping
import uuid

from paths import DATA_DIR
from conversation_daily_evaluation_protocol import (
    EVALUATION_SIGNALS,
    EVALUATION_STATES,
    ISSUE_DOMAINS,
    ISSUE_SEVERITIES,
    MAX_EVALUATION_OBSERVATIONS,
    MAX_OPERATOR_NOTE_CHARS,
    RATING_DIMENSIONS,
    RATING_MAXIMUM,
    RATING_MINIMUM,
    build_daily_evaluation_protocol,
)
from conversation_evaluation_outcomes import classify_evaluation_outcome
from conversation_surface_contracts import DailyEvaluationError

DAILY_EVALUATION_SCHEMA_VERSION = "1"
DAILY_EVALUATIONS_DIR = DATA_DIR / "conversation_evaluations"
_EVALUATION_ID_PATTERN = re.compile(r"^daily_eval_[0-9]{8}T[0-9]{6}_[a-f0-9]{12}$")
_OBSERVATION_ID_PATTERN = re.compile(r"^observation_[a-f0-9]{16}$")
_STORAGE_LOCK = threading.RLock()
_LOCK_TIMEOUT_SECONDS = 8.0
_STALE_LOCK_SECONDS = 120.0


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    ).hexdigest()


def _new_evaluation_id() -> str:
    return f"daily_eval_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}_{uuid.uuid4().hex[:12]}"


def _validate_evaluation_id(evaluation_id: str) -> str:
    token = str(evaluation_id or "").strip()
    if not _EVALUATION_ID_PATTERN.fullmatch(token):
        raise DailyEvaluationError("Invalid daily evaluation identifier.")
    return token


def _evaluation_path(evaluation_id: str) -> Path:
    return DAILY_EVALUATIONS_DIR / f"{_validate_evaluation_id(evaluation_id)}.json"


def _lock_path(evaluation_id: str) -> Path:
    return DAILY_EVALUATIONS_DIR / ".locks" / f"{_validate_evaluation_id(evaluation_id)}.lock"


def _load_json(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _atomic_write(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp")
    try:
        temporary.write_text(json.dumps(dict(value), indent=2, sort_keys=True), encoding="utf-8")
        for attempt in range(5):
            try:
                temporary.replace(path)
                return
            except PermissionError:
                if attempt == 4:
                    raise
                time.sleep(0.01 * (attempt + 1))
    finally:
        temporary.unlink(missing_ok=True)


@contextmanager
def _evaluation_lock(evaluation_id: str) -> Iterator[None]:
    lock_path = _lock_path(evaluation_id)
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + _LOCK_TIMEOUT_SECONDS
    descriptor: int | None = None
    while descriptor is None:
        try:
            descriptor = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(descriptor, f"{os.getpid()}\n".encode("ascii", errors="ignore"))
            os.fsync(descriptor)
        except FileExistsError:
            try:
                age = max(0.0, time.time() - lock_path.stat().st_mtime)
            except OSError:
                age = 0.0
            if age >= _STALE_LOCK_SECONDS:
                try:
                    lock_path.unlink()
                except OSError:
                    pass
                continue
            if time.monotonic() >= deadline:
                raise DailyEvaluationError("This evaluation is being updated by another process. Reload before trying again.")
            time.sleep(0.02)
    try:
        yield
    finally:
        try:
            os.close(descriptor)
        except OSError:
            pass
        try:
            lock_path.unlink()
        except OSError:
            pass


@contextmanager
def _storage_lock(evaluation_id: str) -> Iterator[None]:
    with _STORAGE_LOCK:
        with _evaluation_lock(evaluation_id):
            yield


def _normalize_ratings(ratings: Mapping[str, Any] | None) -> dict[str, int]:
    raw = ratings if isinstance(ratings, Mapping) else {}
    normalized: dict[str, int] = {}
    for dimension in RATING_DIMENSIONS:
        if dimension not in raw or raw.get(dimension) in {None, ""}:
            continue
        try:
            value = int(raw.get(dimension))
        except (TypeError, ValueError) as error:
            raise DailyEvaluationError(f"Rating for {dimension} must be an integer.") from error
        if value < RATING_MINIMUM or value > RATING_MAXIMUM:
            raise DailyEvaluationError(
                f"Rating for {dimension} must be between {RATING_MINIMUM} and {RATING_MAXIMUM}."
            )
        normalized[dimension] = value
    if not normalized:
        raise DailyEvaluationError("At least one explicit operator rating is required.")
    return normalized


def _normalize_signals(signals: Any) -> list[str]:
    if signals is None:
        return []
    if not isinstance(signals, (list, tuple, set)):
        raise DailyEvaluationError("Evaluation signals must be a list.")
    normalized: list[str] = []
    for raw in signals:
        token = str(raw or "").strip().lower()
        if token not in EVALUATION_SIGNALS:
            raise DailyEvaluationError(f"Unsupported evaluation signal: {token or 'empty'}.")
        if token not in normalized:
            normalized.append(token)
    return normalized[: len(EVALUATION_SIGNALS)]


def _normalize_issue(domain: str, severity: str) -> tuple[str, str]:
    domain_token = str(domain or "none").strip().lower()
    severity_token = str(severity or "none").strip().lower()
    if domain_token not in ISSUE_DOMAINS:
        raise DailyEvaluationError("Unsupported evaluation issue domain.")
    if severity_token not in ISSUE_SEVERITIES:
        raise DailyEvaluationError("Unsupported evaluation issue severity.")
    if domain_token == "none" and severity_token != "none":
        raise DailyEvaluationError("An issue severity requires an explicit issue domain.")
    if domain_token != "none" and severity_token == "none":
        severity_token = "minor"
    return domain_token, severity_token


def _load_private(evaluation_id: str) -> dict[str, Any]:
    token = _validate_evaluation_id(evaluation_id)
    value = _load_json(_evaluation_path(token))
    if not value or value.get("type") != "desktop_alpha_daily_evaluation":
        raise DailyEvaluationError("Daily evaluation not found.")
    return value


def _observation_public(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "observation_id": str(row.get("observation_id") or ""),
        "recorded_at": str(row.get("recorded_at") or ""),
        "rating_dimensions": sorted(str(key) for key in (row.get("ratings") or {}) if key in RATING_DIMENSIONS),
        "rating_count": len(row.get("ratings") or {}),
        "signals": [str(item) for item in list(row.get("signals") or ()) if str(item) in EVALUATION_SIGNALS],
        "issue_domain": str(row.get("issue_domain") or "none"),
        "severity": str(row.get("severity") or "none"),
        "reproducible": bool(row.get("reproducible")),
        "note_present": bool(row.get("note")),
        "note_digest": str(row.get("note_digest") or ""),
    }


def _public_summary(value: Mapping[str, Any]) -> dict[str, Any]:
    observations = [row for row in list(value.get("observations") or ()) if isinstance(row, Mapping)]
    classification = classify_evaluation_outcome(
        evaluation_state=str(value.get("state") or "active"),
        observations=observations,
    )
    dimension_counts = {dimension: 0 for dimension in RATING_DIMENSIONS}
    rating_histograms = {
        dimension: {str(rating): 0 for rating in range(RATING_MINIMUM, RATING_MAXIMUM + 1)}
        for dimension in RATING_DIMENSIONS
    }
    for row in observations:
        ratings = row.get("ratings") if isinstance(row.get("ratings"), Mapping) else {}
        for dimension, raw_value in ratings.items():
            if dimension not in dimension_counts:
                continue
            value_token = str(int(raw_value))
            dimension_counts[dimension] += 1
            rating_histograms[dimension][value_token] += 1
    public_observations = [_observation_public(row) for row in observations]
    return {
        "ok": True,
        "type": "desktop_alpha_daily_evaluation_summary",
        "schema_version": DAILY_EVALUATION_SCHEMA_VERSION,
        "evaluation_id": str(value.get("evaluation_id") or ""),
        "session_id": str(value.get("session_id") or ""),
        "state": str(value.get("state") or "active"),
        "revision": int(value.get("revision") or 0),
        "started_at": str(value.get("started_at") or ""),
        "updated_at": str(value.get("updated_at") or ""),
        "completed_at": str(value.get("completed_at") or ""),
        "aborted_at": str(value.get("aborted_at") or ""),
        "readiness_contract_digest": str(value.get("readiness_contract_digest") or ""),
        "readiness_areas_digest": str(value.get("readiness_areas_digest") or ""),
        "observation_count": len(observations),
        "maximum_observations": MAX_EVALUATION_OBSERVATIONS,
        "dimension_observation_counts": dimension_counts,
        "rating_histograms": rating_histograms,
        "observations": public_observations,
        "observation_evidence_digest": _digest(public_observations),
        "outcome": classification,
        "private_notes_stored": sum(1 for row in observations if row.get("note")),
        "private_note_content_returned": False,
        "operator_observation_required": True,
        "autonomous_scoring": False,
        "provider_invoked": False,
        "embedding_provider_invoked": False,
        "model_management": False,
        "provider_switching": False,
        "generation_settings_changed": False,
        "approval_granted": False,
        "rollback_authorized": False,
        "installation_performed": False,
        "promotion_performed": False,
        "release_certified": False,
        "runtime_state_written": True,
        "source_tree_written": False,
        "content_free": True,
        "redacted": True,
    }


def start_daily_evaluation(
    session_id: str,
    *,
    operator_confirmed: bool,
    evaluation_id: str = "",
) -> dict[str, Any]:
    if not operator_confirmed:
        raise DailyEvaluationError("Explicit operator confirmation is required to start an evaluation.")
    session_token = str(session_id or "").strip()
    if not session_token:
        raise DailyEvaluationError("A conversation session identifier is required.")
    from conversation_sessions import load_conversation_session

    if not load_conversation_session(session_token, include_turns=False):
        raise DailyEvaluationError("Conversation session not found.")
    token = _validate_evaluation_id(evaluation_id) if evaluation_id else _new_evaluation_id()
    protocol = build_daily_evaluation_protocol(session_id=session_token)
    if protocol.get("protocol_status") != "ready":
        raise DailyEvaluationError("The conversation-readiness checkpoint requires review before evaluation.")
    record = {
        "type": "desktop_alpha_daily_evaluation",
        "schema_version": DAILY_EVALUATION_SCHEMA_VERSION,
        "evaluation_id": token,
        "session_id": session_token,
        "state": "active",
        "revision": 1,
        "started_at": _now_utc(),
        "updated_at": _now_utc(),
        "completed_at": "",
        "aborted_at": "",
        "readiness_contract_digest": str(protocol.get("readiness_contract_digest") or ""),
        "readiness_areas_digest": str(protocol.get("readiness_areas_digest") or ""),
        "observations": [],
        "operator_confirmed": True,
        "provider_invoked": False,
        "release_certified": False,
        "promotion_performed": False,
    }
    with _storage_lock(token):
        path = _evaluation_path(token)
        if path.exists():
            raise DailyEvaluationError("Daily evaluation already exists.")
        _atomic_write(path, record)
    return _public_summary(record)


def load_daily_evaluation(evaluation_id: str, *, include_private_notes: bool = False) -> dict[str, Any]:
    value = _load_private(evaluation_id)
    if not include_private_notes:
        return _public_summary(value)
    result = dict(value)
    result["outcome"] = classify_evaluation_outcome(
        evaluation_state=str(value.get("state") or "active"),
        observations=[row for row in list(value.get("observations") or ()) if isinstance(row, Mapping)],
    )
    result["private_runtime_data"] = True
    return result


def record_operator_observation(
    evaluation_id: str,
    *,
    ratings: Mapping[str, Any] | None,
    note: str = "",
    signals: Any = None,
    issue_domain: str = "none",
    severity: str = "none",
    reproducible: bool = False,
    expected_revision: int | None,
    operator_confirmed: bool,
) -> dict[str, Any]:
    if not operator_confirmed:
        raise DailyEvaluationError("Explicit operator confirmation is required to record an observation.")
    normalized_ratings = _normalize_ratings(ratings)
    normalized_signals = _normalize_signals(signals)
    domain_token, severity_token = _normalize_issue(issue_domain, severity)
    note_text = str(note or "")
    if len(note_text) > MAX_OPERATOR_NOTE_CHARS:
        raise DailyEvaluationError(f"Operator notes are limited to {MAX_OPERATOR_NOTE_CHARS} characters.")
    token = _validate_evaluation_id(evaluation_id)
    with _storage_lock(token):
        value = _load_private(token)
        if value.get("state") != "active":
            raise DailyEvaluationError("Only an active evaluation can receive observations.")
        current_revision = int(value.get("revision") or 0)
        if expected_revision is None or int(expected_revision) != current_revision:
            raise DailyEvaluationError("Daily evaluation changed in another tab. Reload before updating it.")
        observations = [row for row in list(value.get("observations") or ()) if isinstance(row, Mapping)]
        if len(observations) >= MAX_EVALUATION_OBSERVATIONS:
            raise DailyEvaluationError("The bounded observation limit has been reached.")
        observation_id = f"observation_{uuid.uuid4().hex[:16]}"
        assert _OBSERVATION_ID_PATTERN.fullmatch(observation_id)
        observation = {
            "observation_id": observation_id,
            "recorded_at": _now_utc(),
            "ratings": normalized_ratings,
            "note": note_text,
            "note_digest": hashlib.sha256(note_text.encode("utf-8")).hexdigest() if note_text else "",
            "signals": normalized_signals,
            "issue_domain": domain_token,
            "severity": severity_token,
            "reproducible": bool(reproducible),
            "operator_confirmed": True,
        }
        observations.append(observation)
        value["observations"] = observations
        value["revision"] = current_revision + 1
        value["updated_at"] = _now_utc()
        _atomic_write(_evaluation_path(token), value)
    return _public_summary(value)


def finish_daily_evaluation(
    evaluation_id: str,
    *,
    state: str,
    expected_revision: int | None,
    operator_confirmed: bool,
) -> dict[str, Any]:
    if not operator_confirmed:
        raise DailyEvaluationError("Explicit operator confirmation is required to finish an evaluation.")
    state_token = str(state or "").strip().lower()
    if state_token not in {"completed", "aborted"}:
        raise DailyEvaluationError("Evaluation may only be completed or aborted explicitly.")
    token = _validate_evaluation_id(evaluation_id)
    with _storage_lock(token):
        value = _load_private(token)
        if value.get("state") != "active":
            raise DailyEvaluationError("The evaluation is already closed.")
        current_revision = int(value.get("revision") or 0)
        if expected_revision is None or int(expected_revision) != current_revision:
            raise DailyEvaluationError("Daily evaluation changed in another tab. Reload before updating it.")
        value["state"] = state_token
        value["revision"] = current_revision + 1
        value["updated_at"] = _now_utc()
        value["completed_at"] = _now_utc() if state_token == "completed" else ""
        value["aborted_at"] = _now_utc() if state_token == "aborted" else ""
        _atomic_write(_evaluation_path(token), value)
    return _public_summary(value)


def daily_evaluation_summary_contains_private_fields(value: Mapping[str, Any] | None) -> bool:
    forbidden = {
        "note",
        "notes",
        "content",
        "text",
        "message",
        "user_message",
        "assistant_response",
        "transcript",
        "prompt",
        "temporary_instruction",
        "pinned_context",
        "queued_operator_intent",
        "provider_payload",
        "credentials",
        "vectors",
        "embedding",
        "receipt",
        "receipts",
        "hidden_reasoning",
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
