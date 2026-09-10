from __future__ import annotations

"""Bounded provider-free relevance and stale-memory suppression for v1166."""

from dataclasses import dataclass, asdict
import hashlib, json, re
from datetime import datetime, timezone
from typing import Any, Mapping, Sequence

CONTRACT_VERSION = "1166.8"
MAX_CANDIDATES = 80
MAX_SELECTED = 12
MAX_ARCHIVAL_SELECTED = 2
MAX_PROMPT_CHARS = 3200
MAX_PRIOR_RECEIPTS = 12
MAX_RECEIPT_COLLECTION = 40
MAX_MESSAGE_CHARS = 4000
MAX_REFERENCE_COLLECTION = 80
MAX_AUDIT_RECORDS = 80
_STOP = {"the","and","that","this","with","from","into","your","you","our","are","was","were","have","has","had","for","about","please","would","could","should","what","when","where","which","who","why","how"}
_AGE = {"current":4,"recent":3,"historical":1,"archival":0,"unknown":0}
_CONF = {"high":3,"medium":2,"low":1,"unknown":0}
_AUTHORITY = {"approval_granted","authorized","execute","execution_permitted","tool_use_permitted","installation_permitted","promotion_permitted","certification_permitted"}
_PRIVATE = {"private_chain_of_thought","chain_of_thought","hidden_reasoning","provider_payload","raw_prompt","raw_provider_response"}

def _digest(v: object) -> str:
    return hashlib.sha256(json.dumps(v, sort_keys=True, separators=(",",":"), default=str).encode()).hexdigest()

def _words(v: object) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9_]+", str(v or "").lower()) if len(w)>=3 and w not in _STOP}


def _parse_time(value: object) -> datetime | None:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    token = str(value or "").strip()
    if not token:
        return None
    try:
        parsed = datetime.fromisoformat(token.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        return None

def _prior_retrieval_receipts(rows: object, now: datetime) -> dict[str, Any]:
    if rows is None:
        rows = ()
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes, bytearray)):
        return {"verified":0,"stale":0,"rejected":1,"replayed":0,"oversized":0,"recovery":"malformed_receipt_collection"}
    if len(rows) > MAX_RECEIPT_COLLECTION:
        return {"verified":0,"stale":0,"rejected":0,"replayed":0,"oversized":len(rows)-MAX_RECEIPT_COLLECTION,"recovery":"oversized_receipt_collection"}
    verified=stale=rejected=replayed=0; seen=set()
    for row in list(rows)[-MAX_PRIOR_RECEIPTS:]:
        if not isinstance(row, Mapping):
            rejected += 1; continue
        candidate=row.get("memory_retrieval_runtime_diagnostics")
        if not isinstance(candidate, Mapping):
            cc=row.get("cognitive_context")
            candidate=cc.get("memory_retrieval_runtime_diagnostics") if isinstance(cc, Mapping) else None
        if not isinstance(candidate, Mapping):
            continue
        candidate=dict(candidate)
        if not verify_memory_retrieval_diagnostics(candidate):
            rejected += 1; continue
        digest=str(candidate.get("diagnostics_digest") or "")
        if digest in seen:
            replayed += 1; continue
        seen.add(digest)
        created=_parse_time(row.get("created_at") or row.get("timestamp"))
        if created is not None and (now-created).total_seconds() > 7*86400:
            stale += 1; continue
        verified += 1
    recovery="invalid_prior_receipt" if rejected else ("replayed_prior_receipt" if replayed else ("stale_prior_receipt" if stale and not verified else "none"))
    return {"verified":verified,"stale":stale,"rejected":rejected,"replayed":replayed,"oversized":0,"recovery":recovery}

def _text(row: Mapping[str, Any]) -> str:
    return " ".join(str(row.get(k) or "") for k in ("content","summary","title","name","description","value","type","source"))[:1200]

def _band(row: Mapping[str, Any], key: str, allowed: set[str], default: str) -> str:
    token = str(row.get(key) or default).lower()
    return token if token in allowed else default

