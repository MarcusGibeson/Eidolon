from __future__ import annotations

"""v2506.0-v2506.1 typed memory-role projection over retained unified memory.

This does not create a new memory store. It classifies provenance-preserving
references from the established v1165 unified memory projection into cognitive
roles useful to consolidation: episodic, semantic, relational, procedural, and
Eidolon-autobiographical.
"""

from copy import deepcopy
import hashlib
import json
from typing import Any, Mapping, Sequence

CONTRACT_VERSION = "v2506.1"
MEMORY_ROLES = ("episodic", "semantic", "relational", "procedural", "autobiographical")


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()


def _role(reference: Mapping[str, Any]) -> str:
    domain = str(reference.get("domain") or "").strip().lower()
    ownership = str(reference.get("ownership") or "").strip().lower()
    source = str(reference.get("source") or "").strip().lower()
    if domain == "relationship":
        return "relational"
    if any(token in source for token in ("lesson", "procedure", "repair", "development_outcome", "workflow", "skill")):
        return "procedural"
    if ownership == "eidolon" or any(token in source for token in ("reflection", "self_model", "identity", "eidolon")):
        return "autobiographical"
    if domain == "semantic":
        return "semantic"
    return "episodic"


def build_unified_memory_role_projection(unified_projection: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(unified_projection, Mapping):
        raise ValueError("unified memory projection required")
    policy = unified_projection.get("policy") if isinstance(unified_projection.get("policy"), Mapping) else {}
    evidence = unified_projection.get("evidence") if isinstance(unified_projection.get("evidence"), Mapping) else {}
    refs = unified_projection.get("selected_references")
    if not isinstance(refs, Sequence) or isinstance(refs, (str, bytes, bytearray)):
        refs = []
    if policy.get("policy_recovered"):
        refs = []
    rows=[]; counts={role:0 for role in MEMORY_ROLES}
    for ref in list(refs)[:96]:
        if not isinstance(ref, Mapping):
            continue
        role=_role(ref); counts[role]+=1
        rows.append({
            "role":role,
            "reference_key":str(ref.get("reference_key") or "")[:96],
            "content_digest":str(ref.get("content_digest") or "")[:64],
            "source":str(ref.get("source") or "")[:80],
            "ownership":str(ref.get("ownership") or "")[:24],
            "confidence_band":str(ref.get("confidence_band") or "unknown")[:16],
            "age_band":str(ref.get("age_band") or "unknown")[:16],
            "domain":str(ref.get("domain") or "")[:24],
        })
    public={
        "contract_version":CONTRACT_VERSION,
        "roles":list(MEMORY_ROLES),
        "role_counts":counts,
        "reference_count":len(rows),
        "references":rows,
        "source_evidence_digest":str(evidence.get("evidence_digest") or ""),
        "conflict_groups_detected":int(evidence.get("conflict_groups_detected") or 0),
        "duplicate_references_omitted":int(evidence.get("duplicate_references_omitted") or 0),
        "provenance_complete":bool(evidence.get("provenance_complete")),
        "memory_mutated":False,
        "provider_contacted":False,
        "contains_memory_text":False,
        "contains_private_reasoning":False,
        "authority":"none",
    }
    public["projection_digest"]=_digest(public)
    return public


def verify_unified_memory_role_projection(value: Mapping[str, Any]) -> bool:
    if not isinstance(value, Mapping):return False
    supplied=str(value.get("projection_digest") or "")
    unsigned={k:v for k,v in value.items() if k!="projection_digest"}
    return bool(len(supplied)==64 and _digest(unsigned)==supplied and value.get("memory_mutated") is False and value.get("authority")=="none")


__all__=["CONTRACT_VERSION","MEMORY_ROLES","build_unified_memory_role_projection","verify_unified_memory_role_projection"]
