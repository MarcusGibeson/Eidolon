from __future__ import annotations

"""Private operator development-finding intake with content-free planning evidence."""

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
from typing import Any, Mapping

from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock


CONTRACT_VERSION = "v2503.4.1"
MAX_FINDINGS = 128
MAX_DESCRIPTION_CHARS = 1000
_COMMAND = re.compile(r"^record development finding\s*:\s*(?P<description>.+)$", re.IGNORECASE | re.DOTALL)
_INACTIVE = frozenset({"resolved", "dismissed", "retracted"})


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str).encode("utf-8")
    ).hexdigest()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _path(runtime_root: str | Path | None = None) -> Path:
    root = Path(runtime_root or os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1] / "data").expanduser().resolve()
    return root / "development" / "operator_development_findings.json"


def _default() -> dict[str, Any]:
    return {"schema_version": "1", "contract_version": CONTRACT_VERSION, "revision": 0, "updated_at": "", "findings": []}


def _contains_any(text: str, values: tuple[str, ...]) -> bool:
    return any(
        re.search(r"(?<!\w)" + re.escape(value).replace(r"\ ", r"\s+") + r"(?!\w)", text)
        for value in values
    )


def _classification(description: str) -> tuple[str, str, str, float]:
    text = description.casefold()
    if _contains_any(text, ("secret", "security", "privacy", "credential")):
        return "security_debt", "security", "high", 0.92
    if _contains_any(text, ("slow", "latency", "performance", "response time", "speed")):
        return "performance_regression", "performance", "high", 0.86
    if _contains_any(text, (
        "bounded research", "research session", "source discovery", "source quality",
        "citation", "citations", "evidence matrix", "evidence matrices",
        "recommendation confidence", "public source", "public sources",
        "follow-up search", "follow-up searches", "free tier", "free-tier",
        "demand evidence", "competition evidence",
    )):
        return "operator_reported_defect", "bounded_research", "high", 0.9
    if _contains_any(text, ("dashboard", "button", "window", "layout", "screen", "interface", "ui")):
        return "operator_reported_defect", "interface", "high", 0.84
    if _contains_any(text, ("restart", "session", "draft", "reconnect", "continuity", "disappear")):
        return "operator_reported_defect", "session_continuity", "high", 0.88
    if _contains_any(text, ("chat", "conversation", "response", "memory", "context", "repeat", "natural")):
        return "conversation_quality_finding", "model_quality", "high", 0.88
    if _contains_any(text, ("cannot", "can't", "missing", "should be able", "capability", "feature")):
        return "missing_capability", "operator", "medium", 0.78
    return "operator_reported_defect", "operator", "medium", 0.68


def is_operator_development_finding_command(message: str) -> bool:
    return _COMMAND.fullmatch(str(message or "").strip()) is not None