@dataclass(frozen=True)
class RetrievalDecision:
    candidate_index: int
    relevance_score: int
    freshness_score: int
    confidence_score: int
    direct_match: bool
    stale_suppressed: bool
    selected: bool
    reason: str
    def to_dict(self) -> dict[str, Any]: return asdict(self)

def build_memory_retrieval_relevance(message: object, records: object, references: object = None, prior_retrieval_receipts: object = None, now: datetime | None = None) -> dict[str, Any]:
    current_time = now or datetime.now(timezone.utc)
    prior = _prior_retrieval_receipts(prior_retrieval_receipts, current_time)
    message_text = str(message or "")
    oversized_message = len(message_text) > MAX_MESSAGE_CHARS
    if not isinstance(records, Sequence) or isinstance(records,(str,bytes,bytearray)):
        records = []; malformed_collection = True; oversized_collection = False
    else:
        oversized_collection = len(records) > MAX_CANDIDATES
        records = list(records)[:MAX_CANDIDATES]; malformed_collection = False
    malformed_references = references is not None and (not isinstance(references, Sequence) or isinstance(references,(str,bytes,bytearray)))
    oversized_references = isinstance(references, Sequence) and not isinstance(references,(str,bytes,bytearray)) and len(references) > MAX_REFERENCE_COLLECTION
    refs = list(references)[:MAX_CANDIDATES] if isinstance(references, Sequence) and not isinstance(references,(str,bytes,bytearray)) else []
    query = _words(message_text[:MAX_MESSAGE_CHARS])
    ranked=[]; malformed=authority=private=0
    for i,row in enumerate(records):
        if not isinstance(row, Mapping): malformed += 1; continue
        if any(k in row and row.get(k) not in {False,None,"",0} for k in _AUTHORITY): authority += 1; continue
        if any(k in row for k in _PRIVATE): private += 1; continue
        ref = refs[i] if i < len(refs) and isinstance(refs[i], Mapping) else {}
        overlap=len(query & _words(_text(row))); direct=overlap>0
        rel=min(20, overlap*4 + int(ref.get("relevance_score") or 0))
        age=_band(ref,"age_band",set(_AGE),"unknown"); conf=_band(ref,"confidence_band",set(_CONF),"unknown")
        correction=bool(ref.get("explicit_correction") or row.get("operator_correction") or row.get("explicit_correction"))
        fact_key=str(row.get("fact_key") or row.get("subject_key") or row.get("preference_key") or "")[:120]
        tier=3 if direct else (2 if rel>=4 else 1)
        score=(tier*1000)+(rel*10)+(_AGE[age]*3)+(_CONF[conf]*2)+(25 if correction else 0)
        ranked.append((score,i,dict(row),age,conf,rel,direct,correction,fact_key,tier))
    # Newer evidence with the same explicit fact key suppresses stale alternatives without rewriting either record.
    newest_by_fact={}
    for item in ranked:
        *_, age, conf, rel, direct, correction, fact_key, tier = item[2:]
        if fact_key and age in {"current","recent"}: newest_by_fact[fact_key]=True
    ranked.sort(key=lambda x:(x[0],-x[1]), reverse=True)
    selected=[]; decisions=[]; archival_selected=0; stale_suppressed=0; stale_conflicts=0
    for score,i,row,age,conf,rel,direct,correction,fact_key,tier in ranked:
        stale_conflict=bool(fact_key and newest_by_fact.get(fact_key) and age in {"historical","archival","unknown"} and not correction)
        stale = stale_conflict or (age in {"archival","unknown"} and not correction and rel < 4)
        if stale:
            stale_suppressed += 1; stale_conflicts += int(stale_conflict)
            decisions.append(RetrievalDecision(i,rel,_AGE[age],_CONF[conf],direct,True,False,"stale_conflict" if stale_conflict else "stale_low_relevance").to_dict()); continue
        if age=="archival" and not correction and archival_selected>=MAX_ARCHIVAL_SELECTED:
            stale_suppressed += 1; decisions.append(RetrievalDecision(i,rel,_AGE[age],_CONF[conf],direct,True,False,"archival_budget").to_dict()); continue
        if len(selected)>=MAX_SELECTED:
            decisions.append(RetrievalDecision(i,rel,_AGE[age],_CONF[conf],direct,False,False,"selection_budget").to_dict()); continue
        if age=="archival": archival_selected += 1
        selected.append(row)
        reason="explicit_correction" if correction else ("literal_relevance" if direct else ("supported_relevance" if tier==2 else "bounded_context"))
        decisions.append(RetrievalDecision(i,rel,_AGE[age],_CONF[conf],direct,False,True,reason).to_dict())
    degraded=bool(malformed_collection or oversized_collection or malformed_references or oversized_references or oversized_message or malformed or authority or private or prior["rejected"] or prior["oversized"])
    if degraded: selected=[]
    continuity="recover_literal_request" if degraded else ("resume_verified_retrieval_context" if prior["verified"] and selected else "use_current_retrieval")
    evidence={"contract_version":CONTRACT_VERSION,"candidate_count":len(records),"selected_count":len(selected),"stale_suppressed_count":stale_suppressed,"stale_conflict_suppressed_count":stale_conflicts,"archival_selected_count":archival_selected,"malformed_count":malformed,"malformed_collection":malformed_collection,"oversized_collection":oversized_collection,"malformed_references":malformed_references,"oversized_references":oversized_references,"oversized_message":oversized_message,"authority_violation_count":authority,"private_field_violation_count":private,"prior_receipts_verified":prior["verified"],"prior_receipts_stale":prior["stale"],"prior_receipts_rejected":prior["rejected"],"prior_receipts_replayed":prior["replayed"],"literal_query_terms_present":bool(query),"provider_contacted":False,"memory_mutated":False,"contains_memory_text":False,"contains_private_reasoning":False,"authority":"none","integrity":"degraded" if degraded else "valid"}
    evidence["evidence_digest"]=_digest(evidence)
    policy={"contract_version":CONTRACT_VERSION,"retrieval_posture":"literal_request_only_recovery" if degraded else ("relevant_memory_grounded" if selected else "current_request_without_memory"),"continuity_disposition":continuity,"selected_count":len(selected),"stale_suppressed_count":stale_suppressed,"stale_conflict_suppressed_count":stale_conflicts,"archival_selected_count":archival_selected,"prior_receipts_verified":prior["verified"],"prior_receipts_stale":prior["stale"],"prior_receipts_rejected":prior["rejected"],"prior_receipts_replayed":prior["replayed"],"max_selected":MAX_SELECTED,"max_archival_selected":MAX_ARCHIVAL_SELECTED,"current_message_precedence":True,"stale_memory_may_dominate":False,"memory_mutation_permitted":False,"learning_mutation_permitted":False,"tool_use_permitted":False,"action_execution_permitted":False,"approval_granted":False,"authority":"none","policy_recovered":degraded,"recovery_reason":prior["recovery"] if degraded and prior["recovery"]!="none" else ("oversized_message" if oversized_message else ("oversized_retrieval_collection" if oversized_collection else ("invalid_reference_collection" if malformed_references or oversized_references else ("invalid_retrieval_input" if degraded else "none")))),"content_free":True,"evidence_digest":evidence["evidence_digest"]}
    policy["policy_digest"]=_digest(policy)
    prompt='<memory_retrieval_relevance data_only="true" authority="none">'+json.dumps(policy,sort_keys=True,separators=(",",":"))+'</memory_retrieval_relevance>'
    diagnostics={k:policy[k] for k in ("contract_version","retrieval_posture","continuity_disposition","selected_count","stale_suppressed_count","stale_conflict_suppressed_count","archival_selected_count","prior_receipts_verified","prior_receipts_stale","prior_receipts_rejected","prior_receipts_replayed","policy_recovered","recovery_reason","authority","content_free","policy_digest")}
    diagnostics.update({"candidate_count":len(records),"malformed_collection":malformed_collection,"oversized_collection":oversized_collection,"malformed_references":malformed_references,"oversized_references":oversized_references,"oversized_message":oversized_message,"provider_contacted":False,"memory_mutated":False}); diagnostics["diagnostics_digest"]=_digest(diagnostics)
    return {"policy":policy,"evidence":evidence,"diagnostics":diagnostics,"prompt_section":prompt,"selected_memory_records":selected,"decisions":decisions}

