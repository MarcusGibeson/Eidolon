from __future__ import annotations

"""Era 8 audit lineage and incident-response governance."""

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Iterable, Mapping

from json_storage import AtomicJsonWriteError, load_json_file, write_json_atomic
from metadata_mutation_coordination import MetadataMutationBusy, metadata_mutation_lock
from paths import DATA_DIR
from security_hardening import audit_integrity, incident_response

CONTRACT_VERSION = "v2299.9"
SCHEMA_VERSION = "1"
STATE_FILE = "era8_incidents.json"
MAX_EVENTS = 512

_DENIED = {
    "external_notification_sent": False,
    "capability_disabled_in_os": False,
    "recovery_executed": False,
    "source_modified": False,
    "private_content_recorded": False,
    "installation_authorized": False,
    "promotion_authorized": False,
    "authority_expanded": False,
}


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()


def _hex64(value: Any) -> str:
    text = str(value or "").strip().lower()
    return text if re.fullmatch(r"[0-9a-f]{64}", text) else ""


def _state_path(runtime_root: str | Path | None = None) -> Path:
    root = Path(runtime_root).expanduser().resolve() if runtime_root else DATA_DIR
    return root / "security" / STATE_FILE


def _default_state() -> dict[str, Any]:
    return {"schema_version": SCHEMA_VERSION, "contract_version": CONTRACT_VERSION, "revision": 0, "incidents": {}, "events": [], "raw_private_content_recorded": False}


def _read_state(runtime_root: str | Path | None = None) -> dict[str, Any]:
    state, _ = _read_state_checked(runtime_root)
    return state


