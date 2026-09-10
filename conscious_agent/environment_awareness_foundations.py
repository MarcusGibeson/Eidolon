from __future__ import annotations

"""v1274.0-v1274.2 environment-awareness foundations.

Environment facts are evidence records, not guesses with better typography.  The
record is bound to the existing v1273 ownership lineage and stores only bounded,
privacy-minimized observations.  Raw filesystem paths, environment-variable
values, provider payloads, command output, and secrets are deliberately absent.
"""

import hashlib
import json
import os
import re
import tempfile
import time
from pathlib import Path
from typing import Any, Iterable, Mapping

from ordinary_chat_development_campaign import _proposal_lock
from self_development_alpha_foundations import _runtime_root
from ownership_concurrency_foundations import AUTHORITY_FLAGS as OWNERSHIP_AUTHORITY_FLAGS
from ownership_concurrency_foundations import load_ownership_concurrency, validate_ownership_concurrency

SCHEMA_VERSION = "1"
CONTRACT_VERSION = "v1274.2"
MAX_RECORD_BYTES = 4 * 1024 * 1024
MAX_FACTS = 128
MAX_EVENTS = 96
MAX_SUMMARIES = 8
MAX_CODES = 16

EVIDENCE_CLASSES = frozenset({"observed", "inferred", "assumed", "unknown"})
FACT_DOMAINS = frozenset({"platform", "path", "python", "port", "permission", "configuration", "provider", "process", "resource"})
VALUE_KINDS = frozenset({"boolean", "integer", "number", "code", "digest", "version", "state"})
_SAFE_CODE = re.compile(r"^[a-z0-9][a-z0-9_.:-]{0,127}$")
_DIGEST = re.compile(r"^[a-f0-9]{64}$")
_ENVIRONMENT_ID = re.compile(r"^environment_[a-f0-9]{24}$")

AUTHORITY_FLAGS = {
    **OWNERSHIP_AUTHORITY_FLAGS,
    "environment_observation_is_execution_authority": False,
    "environment_observation_is_provider_authority": False,
    "environment_observation_is_test_authority": False,
    "environment_observation_is_update_authority": False,
    "environment_observation_is_application_authority": False,
    "environment_observation_is_rollback_authority": False,
    "environment_fact_is_authorization": False,
    "environment_preflight_is_execution_authority": False,
    "assumption_may_be_promoted_without_observation": False,
    "unknown_may_be_treated_as_false": False,
    "configuration_values_may_be_persisted": False,
    "raw_paths_may_be_persisted": False,
    "provider_payloads_may_be_persisted": False,
}


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str).encode("utf-8")).hexdigest()


def digest_sensitive_text(value: str) -> str:
    return hashlib.sha256(str(value or "").encode("utf-8", errors="surrogatepass")).hexdigest()


def _root(runtime_root: str | Path | None) -> Path:
    return _runtime_root(runtime_root) / "environment_awareness"


def _path(environment_id: str, runtime_root: str | Path | None) -> Path:
    eid = str(environment_id or "")
    if not _ENVIRONMENT_ID.fullmatch(eid):
        raise ValueError("invalid_environment_awareness_id")
    return _root(runtime_root) / "records" / f"{eid}.json"


def _lock_name(environment_id: str) -> str:
    eid = str(environment_id or "")
    if not _ENVIRONMENT_ID.fullmatch(eid):
        raise ValueError("invalid_environment_awareness_id")
    return "devc_" + eid.split("_", 1)[1]


def environment_id_for_ownership(ownership_id: str, source_manifest_digest: str) -> str:
    return "environment_" + hashlib.sha256(f"{ownership_id}:{source_manifest_digest}:v1274".encode("utf-8")).hexdigest()[:24]