def verify_memory_retrieval_diagnostics(value: object) -> bool:
    if not isinstance(value, Mapping): return False
    supplied=str(value.get("diagnostics_digest") or "")
    unsigned={k:v for k,v in value.items() if k!="diagnostics_digest"}
    return len(supplied)==64 and _digest(unsigned)==supplied and value.get("authority")=="none" and value.get("content_free") is True and value.get("provider_contacted") is False and value.get("memory_mutated") is False


def audit_memory_retrieval_selection(result: object) -> dict[str, Any]:
    """Return content-free structural compliance evidence for a retrieval result."""
    invalid_result = not isinstance(result, Mapping)
    selected = result.get("selected_memory_records", ()) if isinstance(result, Mapping) else ()
    decisions = result.get("decisions", ()) if isinstance(result, Mapping) else ()
    policy = result.get("policy", {}) if isinstance(result, Mapping) else {}
    malformed_selected = 0
    authority_violations = 0
    private_field_violations = 0
    if not isinstance(selected, Sequence) or isinstance(selected, (str, bytes, bytearray)):
        selected = (); malformed_selected = 1
    else:
        selected = list(selected)[:MAX_AUDIT_RECORDS]
        malformed_selected = sum(1 for row in selected if not isinstance(row, Mapping))
        for row in selected:
            if not isinstance(row, Mapping):
                continue
            authority_violations += int(any(k in row and row.get(k) not in {False,None,"",0} for k in _AUTHORITY))
            private_field_violations += int(any(k in row for k in _PRIVATE))
    decision_mismatch = 0
    if isinstance(decisions, Sequence) and not isinstance(decisions, (str, bytes, bytearray)):
        selected_decisions = sum(1 for d in decisions[:MAX_AUDIT_RECORDS] if isinstance(d, Mapping) and d.get("selected") is True)
        decision_mismatch = int(selected_decisions != len(selected))
    else:
        decision_mismatch = 1
    recovered_with_selection = int(bool(isinstance(policy, Mapping) and policy.get("policy_recovered")) and len(selected) > 0)
    selection_budget_violation = int(len(selected) > MAX_SELECTED)
    archival_budget_violation = int(isinstance(policy, Mapping) and int(policy.get("archival_selected_count") or 0) > MAX_ARCHIVAL_SELECTED)
    compliant = not any((invalid_result, malformed_selected, authority_violations, private_field_violations, decision_mismatch, recovered_with_selection, selection_budget_violation, archival_budget_violation))
    audit = {
        "contract_version": CONTRACT_VERSION,
        "selected_count": len(selected),
        "malformed_selected_count": malformed_selected,
        "authority_violation_count": authority_violations,
        "private_field_violation_count": private_field_violations,
        "decision_mismatch_count": decision_mismatch,
        "recovered_with_selection_count": recovered_with_selection,
        "selection_budget_violation_count": selection_budget_violation,
        "archival_budget_violation_count": archival_budget_violation,
        "compliant": compliant,
        "contains_memory_text": False,
        "contains_private_reasoning": False,
        "authority": "none",
    }
    audit["audit_digest"] = _digest(audit)
    return audit

def verify_memory_retrieval_audit(value: object) -> bool:
    if not isinstance(value, Mapping): return False
    supplied = str(value.get("audit_digest") or "")
    unsigned = {k:v for k,v in value.items() if k != "audit_digest"}
    return len(supplied) == 64 and _digest(unsigned) == supplied and value.get("authority") == "none" and value.get("contains_memory_text") is False and value.get("contains_private_reasoning") is False