def record_operator_development_finding(message: str, *, runtime_root: str | Path | None = None) -> dict[str, Any]:
    match = _COMMAND.fullmatch(str(message or "").strip())
    if match is None:
        return {"active": False}
    description = " ".join(match.group("description").split())
    if not description or len(description) > MAX_DESCRIPTION_CHARS:
        return {"active": True, "ok": False, "event": "operator_development_finding_rejected", "conversation_response": "The development finding must contain 1 to 1000 characters. Nothing was recorded.", "runtime_mutated": False}
    evidence_class, issue_domain, severity, impact = _classification(description)
    description_digest = _digest(description)
    path = _path(runtime_root)
    with metadata_mutation_lock(path, timeout_seconds=10):
        state = load_json_file(path, _default(), expected_type=dict)
        state.setdefault("findings", [])
        existing = next((row for row in state["findings"] if row.get("description_digest") == description_digest and row.get("state") not in _INACTIVE), None)
        if existing:
            current = {
                "evidence_class": evidence_class,
                "issue_domain": issue_domain,
                "severity": severity,
                "impact_score": impact,
            }
            changed = any(existing.get(key) != value for key, value in current.items())
            if changed:
                now = _now()
                existing.update(current)
                existing["updated_at"] = now
                existing["record_digest"] = _digest({
                    key: value for key, value in existing.items() if key != "private_description"
                })
                state["contract_version"] = CONTRACT_VERSION
                state["revision"] = int(state.get("revision") or 0) + 1
                state["updated_at"] = now
                write_json_atomic(path, state, expected_type=dict, sort_keys=True)
                public = _public(existing)
                return {
                    "active": True,
                    "ok": True,
                    "event": "operator_development_finding_reclassified",
                    "conversation_response": (
                        f"I reclassified existing development finding {public['finding_id']} as {evidence_class} "
                        f"in the {issue_domain} domain under the current rules. Send: Continue your supervised development."
                    ),
                    "development_finding": public,
                    "runtime_mutated": True,
                    "provider_contacted": False,
                    "source_modified": False,
                    "authority_granted": False,
                }
            public = _public(existing)
            return {"active": True, "ok": True, "event": "operator_development_finding_reused", "conversation_response": f"I reused development finding {public['finding_id']} instead of recording a duplicate. Send: Continue your supervised development.", "development_finding": public, "runtime_mutated": False}
        stable = {
            "description_digest": description_digest,
            "evidence_class": evidence_class,
            "issue_domain": issue_domain,
            "severity": severity,
            "impact_score": impact,
        }
        now = _now()
        row = {
            "finding_id": f"opfind_{_digest(stable)[:24]}",
            "private_description": description,
            **stable,
            "state": "open",
            "confidence": 0.9,
            "frequency": 1,
            "freshness": "current",
            "operator_confirmed": True,
            "created_at": now,
            "updated_at": now,
        }
        row["record_digest"] = _digest({key: value for key, value in row.items() if key != "private_description"})
        state["findings"] = (list(state["findings"]) + [row])[-MAX_FINDINGS:]
        state["revision"] = int(state.get("revision") or 0) + 1
        state["updated_at"] = now
        write_json_atomic(path, state, expected_type=dict, sort_keys=True)
    public = _public(row)
    return {
        "active": True,
        "ok": True,
        "event": "operator_development_finding_recorded",
        "conversation_response": (
            f"I recorded private development finding {public['finding_id']} as {evidence_class} in the {issue_domain} domain. "
            "Only its digest and classification enter planning evidence. No provider, proposal, workspace, test, source change, installation, or authority was created. "
            "Send: Continue your supervised development."
        ),
        "development_finding": public,
        "runtime_mutated": True,
        "provider_contacted": False,
        "source_modified": False,
        "authority_granted": False,
    }


def _public(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "finding_id": str(row.get("finding_id") or ""),
        "record_digest": str(row.get("record_digest") or ""),
        "state": str(row.get("state") or "open"),
        "evidence_class": str(row.get("evidence_class") or "operator_reported_defect"),
        "issue_domain": str(row.get("issue_domain") or "operator"),
        "severity": str(row.get("severity") or "medium"),
        "impact_score": float(row.get("impact_score") or 0.0),
        "confidence": float(row.get("confidence") or 0.0),
        "frequency": int(row.get("frequency") or 1),
        "freshness": str(row.get("freshness") or "unknown"),
        "operator_confirmed": bool(row.get("operator_confirmed")),
        "description_present": bool(row.get("private_description")),
        "description_digest": str(row.get("description_digest") or ""),
        "private_description_returned": False,
        "content_free": True,
    }


def list_operator_development_findings(*, runtime_root: str | Path | None = None) -> list[dict[str, Any]]:
    state = load_json_file(_path(runtime_root), _default(), expected_type=dict)
    return [deepcopy(_public(row)) for row in state.get("findings") or () if str(row.get("state") or "open") not in _INACTIVE]


__all__ = [
    "CONTRACT_VERSION",
    "is_operator_development_finding_command",
    "record_operator_development_finding",
    "list_operator_development_findings",
]
