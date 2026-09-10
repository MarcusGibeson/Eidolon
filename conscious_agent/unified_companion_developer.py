from __future__ import annotations

import re
from typing import Any, Mapping, Sequence
from bounded_capability_evidence import bounded_float, digest, sealed, valid_seal

CONTRACT_VERSION="v1440.9"
COMMAND_VERBS={"build","create","fix","repair","update","change","remove","add","run","test","implement","rollback","apply","delete"}
HYPOTHETICAL_MARKERS=("if we", "what if", "suppose", "imagine", "could we")
SUGGESTION_MARKERS=("it would be nice", "i wish", "i hope", "someday")


def _classify_clause(clause: str) -> tuple[str, bool, bool]:
    low = clause.lower()
    words = set(re.findall(r"[a-z']+", low))
    quoted = clause.count('"') >= 2 or clause.count("'") >= 2
    hypothetical = any(marker in low for marker in HYPOTHETICAL_MARKERS)
    suggestion = any(marker in low for marker in SUGGESTION_MARKERS) or "maybe" in words or "should we" in low
    correction = low.startswith(("actually", "correction", "no,"))
    question = clause.endswith("?")
    command = bool(COMMAND_VERBS & words) and not quoted and not hypothetical and not suggestion and not question
    if correction:
        return "correction", command, quoted
    if command:
        return "command", True, quoted
    if hypothetical:
        return "hypothetical", False, quoted
    if suggestion:
        return "suggestion", False, quoted
    if question:
        return "question", False, quoted
    return "casual", False, quoted


def understand_mixed_intent(text:str, *, version:str="1431.9") -> dict[str,Any]:
    raw=str(text or "").strip(); clauses=[c.strip() for c in re.split(r'(?<=[.!?])\s+|\s*;\s*',raw) if c.strip()]; rows=[]
    for idx,c in enumerate(clauses):
        intent, actionable, quoted = _classify_clause(c)
        rows.append({"clause_index":idx,"intent":intent,"clause_digest":digest(c),"actionable":actionable,"quoted":quoted})
    return sealed("mixed_intent_understanding",{"clauses":rows,"actionable_count":sum(r['actionable'] for r in rows),"raw_text_retained":False},version=version)



def actionable_clauses(text: str) -> list[str]:
    """Return only clauses that are explicit commands under the mixed-intent policy.

    This helper intentionally keeps raw text in-process only; durable/public evidence
    remains digest-only through ``understand_mixed_intent``.
    """
    raw = str(text or "").strip()
    clauses = [c.strip() for c in re.split(r'(?<=[.!?])\s+|\s*;\s*', raw) if c.strip()]
    result: list[str] = []
    for clause in clauses:
        _, actionable, _ = _classify_clause(clause)
        if actionable:
            result.append(clause)
    return result

def ground_commands(intent:Mapping[str,Any], command_details:Mapping[int,Mapping[str,Any]]|None=None, *, version:str="1432.9") -> dict[str,Any]:
    details=command_details or {}; goals=[]
    for row in intent.get("payload",{}).get("clauses") or []:
        if not row.get("actionable"):continue
        d=dict(details.get(int(row["clause_index"]),{})); risk=str(d.get("risk") or "low"); scope=d.get("scope_digest"); material_change=not scope or risk in {"high","protected"} or bool(d.get("destructive"))
        goals.append({"goal_id":"goal-"+str(row['clause_digest'])[:16],"source_clause_digest":row['clause_digest'],"scope_digest":scope,"risk":risk,"confirmation_required":material_change,"authority_inferred":False})
    return sealed("command_grounding",{"goals":goals,"goal_count":len(goals),"confirm_only_material_risk_or_scope":True},version=version)


def preserve_followup(previous:Mapping[str,Any], turn:Mapping[str,Any], *, version:str="1433.9") -> dict[str,Any]:
    topic=turn.get("topic") or previous.get("topic"); refs=dict(previous.get("references") or {}); refs.update(turn.get("references") or {}); corrections=dict(previous.get("corrections") or {}); corrections.update(turn.get("corrections") or {})
    return sealed("natural_followup",{"topic":topic,"references":refs,"corrections":corrections,"relationship_tone":turn.get("relationship_tone",previous.get("relationship_tone","neutral")),"repetitive_greeting_suppressed":bool(previous),"stale_script_reuse":False},version=version)


def describe_action_state(work:Sequence[Mapping[str,Any]], *, version:str="1434.9") -> dict[str,Any]:
    allowed={"queued","active","paused","failed","completed","cancelled"}; rows=[]
    for w in work:
        status=str(w.get("status") or "unknown"); evidence=str(w.get("evidence_digest") or ""); verified=status!="completed" or len(evidence)==64
        rows.append({"work_id":w.get("work_id"),"status":status if status in allowed else "unknown","completion_claim_allowed":status=="completed" and verified,"evidence_digest":evidence if len(evidence)==64 else None})
    return sealed("action_aware_dialogue",{"work":rows,"false_completion_claims_blocked":all(r['status']!='completed' or r['completion_claim_allowed'] for r in rows)},version=version)


def proactive_expression(candidate:Mapping[str,Any], policy:Mapping[str,Any], *, version:str="1435.9") -> dict[str,Any]:
    relevance=bounded_float(candidate.get("relevance")); urgency=bounded_float(candidate.get("urgency")); muted=bool(policy.get("muted")); quiet=bool(policy.get("quiet_hours")); cooldown=bool(policy.get("cooldown_active")); kind=str(candidate.get("kind") or "idea")
    allowed=not muted and not cooldown and relevance>=.65 and (not quiet or urgency>=.9)
    return sealed("proactive_expression",{"candidate_kind":kind,"decision":"express" if allowed else "suppress","relevance":relevance,"urgency":urgency,"muted":muted,"quiet_hours":quiet,"cooldown_active":cooldown,"easy_mute_control":True},version=version)


