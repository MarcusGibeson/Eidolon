from __future__ import annotations

"""Content-free operator controls for Era 4 memory/world-model evidence.

These controls reuse the canonical memory store and the Era 4 read-only projection.
They never expose raw memory text, browse, refresh knowledge, mutate memory/beliefs,
or grant execution authority.
"""

import re
from typing import Any

from memory import load_memories
from memory_world_model_coherence import build_memory_world_model_projection
from knowledge_freshness_maintenance import build_refresh_proposal

CONTRACT_VERSION = "v1899.9"
AUTHORITY_FLAGS = {
    "memory_mutated": False,
    "belief_mutated": False,
    "identity_mutated": False,
    "provider_contacted": False,
    "external_browsing_performed": False,
    "execution_authorized": False,
    "installation_authorized": False,
    "promotion_authorized": False,
    "authority_granted": False,
}

_SHOW = re.compile(r"^(?:show|inspect) memory world model\.?$", re.I)
_STALE = re.compile(r"^(?:show|inspect) stale knowledge\.?$", re.I)
_PREPARE = re.compile(r"^prepare knowledge refresh (?P<knowledge>[0-9a-f]{24}) at (?P<inspection>[0-9a-f]{64})\.?$", re.I)


def _projection() -> dict[str, Any]:
    records = load_memories(limit=160)
    return build_memory_world_model_projection("", records)


def inspect_memory_world_model() -> dict[str, Any]:
    p = _projection()
    return {
        "ok": bool(p.get("ok")),
        "status": "memory_world_model_inspected",
        "contract_version": CONTRACT_VERSION,
        "memory_evidence": dict((p.get("memory") or {}).get("evidence") or {}),
        "temporal_identity_evidence": dict((p.get("temporal_identity") or {}).get("evidence") or {}),
        "belief_group_count": len(p.get("belief_groups") or []),
        "knowledge_freshness": dict(p.get("knowledge_freshness") or {}),
        "raw_memory_exposed": False,
        **AUTHORITY_FLAGS,
    }


def inspect_stale_knowledge() -> dict[str, Any]:
    p = _projection()
    k = dict(p.get("knowledge_freshness") or {})
    return {
        "ok": bool(p.get("ok")),
        "status": "stale_knowledge_inspected",
        "contract_version": CONTRACT_VERSION,
        "inspection": k,
        "raw_memory_exposed": False,
        **AUTHORITY_FLAGS,
    }


def prepare_refresh(knowledge_digest: str, inspection_digest: str) -> dict[str, Any]:
    p = _projection()
    k = dict(p.get("knowledge_freshness") or {})
    current = str(k.get("inspection_digest") or "")
    if inspection_digest.lower() != current.lower():
        return {
            "ok": False,
            "status": "stale_knowledge_inspection_digest",
            "current_inspection_digest": current,
            **AUTHORITY_FLAGS,
        }
    matches = [c for c in (k.get("refresh_candidates") or []) if str(c.get("knowledge_digest") or "").lower() == knowledge_digest.lower()]
    if len(matches) != 1:
        return {"ok": False, "status": "knowledge_refresh_candidate_not_unique", **AUTHORITY_FLAGS}
    proposal = build_refresh_proposal(matches[0])
    return {
        "ok": True,
        "status": "knowledge_refresh_proposal_prepared",
        "contract_version": CONTRACT_VERSION,
        "proposal": proposal,
        "refresh_completed": False,
        "raw_memory_exposed": False,
        **AUTHORITY_FLAGS,
    }


def process_memory_world_model_control(user_text: str) -> dict[str, Any]:
    text = str(user_text or "").strip()
    lowered = text.lower()
    if any(token in lowered for token in (" and install", " and promote", " and execute", " and delete", " and browse", " and refresh it")) and any(key in lowered for key in ("memory world model", "stale knowledge", "knowledge refresh")):
        return {"active": True, "ok": False, "status": "read_only_scope_expansion_rejected", **AUTHORITY_FLAGS}
    if _SHOW.fullmatch(text):
        return {"active": True, **inspect_memory_world_model()}
    if _STALE.fullmatch(text):
        return {"active": True, **inspect_stale_knowledge()}
    match = _PREPARE.fullmatch(text)
    if match:
        return {"active": True, **prepare_refresh(match.group("knowledge"), match.group("inspection"))}
    return {"active": False}


__all__ = [
    "CONTRACT_VERSION", "AUTHORITY_FLAGS", "inspect_memory_world_model", "inspect_stale_knowledge",
    "prepare_refresh", "process_memory_world_model_control",
]
