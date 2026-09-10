from __future__ import annotations
"""Normalized, versioned training-example view for governed Eidolon evidence."""
import hashlib, json, re
from typing import Any, Mapping

NORMALIZED_SCHEMA_VERSION = "2"
CONTRACT_VERSION = "v2503.4.18"
_CAPABILITIES = {"coding","repair","research","planning","tool_use","governance","conversation","memory","abstention","other"}
_TASK_TO_CAPABILITY = {
    "software_development":"coding", "software_repair":"repair", "research_synthesis":"research",
    "planning":"planning", "tool_use":"tool_use", "governance":"governance", "conversation":"conversation",
}

def _canon(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode("utf-8")
def _digest(value: Any) -> str: return hashlib.sha256(_canon(value)).hexdigest()
def _text(value: Any) -> str:
    return value if isinstance(value,str) else json.dumps(value,ensure_ascii=True,sort_keys=True)
def _tokens(value: Any) -> list[str]: return re.findall(r"[a-z0-9_]+", _text(value).lower())

def normalize_training_record(record: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(record, Mapping) or not str(record.get("record_id") or "").startswith("trn_"):
        raise ValueError("invalid_training_record")
    task=str(record.get("task_type") or "other")
    prov=record.get("provenance") if isinstance(record.get("provenance"),Mapping) else {}
    capability=str(prov.get("capability") or _TASK_TO_CAPABILITY.get(task,"other"))
    if capability not in _CAPABILITIES: capability="other"
    chosen=record.get("corrected_output") if record.get("corrected_output") is not None else record.get("model_output")
    rejected=record.get("model_output") if record.get("corrected_output") is not None else None
    validation=record.get("validation") if isinstance(record.get("validation"),Mapping) else {}
    normalized={
        "schema_version": NORMALIZED_SCHEMA_VERSION,
        "record_id": str(record.get("record_id")),
        "task_type": task,
        "capability": capability,
        "source_system": str(record.get("source_system") or "eidolon"),
        "input": record.get("input_payload"),
        "chosen_output": chosen,
        "rejected_output": rejected,
        "validation": dict(validation),
        "validation_passed": bool(record.get("validation_passed") is True),
        "failure_code": str(record.get("failure_code") or "")[:120],
        "has_preference_pair": rejected is not None,
        "difficulty": max(1,min(5,int(prov.get("difficulty",2 if rejected is not None else 1) or 1))),
        "provenance": dict(prov),
        "sanitized": bool(record.get("sanitized") is True),
        "approved_for_training": bool(record.get("approved_for_training") is True),
        "runtime_only": True,
        "model_training_authorized": False,
        "model_promotion_authorized": False,
    }
    normalized["semantic_fingerprint"]=_digest({"capability":capability,"input_tokens":sorted(set(_tokens(normalized["input"]))),"chosen_tokens":sorted(set(_tokens(chosen)))})
    normalized["normalized_digest"]=_digest(normalized)
    return normalized
