from __future__ import annotations

"""Integrated Era 4 memory/world-model projection for ordinary conversation."""

import hashlib
import json
from typing import Any, Mapping, Sequence

try:
    from memory_coherence import build_memory_coherence_projection, classify_memory_record
    from temporal_identity_coherence import build_temporal_identity_projection
    from knowledge_freshness_maintenance import inspect_knowledge_freshness
    from revisable_belief_world_model import assess_belief_evidence
except ImportError:
    from memory_coherence import build_memory_coherence_projection, classify_memory_record
    from temporal_identity_coherence import build_temporal_identity_projection
    from knowledge_freshness_maintenance import inspect_knowledge_freshness
    from revisable_belief_world_model import assess_belief_evidence

CONTRACT_VERSION = "v1899.9"
MAX_BELIEF_GROUPS = 12


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()


def _belief_groups(records: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[Mapping[str, Any]]] = {}
    for row in records:
        cls = classify_memory_record(row)
        if cls not in {"semantic", "correction"} and "belief" not in str(row.get("type") or "").lower():
            continue
        key = str(row.get("fact_key") or row.get("semantic_subject_key") or row.get("subject_key") or "").strip()
        if not key:
            continue
        grouped.setdefault(key[:160], []).append(row)
    output = []
    for key, rows in list(grouped.items())[:MAX_BELIEF_GROUPS]:
        # Use the newest proposition as the current candidate while retaining opposing rows as evidence.
        candidate = rows[-1]
        proposition = str(candidate.get("content") or candidate.get("summary") or candidate.get("value") or "").strip()[:600]
        if not proposition:
            continue
        evidence_rows = []
        for index, row in enumerate(rows):
            source = dict(row)
            source.setdefault("id", str(row.get("id") or row.get("memory_id") or f"group:{index}"))
            if row is candidate:
                source.setdefault("stance", "supports")
            elif str(row.get("status") or "").lower() in {"superseded", "retracted"}:
                source.setdefault("stance", "contextualizes")
            elif str(row.get("stance") or "") not in {"supports", "contradicts", "contextualizes"}:
                older_text = str(row.get("content") or row.get("summary") or row.get("value") or "").strip().casefold()
                source["stance"] = "supports" if older_text == proposition.casefold() else "contradicts"
            evidence_rows.append(source)
        assessment = assess_belief_evidence(proposition, evidence_rows)
        output.append({
            "subject_digest": _digest(key)[:24],
            "proposition_digest": _digest(proposition)[:24],
            "state": assessment["state"],
            "confidence": assessment["confidence"],
            "counted_evidence": assessment["counted_evidence"],
            "source_disagreement": assessment["source_disagreement"],
            "assistant_authored_rejected_count": assessment["assistant_authored_rejected_count"],
            "raw_proposition_exposed": False,
        })
    return output


def build_memory_world_model_projection(message: object, records: object) -> dict[str, Any]:
    memory = build_memory_coherence_projection(message, records)
    selected = memory.get("selected_memory_records") if isinstance(memory.get("selected_memory_records"), list) else []
    temporal = build_temporal_identity_projection(selected)
    knowledge = inspect_knowledge_freshness(selected)
    beliefs = _belief_groups([row for row in selected if isinstance(row, Mapping)])
    evidence = {
        "contract_version": CONTRACT_VERSION,
        "selected_memory_count": len(selected),
        "memory_class_counts": dict((memory.get("evidence") or {}).get("class_counts") or {}),
        "memory_conflict_exception_count": int((memory.get("evidence") or {}).get("conflict_exception_preserved_count") or 0),
        "timeline_event_count": int((temporal.get("evidence") or {}).get("timeline_event_count") or 0),
        "ambiguous_alias_count": int((temporal.get("evidence") or {}).get("ambiguous_alias_count") or 0),
        "belief_group_count": len(beliefs),
        "contested_belief_group_count": sum(1 for b in beliefs if b.get("state") == "contested"),
        "stale_knowledge_count": int(knowledge.get("stale_count") or 0),
        "refresh_candidate_count": int(knowledge.get("refresh_candidate_count") or 0),
        "memory_mutated": False,
        "belief_mutated": False,
        "identity_mutated": False,
        "external_browsing_performed": False,
        "provider_contacted": False,
        "authority": "none",
        "raw_memory_text_exposed": False,
    }
    evidence["evidence_digest"] = _digest(evidence)
    prompt_section = (
        '<memory_world_model_policy data_only="true" authority="none">'
        + json.dumps({
            "use_selected_memory_only": True,
            "explicit_corrections_outrank_superseded_records": True,
            "preserve_conflicting_exceptions": True,
            "ambiguous_aliases_must_remain_ambiguous": True,
            "stale_knowledge_must_not_be_presented_as_current_without_current_evidence": True,
            "assistant_authored_material_is_not_independent_historical_evidence": True,
        }, sort_keys=True, separators=(",", ":"))
        + '</memory_world_model_policy>'
    )
    return {
        "ok": bool(memory.get("ok")) and bool(temporal.get("ok")),
        "contract_version": CONTRACT_VERSION,
        "selected_memory_records": selected,
        "memory": memory,
        "temporal_identity": temporal,
        "belief_groups": beliefs,
        "knowledge_freshness": knowledge,
        "evidence": evidence,
        "prompt_section": prompt_section,
        "authority_boundary": {"can_mutate_memory": False, "can_mutate_belief": False, "can_merge_identity": False, "can_browse": False, "can_authorize": False, "can_execute": False},
    }


__all__ = ["CONTRACT_VERSION", "build_memory_world_model_projection"]