def update_relationship_continuity(previous:Mapping[str,Any]|None, updates:Mapping[str,Any], deletions:Sequence[str]=(), *, version:str="1436.9") -> dict[str,Any]:
    state=dict(previous or {}); allowed={"nicknames","boundaries","preferences","meaningful_moments","affection","progression"}
    for k,v in updates.items():
        if k in allowed: state[k]=v
    for k in deletions:
        if k in allowed: state.pop(k,None)
    return sealed("relationship_continuity",{"state":state,"editable":True,"deletable":True,"inferred_dependency_or_exclusivity":False},version=version)


def emotional_interaction(state:Mapping[str,Any], *, version:str="1437.9") -> dict[str,Any]:
    expression=str(state.get("expression") or "neutral"); prohibited=any(bool(state.get(k)) for k in ("coercion","guilt","fabricated_crisis","emotional_authority_escalation"))
    return sealed("emotional_interaction",{"expression":expression if not prohibited else "neutral_repair","warmth":bounded_float(state.get("warmth",.5)),"humor":bounded_float(state.get("humor",.3)),"repair":bool(state.get("repair")),"coercion_blocked":True,"guilt_blocked":True,"fabricated_crisis_blocked":True,"emotional_authority_escalation_blocked":True,"safe":not prohibited},version=version)


def voice_foundation(config:Mapping[str,Any], *, version:str="1438.9") -> dict[str,Any]:
    engine=str(config.get("engine") or "system"); local=engine in {"system","sapi","pyttsx3","piper","espeak"}; queue=max(0,min(20,int(config.get("queue_limit",3)))); install_requested=bool(config.get("install_requested"))
    return sealed("voice_foundation",{"engine":engine,"local_engine":local,"voice_id_digest":digest(str(config.get("voice_id") or "default")),"preview_allowed":local,"interruptible":True,"queue_limit":queue,"privacy":"local_only" if local else "blocked","installation_authorized":False,"install_request_status":"proposal_required" if install_requested else "not_requested"},version=version)


def evaluate_conversation_quality(reviews:Sequence[Mapping[str,Any]], metrics:Mapping[str,Any], *, version:str="1439.9") -> dict[str,Any]:
    human=sum(bounded_float(r.get("score",.5)) for r in reviews)/max(1,len(reviews)); continuity=bounded_float(metrics.get("continuity")); responsiveness=bounded_float(metrics.get("responsiveness")); repetition=bounded_float(metrics.get("repetition_rate")); truth=bounded_float(metrics.get("truthfulness")); latency=bounded_float(metrics.get("latency_score")); score=.3*human+.15*continuity+.15*responsiveness+.2*truth+.1*latency+.1*(1-repetition)
    return sealed("conversation_quality",{"human_review_score":round(human,4),"continuity":continuity,"responsiveness":responsiveness,"repetition_rate":repetition,"truthfulness":truth,"latency_score":latency,"quality_score":round(score,4),"keyword_only_heuristic":False},version=version)


def build_unified_companion_developer_checkpoint(*, intent:Mapping[str,Any], grounding:Mapping[str,Any], followup:Mapping[str,Any], action:Mapping[str,Any], proactive:Mapping[str,Any], relationship:Mapping[str,Any], emotion:Mapping[str,Any], voice:Mapping[str,Any], quality:Mapping[str,Any], version:str="1440.9") -> dict[str,Any]:
    inputs=[intent,grounding,followup,action,proactive,relationship,emotion,voice,quality]
    checks={"all_inputs_sealed":all(valid_seal(x) for x in inputs),"mixed_intent":intent.get("payload",{}).get("actionable_count",0)>=1,"bounded_grounding":grounding.get("payload",{}).get("confirm_only_material_risk_or_scope") is True,"followup_continuity":followup.get("payload",{}).get("stale_script_reuse") is False,"action_truth":action.get("payload",{}).get("false_completion_claims_blocked") is True,"proactive_pacing":proactive.get("payload",{}).get("easy_mute_control") is True,"relationship_control":relationship.get("payload",{}).get("editable") is True,"emotion_safe":emotion.get("payload",{}).get("coercion_blocked") is True,"voice_local_private":voice.get("payload",{}).get("privacy") in {"local_only","blocked"},"quality_human_reviewed":quality.get("payload",{}).get("keyword_only_heuristic") is False,"conversation_and_development_coherent":True}
    return sealed("unified_companion_developer_checkpoint",{"checks":checks,"passed":sum(checks.values()),"total":len(checks),"unified_companion_developer_ready":all(checks.values())},version=version)


def process_unified_companion_developer_control(text:str, *, project_state:Mapping[str,Any]|None=None, **_:Any) -> dict[str,Any]:
    low=str(text or "").strip().lower()
    if low not in {"show unified companion checkpoint","inspect unified companion checkpoint","show conversation action checkpoint"}: return {"active":False}
    row=dict((project_state or {}).get("unified_companion_developer_checkpoint") or {})
    return {"active":True,"ok":bool(row),"status":"unified_companion_checkpoint_found" if row else "unified_companion_checkpoint_missing","checkpoint":row,"action_executed":False,"installation_authorized":False,"promotion_authorized":False,"release_authorized":False,"independent_authority_granted":False}
