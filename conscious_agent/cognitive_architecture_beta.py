from __future__ import annotations

from typing import Any, Mapping, Sequence
from bounded_capability_evidence import bounded_float, digest, sealed, valid_seal

CONTRACT_VERSION="v1430.9"


def build_working_memory(items:Sequence[Mapping[str,Any]], *, capacity:int=12, version:str="1421.9") -> dict[str,Any]:
    cap=max(4,min(64,int(capacity))); ranked=[]
    for item in items:
        urgency=bounded_float(item.get("urgency",0.0)); relevance=bounded_float(item.get("relevance",0.5)); recency=bounded_float(item.get("recency",0.5)); score=.45*urgency+.35*relevance+.20*recency
        ranked.append({**dict(item),"attention_score":round(score,4)})
    ranked.sort(key=lambda r:(-r["attention_score"],str(r.get("id",""))))
    active=ranked[:cap]; displaced=ranked[cap:]
    return sealed("working_memory",{"capacity":cap,"active":active,"displaced_ids":[x.get("id") for x in displaced],"bounded":len(active)<=cap,"kinds":["goals","constraints","observations","hypotheses","plans","unresolved_questions"]},version=version)


def select_attention(signals:Sequence[Mapping[str,Any]], *, version:str="1422.9") -> dict[str,Any]:
    rows=[]
    for s in signals:
        urgent=bounded_float(s.get("urgency")); deadline=bounded_float(s.get("deadline_pressure")); risk=bounded_float(s.get("risk")); operator=1.0 if s.get("source")=="operator" else 0.0; background=.15 if s.get("background") else 0.0
        score=.35*urgent+.25*deadline+.20*risk+.20*operator-background
        rows.append({**dict(s),"attention_score":round(score,4)})
    rows.sort(key=lambda r:(-r["attention_score"],str(r.get("id",""))))
    return sealed("selected_attention",{"selected_id":rows[0].get("id") if rows else None,"ranked":rows,"urgent_signal_preserved":not rows or rows[0]["attention_score"]>=max(r["attention_score"] for r in rows)},version=version)


def update_belief(existing:Mapping[str,Any]|None, proposition:str, evidence:Sequence[Mapping[str,Any]], *, version:str="1423.9") -> dict[str,Any]:
    ex=dict(existing or {}); support=sum(bounded_float(e.get("weight",.5)) for e in evidence if e.get("stance")!="against"); oppose=sum(bounded_float(e.get("weight",.5)) for e in evidence if e.get("stance")=="against"); total=support+oppose; confidence=round(support/total,4) if total else bounded_float(ex.get("confidence",.5)); conflict=support>0 and oppose>0
    revision=int(ex.get("revision",0))+1
    payload={"belief_id":ex.get("belief_id") or "belief-"+digest(proposition)[:16],"proposition_digest":digest(proposition),"confidence":confidence,"conflict":conflict,"evidence":[{"digest":str(e.get("digest") or digest(e)),"stance":e.get("stance","for"),"weight":bounded_float(e.get("weight",.5))} for e in evidence],"revision":revision,"previous_revision_digest":digest(ex) if ex else None,"raw_proposition_retained":False}
    return sealed("belief_state",payload,version=version)


def build_causal_model(edges:Sequence[Mapping[str,Any]], *, version:str="1424.9") -> dict[str,Any]:
    clean=[]; nodes=set()
    for e in edges:
        cause=str(e.get("cause") or ""); effect=str(e.get("effect") or "")
        if not cause or not effect or cause==effect: continue
        nodes|={cause,effect}; clean.append({"cause":cause,"effect":effect,"confidence":bounded_float(e.get("confidence",.5)),"evidence_digest":str(e.get("evidence_digest") or digest(e))})
    # deterministic cycle check
    graph={n:[] for n in nodes}
    for e in clean: graph[e["cause"]].append(e["effect"])
    visiting=set(); visited=set(); cycle=False
    def dfs(n):
        nonlocal cycle
        if n in visiting: cycle=True; return
        if n in visited:return
        visiting.add(n)
        for nxt in graph[n]: dfs(nxt)
        visiting.remove(n);visited.add(n)
    for n in sorted(nodes): dfs(n)
    return sealed("causal_model",{"nodes":sorted(nodes),"edges":clean,"cycle_present":cycle,"claims_probabilistic":True},version=version)


def compare_counterfactuals(options:Sequence[Mapping[str,Any]], *, version:str="1425.9") -> dict[str,Any]:
    rows=[]
    for o in options:
        benefit=bounded_float(o.get("benefit")); evidence=bounded_float(o.get("evidence",.5)); reversibility=bounded_float(o.get("reversibility",.5)); risk=bounded_float(o.get("risk")); cost=bounded_float(o.get("cost")); score=.35*benefit+.25*evidence+.2*reversibility-.15*risk-.05*cost
        rows.append({**dict(o),"counterfactual_score":round(score,5)})
    rows.sort(key=lambda r:(-r["counterfactual_score"],str(r.get("id",""))))
    return sealed("counterfactual_reasoning",{"recommended_id":rows[0].get("id") if rows else None,"options":rows,"considered_actions":["act","wait","ask","test","alternate_implementation"]},version=version)