def _read_state_checked(runtime_root: str | Path | None = None) -> tuple[dict[str, Any], bool]:
    path = _state_path(runtime_root)
    if not path.exists():
        return _default_state(), True
    try:
        value = json.loads(path.read_bytes().decode("utf-8-sig"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return _default_state(), False
    if not isinstance(value, dict) or not isinstance(value.get("incidents"), dict) or not isinstance(value.get("events"), list):
        return _default_state(), False
    state = deepcopy(value)
    integrity_ok = True
    for iid, incident in state["incidents"].items():
        if not isinstance(iid, str) or not isinstance(incident, Mapping) or not _hex64(incident.get("incident_digest")):
            integrity_ok = False
            continue
        expected = _digest({k: v for k, v in incident.items() if k not in {"opened_at", "incident_digest"}})
        if expected != incident.get("incident_digest"):
            integrity_ok = False
    state["raw_private_content_recorded"] = False
    return state, integrity_ok


def build_audit_lineage(events: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    """Build a content-free chain binding the full Era 8 action lineage."""
    normalized = []
    previous = "0" * 64
    event_digests: list[str] = []
    required = ("intent_digest", "authority_digest", "attempt_digest", "result_digest", "rollback_digest", "operator_decision_digest")
    for ordinal, event in enumerate(list(events)[:MAX_EVENTS], 1):
        row = {
            "ordinal": ordinal,
            "session_id": str(event.get("session_id") or "")[:160],
            "event": str(event.get("event") or "")[:120],
            "intent_digest": _hex64(event.get("intent_digest")),
            "authority_digest": _hex64(event.get("authority_digest")),
            "attempt_digest": _hex64(event.get("attempt_digest")),
            "result_digest": _hex64(event.get("result_digest")),
            "rollback_digest": _hex64(event.get("rollback_digest")),
            "operator_decision_digest": _hex64(event.get("operator_decision_digest")),
            "side_effect_digest": _hex64(event.get("side_effect_digest")),
            "previous_digest": previous,
        }
        current = _digest(row)
        row["event_digest"] = current
        previous = current
        event_digests.append(current)
        normalized.append(row)
    retained = audit_integrity(normalized, version=CONTRACT_VERSION)
    result = {
        "ok": all(all(key in row for key in required) for row in normalized),
        "status": "audit_lineage_built",
        "contract_version": CONTRACT_VERSION,
        "event_count": len(normalized),
        "chain_head": previous,
        "tamper_evident": True,
        "reconstructable": all(row["ordinal"] == index + 1 for index, row in enumerate(normalized)),
        "lineage_fields_present": all(all(key in row for key in required) for row in normalized),
        "event_digests": event_digests,
        "chain": normalized,
        "retained_audit_chain_head": str((retained.get("payload") or {}).get("chain_head") or ""),
        "retained_audit_compatibility": bool((retained.get("payload") or {}).get("tamper_evident")),
        "raw_content_exposed": False,
        **_DENIED,
    }
    result["lineage_digest"] = _digest({key: value for key, value in result.items() if key != "chain"})
    return result


def validate_audit_lineage(lineage: Mapping[str, Any]) -> dict[str, Any]:
    chain = lineage.get("chain") if isinstance(lineage.get("chain"), list) else []
    previous = "0" * 64
    reasons: list[str] = []
    if lineage.get("contract_version") != CONTRACT_VERSION:
        reasons.append("contract_version_mismatch")
    if int(lineage.get("event_count") or -1) != len(chain):
        reasons.append("event_count_mismatch")
    for ordinal, raw in enumerate(chain, 1):
        if not isinstance(raw, Mapping):
            reasons.append("non_mapping_event")
            continue
        row = dict(raw)
        supplied = str(row.pop("event_digest", ""))
        if int(row.get("ordinal") or 0) != ordinal:
            reasons.append("ordinal_mismatch")
        if str(row.get("previous_digest") or "") != previous:
            reasons.append("previous_digest_mismatch")
        calculated = _digest(row)
        if supplied != calculated:
            reasons.append("event_digest_mismatch")
        previous = supplied if supplied else calculated
        for key in ("intent_digest", "authority_digest", "attempt_digest", "result_digest", "operator_decision_digest"):
            if not _hex64(row.get(key)):
                reasons.append(f"{key}_invalid")
        if row.get("rollback_digest") and not _hex64(row.get("rollback_digest")):
            reasons.append("rollback_digest_invalid")
    if str(lineage.get("chain_head") or "") != previous:
        reasons.append("chain_head_mismatch")
    supplied_events = lineage.get("event_digests") if isinstance(lineage.get("event_digests"), list) else []
    actual_events = [str(row.get("event_digest") or "") for row in chain if isinstance(row, Mapping)]
    if supplied_events != actual_events:
        reasons.append("event_digests_mismatch")
    supplied_lineage = _hex64(lineage.get("lineage_digest"))
    expected_lineage = _digest({key: value for key, value in lineage.items() if key not in {"chain", "lineage_digest"}})
    if supplied_lineage != expected_lineage:
        reasons.append("lineage_digest_mismatch")
    return {
        "ok": not reasons,
        "status": "audit_lineage_valid" if not reasons else "audit_lineage_tampered",
        "reason_codes": sorted(set(reasons)),
        "event_count": len(chain),
        "raw_content_exposed": False,
        **_DENIED,
    }


def open_incident(
    *, incident_id: str, signals: Iterable[Mapping[str, Any]], affected_capabilities: Iterable[str] = (),
    event_id: str, runtime_root: str | Path | None = None,
) -> dict[str, Any]:
    iid = str(incident_id or "").strip()[:160]
    token = str(event_id or "").strip()[:160]
    rows = [dict(row) for row in list(signals)[:64] if isinstance(row, Mapping)]
    if not iid or not token:
        return {"ok": False, "status": "incident_id_and_event_id_required", **_DENIED}
    retained = incident_response(rows, {"session_id": iid}, version=CONTRACT_VERSION)
    payload = retained.get("payload") if isinstance(retained.get("payload"), Mapping) else {}
    triggered = bool(payload.get("incident_triggered"))
    signal_summary = [{
        "severity": str(row.get("severity") or "unknown").lower()[:32],
        "signal_digest": _digest({"code": str(row.get("code") or ""), "severity": str(row.get("severity") or ""), "containment_failure": bool(row.get("containment_failure"))}),
    } for row in rows]
    path = _state_path(runtime_root)
    try:
        with metadata_mutation_lock(f"era8_incident:{_digest(str(path))[:24]}"):
            state, state_integrity_ok = _read_state_checked(runtime_root)
            if not state_integrity_ok:
                return {"ok": False, "status": "incident_state_integrity_invalid", **_DENIED}
            event_digest = _digest({"incident_id": iid, "event_id": token, "signals": signal_summary})
            for event in state.get("events", []):
                if isinstance(event, Mapping) and event.get("event_digest") == event_digest:
                    existing = state.get("incidents", {}).get(iid) or {}
                    return {"ok": True, "status": "incident_open_replayed", "incident": deepcopy(existing), "idempotent": True, **_DENIED}
            incident = {
                "incident_id": iid,
                "state": "contained_pending_operator" if triggered else "monitoring",
                "triggered": triggered,
                "signal_summary": signal_summary,
                "affected_capabilities": sorted({str(x or "").strip().lower()[:120] for x in affected_capabilities if str(x or "").strip()})[:64],
                "logical_capability_freeze": triggered,
                "freeze_is_policy_signal_not_os_action": True,
                "preserve_content_free_evidence": triggered,
                "operator_notification_proposal": triggered,
                "recovery_proposal_required": triggered,
                "opened_at": datetime.now(timezone.utc).isoformat(),
                "event_digest": event_digest,
                **_DENIED,
            }
            incident["incident_digest"] = _digest({k: v for k, v in incident.items() if k != "opened_at"})
            state["incidents"][iid] = incident
            state["events"] = (state.get("events", []) + [{"event_digest": event_digest, "incident_id": iid, "event": "open"}])[-MAX_EVENTS:]
            state["revision"] = int(state.get("revision") or 0) + 1
            state["contract_version"] = CONTRACT_VERSION
            write_json_atomic(path, state, expected_type=dict, sort_keys=True, coordinate=False)
            return {"ok": True, "status": "incident_opened" if triggered else "incident_monitoring_started", "incident": deepcopy(incident), "idempotent": False, "revision": state["revision"], **_DENIED}
    except (MetadataMutationBusy, AtomicJsonWriteError, OSError):
        return {"ok": False, "status": "incident_state_write_blocked", **_DENIED}


def inspect_incidents(*, runtime_root: str | Path | None = None) -> dict[str, Any]:
    state, state_integrity_ok = _read_state_checked(runtime_root)
    rows = []
    for iid, incident in sorted((state.get("incidents") or {}).items()):
        if not isinstance(incident, Mapping):
            continue
        rows.append({
            "incident_id": iid, "state": incident.get("state"), "triggered": bool(incident.get("triggered")),
            "affected_capability_count": len(incident.get("affected_capabilities") or []),
            "logical_capability_freeze": bool(incident.get("logical_capability_freeze")),
            "incident_digest": incident.get("incident_digest"),
        })
    result = {
        "ok": state_integrity_ok, "status": "incident_state_inspected" if state_integrity_ok else "incident_state_integrity_invalid", "contract_version": CONTRACT_VERSION,
        "revision": int(state.get("revision") or 0), "incident_count": len(rows), "incidents": rows,
        "raw_private_content_exposed": False, "fail_closed_required": not state_integrity_ok, **_DENIED,
    }
    result["inspection_digest"] = _digest(result)
    return result


__all__ = ["CONTRACT_VERSION", "build_audit_lineage", "validate_audit_lineage", "open_incident", "inspect_incidents"]