def _read(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    if path.stat().st_size > MAX_RECORD_BYTES:
        raise ValueError("environment_awareness_record_too_large")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("environment_awareness_record_invalid")
    return value


def _write(path: Path, row: Mapping[str, Any]) -> None:
    data = (json.dumps(dict(row), indent=2, sort_keys=True, ensure_ascii=True) + "\n").encode("utf-8")
    if len(data) > MAX_RECORD_BYTES:
        raise ValueError("environment_awareness_record_too_large")
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp: Path | None = None
    try:
        with tempfile.NamedTemporaryFile("wb", delete=False, dir=path.parent, suffix=".tmp") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
            tmp = Path(handle.name)
        os.replace(tmp, path)
        tmp = None
    finally:
        if tmp is not None:
            tmp.unlink(missing_ok=True)


def _fact_digest(row: Mapping[str, Any]) -> str:
    return _digest({k: v for k, v in row.items() if k != "fact_digest"})


def _seal_fact(row: Mapping[str, Any]) -> dict[str, Any]:
    out = dict(row)
    out["fact_digest"] = _fact_digest(out)
    return out


def _event_digest(row: Mapping[str, Any]) -> str:
    return _digest({k: v for k, v in row.items() if k != "event_digest"})


def _seal_event(row: Mapping[str, Any]) -> dict[str, Any]:
    out = dict(row)
    out["event_digest"] = _event_digest(out)
    return out


def _record_digest(row: Mapping[str, Any]) -> str:
    return _digest({k: v for k, v in row.items() if k not in {"record_digest", "operation_status"}})


def _seal(row: Mapping[str, Any]) -> dict[str, Any]:
    out = dict(row)
    out["record_digest"] = _record_digest(out)
    return out


def _safe_code(value: Any, *, field: str) -> str:
    text = str(value or "").strip().lower()
    if not _SAFE_CODE.fullmatch(text):
        raise ValueError(f"invalid_environment_{field}_code")
    return text


def _normalize_value(value: Any, kind: str) -> Any:
    if kind == "boolean":
        if not isinstance(value, bool):
            raise ValueError("environment_boolean_value_required")
        return value
    if kind == "integer":
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError("environment_integer_value_required")
        return int(value)
    if kind == "number":
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("environment_number_value_required")
        return float(value)
    text = str(value or "")
    if kind == "digest":
        if not _DIGEST.fullmatch(text):
            raise ValueError("environment_digest_value_required")
        return text
    if kind in {"code", "state"}:
        return _safe_code(text, field="value")
    if kind == "version":
        if not re.fullmatch(r"[0-9]+(?:\.[0-9]+){1,3}", text):
            raise ValueError("environment_version_value_required")
        return text
    raise ValueError("invalid_environment_value_kind")


def build_environment_fact(
    *,
    domain: str,
    key: str,
    evidence_class: str,
    value_kind: str,
    value: Any,
    source_code: str,
    observed_at: float | None = None,
    basis_fact_digests: Iterable[str] = (),
    stale_after_seconds: int = 300,
) -> dict[str, Any]:
    dom = str(domain or "")
    if dom not in FACT_DOMAINS:
        raise ValueError("invalid_environment_fact_domain")
    evidence = str(evidence_class or "")
    if evidence not in EVIDENCE_CLASSES:
        raise ValueError("invalid_environment_evidence_class")
    kind = str(value_kind or "")
    if kind not in VALUE_KINDS:
        raise ValueError("invalid_environment_value_kind")
    if evidence == "unknown" and kind != "state":
        raise ValueError("unknown_environment_fact_requires_state_value")
    normalized = _normalize_value(value, kind)
    basis = [str(x) for x in basis_fact_digests if str(x)]
    if len(basis) > MAX_CODES or any(not _DIGEST.fullmatch(x) for x in basis):
        raise ValueError("invalid_environment_fact_basis")
    if evidence == "inferred" and not basis:
        raise ValueError("inferred_environment_fact_requires_basis")
    if evidence != "inferred" and basis:
        raise ValueError("environment_fact_basis_only_allowed_for_inference")
    clock = float(time.time() if observed_at is None else observed_at)
    ttl = int(stale_after_seconds)
    if ttl < 1 or ttl > 86400:
        raise ValueError("environment_fact_staleness_out_of_bounds")
    return _seal_fact({
        "domain": dom,
        "key": _safe_code(key, field="fact"),
        "evidence_class": evidence,
        "value_kind": kind,
        "value": normalized,
        "source_code": _safe_code(source_code, field="source"),
        "basis_fact_digests": basis,
        "observed_at": clock,
        "stale_after_seconds": ttl,
        "content_minimized": True,
        "raw_path_present": False,
        "configuration_value_present": False,
        "provider_payload_present": False,
    })


def validate_environment_fact(row: Mapping[str, Any]) -> bool:
    try:
        if row.get("fact_digest") != _fact_digest(row):
            return False
        if str(row.get("domain") or "") not in FACT_DOMAINS:
            return False
        if str(row.get("evidence_class") or "") not in EVIDENCE_CLASSES:
            return False
        kind = str(row.get("value_kind") or "")
        if kind not in VALUE_KINDS:
            return False
        _safe_code(row.get("key"), field="fact")
        _safe_code(row.get("source_code"), field="source")
        _normalize_value(row.get("value"), kind)
        basis = list(row.get("basis_fact_digests") or [])
        if row.get("evidence_class") == "inferred":
            if not basis or any(not _DIGEST.fullmatch(str(x)) for x in basis):
                return False
        elif basis:
            return False
        return row.get("content_minimized") is True and row.get("raw_path_present") is False and row.get("configuration_value_present") is False and row.get("provider_payload_present") is False
    except Exception:
        return False


def _summary(facts: list[Mapping[str, Any]]) -> dict[str, Any]:
    return {
        "summary_version": "1",
        "fact_count": len(facts),
        "observed_count": sum(1 for x in facts if x.get("evidence_class") == "observed"),
        "inferred_count": sum(1 for x in facts if x.get("evidence_class") == "inferred"),
        "assumed_count": sum(1 for x in facts if x.get("evidence_class") == "assumed"),
        "unknown_count": sum(1 for x in facts if x.get("evidence_class") == "unknown"),
        "domains": sorted({str(x.get("domain") or "") for x in facts}),
        "content_minimized": True,
    }


def validate_environment_awareness(row: Mapping[str, Any]) -> dict[str, Any]:
    facts = list(row.get("facts") or [])
    events = list(row.get("events") or [])
    summaries = list(row.get("bounded_summaries") or [])
    digest_ok = bool(row.get("record_digest")) and row.get("record_digest") == _record_digest(row)
    facts_ok = len(facts) <= MAX_FACTS and all(validate_environment_fact(x) for x in facts)
    events_ok = len(events) <= MAX_EVENTS and all(x.get("event_digest") == _event_digest(x) for x in events)
    semantic_ok = (
        bool(_ENVIRONMENT_ID.fullmatch(str(row.get("environment_id") or "")))
        and str(row.get("ownership_id") or "").startswith("ownership_")
        and str(row.get("recovery_id") or "").startswith("recovery_")
        and str(row.get("session_id") or "").startswith("longwork_")
        and str(row.get("campaign_id") or "").startswith("selfalpha_")
        and bool(_DIGEST.fullmatch(str(row.get("source_manifest_digest") or "")))
        and len(summaries) <= MAX_SUMMARIES
        and row.get("content_minimized") is True
        and row.get("raw_paths_persisted") is False
        and row.get("configuration_values_persisted") is False
        and row.get("provider_payloads_persisted") is False
        and row.get("active_source_modified") is False
    )
    authority_ok = all(row.get(k) is v for k, v in AUTHORITY_FLAGS.items())
    ok = digest_ok and facts_ok and events_ok and semantic_ok and authority_ok
    return {
        "ok": ok,
        "status": "environment_awareness_valid" if ok else "environment_awareness_invalid",
        "digest_valid": digest_ok,
        "facts_valid": facts_ok,
        "events_valid": events_ok,
        "semantic_valid": semantic_ok,
        "authority_contained": authority_ok,
    }


def prepare_environment_awareness(ownership_id: str, *, runtime_root: str | Path | None, now: float | None = None) -> dict[str, Any]:
    runtime = _runtime_root(runtime_root)
    ownership = load_ownership_concurrency(ownership_id, runtime_root=runtime)
    if not ownership or not validate_ownership_concurrency(ownership).get("ok"):
        raise ValueError("valid_v1273_ownership_concurrency_required")
    source_digest = str(ownership.get("source_manifest_digest") or "")
    environment_id = environment_id_for_ownership(ownership_id, source_digest)
    path = _path(environment_id, runtime)
    clock = float(time.time() if now is None else now)
    with _proposal_lock(_lock_name(environment_id), runtime):
        existing = _read(path)
        if existing:
            if not validate_environment_awareness(existing).get("ok"):
                raise ValueError("stored_environment_awareness_invalid")
            return {**existing, "operation_status": "restored"}
        row = _seal({
            "ok": True,
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "status": "environment_awareness_prepared",
            "environment_id": environment_id,
            "ownership_id": ownership_id,
            "recovery_id": str(ownership.get("recovery_id") or ""),
            "session_id": str(ownership.get("session_id") or ""),
            "campaign_id": str(ownership.get("campaign_id") or ""),
            "source_manifest_digest": source_digest,
            "facts": [],
            "events": [],
            "bounded_summaries": [],
            "created_at": clock,
            "updated_at": clock,
            "content_minimized": True,
            "raw_paths_persisted": False,
            "configuration_values_persisted": False,
            "provider_payloads_persisted": False,
            "evidence_classes_preserved": True,
            "unknowns_remain_unknown": True,
            "active_source_modified": False,
            **AUTHORITY_FLAGS,
        })
        _write(path, row)
        return {**row, "operation_status": "created"}


def load_environment_awareness(environment_id: str, *, runtime_root: str | Path | None) -> dict[str, Any]:
    return _read(_path(environment_id, runtime_root))


def record_environment_facts(environment_id: str, facts: Iterable[Mapping[str, Any]], *, runtime_root: str | Path | None, event_code: str = "environment_observation_recorded", now: float | None = None) -> dict[str, Any]:
    runtime = _runtime_root(runtime_root)
    incoming = [dict(x) for x in facts]
    if not incoming or len(incoming) > MAX_FACTS or not all(validate_environment_fact(x) for x in incoming):
        raise ValueError("valid_environment_facts_required")
    event = _safe_code(event_code, field="event")
    clock = float(time.time() if now is None else now)
    with _proposal_lock(_lock_name(environment_id), runtime):
        row = load_environment_awareness(environment_id, runtime_root=runtime)
        if not validate_environment_awareness(row).get("ok"):
            raise ValueError("valid_environment_awareness_required")
        # Latest observation for one domain/key replaces the older projection so
        # bounded state does not grow forever across long-running sessions.
        latest: dict[tuple[str, str], dict[str, Any]] = {(str(x.get("domain")), str(x.get("key"))): dict(x) for x in row.get("facts") or []}
        for fact in incoming:
            latest[(str(fact.get("domain")), str(fact.get("key")))] = fact
        merged = list(latest.values())[-MAX_FACTS:]
        events = list(row.get("events") or [])
        events.append(_seal_event({
            "event_code": event,
            "fact_count": len(incoming),
            "recorded_at": clock,
            "content_minimized": True,
            "provider_contacted": False,
            "commands_executed": False,
            "tests_executed": False,
            "authorization_created": False,
        }))
        updated = dict(row)
        updated["facts"] = merged
        updated["events"] = events[-MAX_EVENTS:]
        summaries = list(updated.get("bounded_summaries") or [])
        summaries.append(_summary(merged))
        updated["bounded_summaries"] = summaries[-MAX_SUMMARIES:]
        updated["updated_at"] = clock
        updated["status"] = "environment_awareness_observed"
        updated = _seal(updated)
        _write(_path(environment_id, runtime), updated)
        return {**updated, "operation_status": "facts_recorded"}


def public_environment_awareness(row: Mapping[str, Any], *, now: float | None = None) -> dict[str, Any]:
    clock = float(time.time() if now is None else now)
    facts = list(row.get("facts") or [])
    stale = [x for x in facts if clock >= float(x.get("observed_at") or 0.0) + int(x.get("stale_after_seconds") or 0)]
    return {
        "ok": validate_environment_awareness(row).get("ok") is True,
        "status": "environment_awareness_operator_status",
        "environment_id": row.get("environment_id"),
        "ownership_id": row.get("ownership_id"),
        "fact_count": len(facts),
        "observed_count": sum(1 for x in facts if x.get("evidence_class") == "observed"),
        "inferred_count": sum(1 for x in facts if x.get("evidence_class") == "inferred"),
        "assumed_count": sum(1 for x in facts if x.get("evidence_class") == "assumed"),
        "unknown_count": sum(1 for x in facts if x.get("evidence_class") == "unknown"),
        "stale_fact_count": len(stale),
        "domains": sorted({str(x.get("domain") or "") for x in facts}),
        "raw_paths_persisted": False,
        "configuration_values_persisted": False,
        "provider_payloads_persisted": False,
        "content_minimized": True,
        "active_source_modified": False,
        **AUTHORITY_FLAGS,
    }


__all__ = [
    "CONTRACT_VERSION", "AUTHORITY_FLAGS", "EVIDENCE_CLASSES", "FACT_DOMAINS", "VALUE_KINDS", "MAX_FACTS",
    "build_environment_fact", "validate_environment_fact", "digest_sensitive_text", "prepare_environment_awareness",
    "load_environment_awareness", "validate_environment_awareness", "record_environment_facts", "public_environment_awareness",
    "environment_id_for_ownership",
]