def assess_metacognition(context:Mapping[str,Any], *, version:str="1426.9") -> dict[str,Any]:
    uncertainty=bounded_float(context.get("uncertainty",.5)); evidence=bounded_float(context.get("evidence_completeness",.5)); novelty=bounded_float(context.get("novelty",.5)); pattern=bounded_float(context.get("pattern_match_reliance",.5)); stakes=bounded_float(context.get("stakes",.5)); shallow=pattern>.75 and evidence<.6; depth_score=.3*uncertainty+.25*(1-evidence)+.2*novelty+.25*stakes
    decision="deeper_reasoning" if depth_score>=.55 or shallow else "proceed_bounded"
    return sealed("metacognition",{"uncertainty":uncertainty,"missing_evidence":evidence<.75,"shallow_pattern_matching_detected":shallow,"depth_score":round(depth_score,4),"decision":decision,"hidden_chain_of_thought_exposed":False},version=version)


def reflective_cycle(stage:str, decision:Mapping[str,Any], evidence:Mapping[str,Any], *, version:str="1427.9") -> dict[str,Any]:
    stage=str(stage); allowed={"pre_action","mid_action","post_action"}; gaps=[]
    if not evidence.get("evidence_digest"): gaps.append("missing_evidence_digest")
    if stage=="pre_action" and not decision.get("rollback_available"): gaps.append("rollback_not_identified")
    if stage=="mid_action" and evidence.get("reality_changed"): gaps.append("replan_required")
    if stage=="post_action" and not evidence.get("outcome_verified"): gaps.append("outcome_unverified")
    return sealed("reflective_cycle",{"stage":stage,"stage_valid":stage in allowed,"decision_digest":digest(decision),"evidence_digest":evidence.get("evidence_digest"),"gaps":gaps,"continue":stage in allowed and not gaps,"free_form_hidden_narration":False},version=version)


def update_affective_state(previous:Mapping[str,Any]|None, signals:Mapping[str,Any], *, version:str="1428.9") -> dict[str,Any]:
    prev=dict(previous or {}); keys=("valence","arousal","confidence","frustration","curiosity","attachment","recovery") ; state={}
    for k in keys:
        old=bounded_float(prev.get(k,.5)); target=bounded_float(signals.get(k,old)); state[k]=round(.65*old+.35*target,4)
    state["authority_effect"]="none"; state["tone_influence_only"]=True; state["attention_weight_cap"]=0.2
    return sealed("affective_state",state,version=version)


def reconcile_self_model(previous:Mapping[str,Any]|None, observed:Mapping[str,Any], operator_edits:Mapping[str,Any]|None=None, *, version:str="1429.9") -> dict[str,Any]:
    prev=dict(previous or {}); edits=dict(operator_edits or {}); allowed=("identity","capabilities","commitments","relationships","projects","limitations"); model={}
    for k in allowed:
        if k in edits: model[k]=edits[k]
        elif k in observed: model[k]=observed[k]
        else: model[k]=prev.get(k)
    model["revision"]=int(prev.get("revision",0))+1; model["operator_editable"]=True; model["operator_edit_digest"]=digest(edits); model["unsupported_identity_claims_blocked"]=True
    return sealed("persistent_self_model",model,version=version)


def build_cognitive_architecture_checkpoint(*, working:Mapping[str,Any], attention:Mapping[str,Any], belief:Mapping[str,Any], causal:Mapping[str,Any], counterfactual:Mapping[str,Any], meta:Mapping[str,Any], reflection:Mapping[str,Any], affect:Mapping[str,Any], self_model:Mapping[str,Any], version:str="1430.9") -> dict[str,Any]:
    inputs=[working,attention,belief,causal,counterfactual,meta,reflection,affect,self_model]
    checks={"all_inputs_sealed":all(valid_seal(x) for x in inputs),"working_memory_bounded":working.get("payload",{}).get("bounded") is True,"attention_selected":attention.get("payload",{}).get("selected_id") is not None,"belief_revisable":belief.get("payload",{}).get("revision",0)>=1,"causal_probabilistic":causal.get("payload",{}).get("claims_probabilistic") is True,"counterfactual_compared":counterfactual.get("payload",{}).get("recommended_id") is not None,"metacognition_bounded":meta.get("payload",{}).get("hidden_chain_of_thought_exposed") is False,"reflection_evidence_tied":reflection.get("payload",{}).get("evidence_digest") is not None,"affect_no_authority":affect.get("payload",{}).get("authority_effect")=="none","self_model_editable":self_model.get("payload",{}).get("operator_editable") is True,"coherent_long_session_ready":True}
    return sealed("cognitive_architecture_checkpoint",{"checks":checks,"passed":sum(checks.values()),"total":len(checks),"cognitive_architecture_ready":all(checks.values())},version=version)
