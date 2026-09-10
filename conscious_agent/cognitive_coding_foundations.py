from __future__ import annotations

"""v1290.0-v1290.2 cognitive-coding benchmark evidence foundations.

This module coordinates evidence from the existing supervised coding lineage.  It
is deliberately non-executing: project mutation, provider contact, diagnostics,
tests, application, update, and release remain owned by their established
boundaries.  v1290 records whether a coding campaign actually revised a mistaken
assumption and selected useful evidence rather than merely accumulating green
receipts.
"""
from hashlib import sha256
import json
from typing import Any, Iterable, Mapping

CONTRACT_VERSION = "v1290.2"
MIN_MULTI_FILE_CHANGE = 2
DENIED_AUTHORITY = {
    "provider_contact_authorized": False, "command_execution_authorized": False,
    "test_execution_authorized": False, "diagnostic_execution_authorized": False,
    "repair_authorized": False, "project_mutation_authorized": False,
    "source_application_authorized": False, "installation_authorized": False,
    "self_update_authorized": False, "rollback_authorized": False,
    "release_authorized": False, "standing_authority_granted": False,
}
ARCHITECTURE_LINEAGE = {
    "isolated_coding": "v1254", "persistent_sessions": "v1256",
    "diagnostic_reasoning": "v1257", "test_selection": "v1266",
    "product_quality": "v1289",
}


def digest(value: Any) -> str:
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def _hex64(value: Any, label: str) -> str:
    text = str(value or "").lower().strip()
    if len(text) != 64 or any(ch not in "0123456789abcdef" for ch in text):
        raise ValueError(label)
    return text


def create_cognitive_coding_campaign(*, objective_digest: str, project_manifest_digest: str, project_file_count: int,
                                     initial_assumptions: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    objective = _hex64(objective_digest, "objective_digest_required")
    project = _hex64(project_manifest_digest, "project_manifest_digest_required")
    assumptions=[]; seen=set()
    for raw in initial_assumptions:
        code=str(raw.get("assumption_code") or "").strip()
        if not code or code in seen: continue
        seen.add(code)
        evidence_digest=_hex64(raw.get("evidence_digest"), "assumption_evidence_digest_required")
        assumptions.append({"assumption_code":code,"state":"active","evidence_digest":evidence_digest,"content_free":True})
    if not assumptions: raise ValueError("initial_assumption_required")
    base={
        "contract_version":CONTRACT_VERSION,"objective_digest":objective,"project_manifest_digest":project,
        "project_file_count":max(0,int(project_file_count)),"initial_assumptions":assumptions,
        "assumption_revisions":[],"diagnostic_selections":[],"implementation_evidence":[],"verification_evidence":[],
        "continuity_events":[],"content_free":True,"read_only_coordinator":True,
        "architecture_lineage":dict(ARCHITECTURE_LINEAGE),**DENIED_AUTHORITY,
    }
    base["campaign_id"]="cognitive-coding-"+digest({"objective":objective,"project":project})[:20]
    base["campaign_digest"]=digest(base)
    return base


def record_assumption_revision(campaign: Mapping[str, Any], *, assumption_code: str, outcome: str,
                               contradicting_evidence_digest: str, replacement_assumption_code: str = "") -> dict[str, Any]:
    if str(outcome) not in {"revised","rejected","suspended"}: raise ValueError("revision_outcome_invalid")
    evidence=_hex64(contradicting_evidence_digest,"revision_evidence_digest_required")
    code=str(assumption_code or "").strip(); active={x.get("assumption_code") for x in campaign.get("initial_assumptions") or []}
    if code not in active: raise ValueError("unknown_assumption")
    row={"assumption_code":code,"outcome":str(outcome),"contradicting_evidence_digest":evidence,
         "replacement_assumption_code":str(replacement_assumption_code or "").strip(),"content_free":True}
    row["revision_digest"]=digest(row)
    return row


def select_discriminating_diagnostics(campaign: Mapping[str, Any], candidates: Iterable[Mapping[str, Any]], *, max_count: int = 4) -> list[dict[str, Any]]:
    """Select bounded diagnostics that distinguish at least two competing explanations.

    Selection is evidence-only.  The returned rows never execute probes.
    """
    rows=[]; seen=set()
    for raw in candidates:
        code=str(raw.get("probe_code") or "").strip(); predictions=tuple(sorted({str(x) for x in raw.get("distinguishes") or [] if str(x)}))
        if not code or code in seen or len(predictions)<2: continue
        seen.add(code)
        cost=max(0,min(100,int(raw.get("cost",50)))); info=max(0,min(100,int(raw.get("information_gain",0))))
        row={"probe_code":code,"distinguishes":predictions,"cost":cost,"information_gain":info,
             "selection_score":info*2-cost,"probe_digest":digest({"probe_code":code,"distinguishes":predictions}),
             "executed":False,"content_free":True,**DENIED_AUTHORITY}
        rows.append(row)
    rows.sort(key=lambda r:(-r["selection_score"],r["probe_code"]))
    return rows[:max(1,min(8,int(max_count)))]


def continuity_event(campaign: Mapping[str, Any], *, stage: str, evidence_digest: str, previous_event_digest: str = "") -> dict[str, Any]:
    evidence=_hex64(evidence_digest,"continuity_evidence_digest_required")
    prev=str(previous_event_digest or "")
    if prev: _hex64(prev,"previous_event_digest_invalid")
    row={"campaign_id":campaign.get("campaign_id"),"objective_digest":campaign.get("objective_digest"),
         "project_manifest_digest":campaign.get("project_manifest_digest"),"stage":str(stage or "").strip(),
         "evidence_digest":evidence,"previous_event_digest":prev,"content_free":True}
    if not row["stage"]: raise ValueError("continuity_stage_required")
    row["event_digest"]=digest(row)
    return row
