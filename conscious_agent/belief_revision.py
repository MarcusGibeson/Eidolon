from __future__ import annotations

"""Provider-neutral beliefs, conflict sets, uncertainty, and commitment review.

This module stores concise propositions and evidence references, not hidden reasoning.
Belief or commitment changes remain internal state and never authorize actions.
"""

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping
import uuid

try:
    from json_storage import load_json_file, write_json_atomic
    from metadata_mutation_coordination import metadata_mutation_lock
    from persistent_motivation import MotivationStore
except ImportError:
    from json_storage import load_json_file, write_json_atomic
    from metadata_mutation_coordination import metadata_mutation_lock
    from persistent_motivation import MotivationStore

BELIEF_SCHEMA_VERSION = "1"
BELIEF_CONTRACT_VERSION = "v1152.8"
EVIDENCE_STANCES = {"supports", "contradicts", "contextualizes"}
BELIEF_STATES = {"active", "contested", "retracted", "superseded"}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _clean(value: Any, limit: int = 600) -> str:
    return " ".join(str(value or "").split())[: max(0, int(limit))]


def _bounded(value: Any, minimum: float = 0.0, maximum: float = 1.0) -> float:
    try: number=float(value)
    except (TypeError,ValueError): number=minimum
    return round(max(minimum,min(maximum,number)),4)


def _digest(*parts: Any) -> str:
    material="\x1f".join(_clean(part,2000) for part in parts)
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def _default_runtime_root() -> Path:
    root=Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1]/"data").expanduser().resolve()
    return root/"cognition"


def _default_state() -> dict[str,Any]:
    return {
        "schema_version":BELIEF_SCHEMA_VERSION,
        "contract_version":BELIEF_CONTRACT_VERSION,
        "beliefs":[],
        "conflict_sets":[],
        "commitment_reviews":[],
        "processed_events":[],
        "revision":0,
        "updated_at":"",
        "authority_boundary":{
            "belief_can_authorize_action":False,
            "belief_can_execute_action":False,
            "commitment_review_can_approve":False,
            "operator_authority_unchanged":True,
        },
    }


class BeliefRevisionStore:
    def __init__(self,runtime_root:str|Path|None=None,*,motivation_store:MotivationStore|None=None,clock:Callable[[],str]|None=None,history_limit:int=512)->None:
        self.runtime_root=Path(runtime_root).expanduser().resolve() if runtime_root else _default_runtime_root()
        self.path=self.runtime_root/"belief_revision.json"
        self.motivations=motivation_store or MotivationStore(self.runtime_root)
        self.clock=clock or _utc_now
        self.history_limit=max(64,int(history_limit))

    def _load(self)->dict[str,Any]:
        state=load_json_file(self.path,_default_state(),expected_type=dict)
        if state.get("schema_version")!=BELIEF_SCHEMA_VERSION: return _default_state()
        for key,default in _default_state().items(): state.setdefault(key,deepcopy(default))
        return state

    def snapshot(self)->dict[str,Any]: return deepcopy(self._load())

    def _mutate(self,event_id:str,mutator:Callable[[dict[str,Any],str],dict[str,Any]])->dict[str,Any]:
        event_id=_clean(event_id,160)
        if not event_id: raise ValueError("event_id is required")
        with metadata_mutation_lock(self.path,timeout_seconds=5.0):
            state=self._load(); prior=next((r for r in state["processed_events"] if r.get("event_id")==event_id),None)
            if prior: return {"ok":True,"status":"duplicate_event_ignored","result":deepcopy(prior.get("result") or {}),"idempotent":True}
            now=self.clock(); result=mutator(state,now); state["revision"]=int(state.get("revision") or 0)+1; state["updated_at"]=now
            state["processed_events"]=(state["processed_events"]+[{"event_id":event_id,"event_digest":_digest(event_id),"occurred_at":now,"result":deepcopy(result),"content_free":True}])[-self.history_limit:]
            write_json_atomic(self.path,state,expected_type=dict,sort_keys=True)
            return {"ok":True,"status":str(result.get("status") or "updated"),"result":deepcopy(result),"idempotent":False}

    @staticmethod
    def _recompute(belief:dict[str,Any])->None:
        support=0.0; contradict=0.0; active_support=False; active_contradict=False
        for row in belief.get("evidence") or []:
            if not row.get("active"): continue
            impact=float(row.get("weight") or 0.0)*float(row.get("reliability") or 0.0)
            if row.get("stance")=="supports": support+=impact; active_support=True
            elif row.get("stance")=="contradicts": contradict+=impact; active_contradict=True
        prior=float(belief.get("prior_confidence") or .5)
        belief["confidence"]=_bounded(prior+(support-contradict)*.35)
        belief["uncertainty"]=_bounded(1.0-abs(belief["confidence"]-.5)*2.0)
        if belief.get("lifecycle_state") in {"retracted","superseded"}: return
        belief["lifecycle_state"]="contested" if active_support and active_contradict else "active"


    def integrate_candidate(self,event_id:str,*,candidate:Mapping[str,Any])->dict[str,Any]:
        """Atomically merge one ordinary-conversation belief candidate into the durable ledger.

        The candidate can revise internal belief state, but never grants approval or action
        authority. Historical beliefs and evidence remain preserved.
        """
        if not isinstance(candidate,Mapping): raise TypeError("candidate must be a mapping")
        candidate_id=_clean(candidate.get("belief_candidate_id"),120)
        proposition=_clean(candidate.get("proposition") or candidate.get("content"),600)
        subject_key=_clean(candidate.get("semantic_subject_key"),128)
        origin_ref=_clean(candidate.get("origin_reflection_id") or candidate_id,240)
        evidence_refs=[_clean(v,300) for v in (candidate.get("evidence_refs") or []) if _clean(v,300)][:4]
        confidence=_bounded(candidate.get("confidence",.5))
        retires={_clean(v,120) for v in (candidate.get("retires_belief_candidate_ids") or []) if _clean(v,120)}
        explicit_correction=str(candidate.get("revision_basis") or "")=="explicit_user_correction" or bool(retires)
        if not all((candidate_id,proposition,subject_key,origin_ref)): raise ValueError("candidate identity, proposition, subject, and origin are required")
        def apply(state:dict[str,Any],now:str)->dict[str,Any]:
            prior_by_candidate=next((r for r in state["beliefs"] if r.get("source_candidate_id")==candidate_id),None)
            if prior_by_candidate:
                return {"status":"candidate_already_integrated","belief_id":prior_by_candidate["belief_id"],"created":False,"projection":self._projection(prior_by_candidate,state)}
            matching=[r for r in state["beliefs"] if r.get("candidate_subject_key")==subject_key and r.get("lifecycle_state") in {"active","contested"}]
            normalized=" ".join(proposition.casefold().split())
            same=next((r for r in reversed(matching) if " ".join(str(r.get("proposition") or "").casefold().split())==normalized),None)
            if same and not explicit_correction:
                applied=[]
                for ref in evidence_refs:
                    semantic=_digest(same["belief_id"],"supports",ref)
                    if any(e.get("semantic_key")==semantic for e in same.get("evidence") or []): continue
                    evidence_id=f"evidence-{_digest(candidate_id,ref)[:28]}"
                    same.setdefault("evidence",[]).append({"evidence_id":evidence_id,"semantic_key":semantic,"stance":"supports","weight":.5,"reliability":confidence,"source_type":"ordinary_conversation_candidate","reference_digest":_digest(ref),"active":True,"created_at":now,"retracted_at":""})
                    applied.append(evidence_id)
                before=same.get("confidence"); self._recompute(same); same["updated_at"]=now
                same.setdefault("source_candidate_ids",[]).append(candidate_id); same["source_candidate_ids"]=same["source_candidate_ids"][-64:]
                same["update_history"]=(same.get("update_history",[])+[{"event":"candidate_evidence_merged","occurred_at":now,"candidate_id_digest":_digest(candidate_id),"prior_confidence":before,"new_confidence":same["confidence"],"evidence_count":len(applied),"authored_conclusion":"New ordinary-turn evidence updated confidence without granting action authority."}])[-64:]
                return {"status":"candidate_evidence_merged","belief_id":same["belief_id"],"created":False,"projection":self._projection(same,state)}
            belief_id=f"belief-{_digest(candidate_id,subject_key)[:28]}"
            base={"belief_id":belief_id,"semantic_key":_digest(proposition.casefold(),""),"candidate_subject_key":subject_key,"source_candidate_id":candidate_id,"source_candidate_ids":[candidate_id],"proposition":proposition,"prior_confidence":confidence,"confidence":confidence,"uncertainty":_bounded(1.0-abs(confidence-.5)*2.0),"lifecycle_state":"active","scope_project_id":"","origin":{"type":"ordinary_conversation_belief_candidate","reference_digest":_digest(origin_ref),"occurred_at":now},"evidence":[],"created_at":now,"updated_at":now,"update_history":[{"event":"candidate_integrated","occurred_at":now,"conclusion":"Provisional belief integrated with explicit uncertainty and no action authority."}],"authority":{"authorizes_action":False,"executes_action":False}}
            for ref in evidence_refs:
                base["evidence"].append({"evidence_id":f"evidence-{_digest(candidate_id,ref)[:28]}","semantic_key":_digest(belief_id,"supports",ref),"stance":"supports","weight":.5,"reliability":confidence,"source_type":"ordinary_conversation_candidate","reference_digest":_digest(ref),"active":True,"created_at":now,"retracted_at":""})
            self._recompute(base)
            superseded=[]
            if explicit_correction:
                for old in matching:
                    old_candidate=str(old.get("source_candidate_id") or "")
                    if retires and old_candidate not in retires: continue
                    old["lifecycle_state"]="superseded"; old["updated_at"]=now
                    old["update_history"]=(old.get("update_history",[])+[{"event":"ordinary_correction_supersession","occurred_at":now,"preferred_belief_id":belief_id,"authored_conclusion":"Explicit user correction preserved this belief historically but removed it from active selection."}])[-64:]
                    superseded.append(old["belief_id"])
            elif matching:
                base["lifecycle_state"]="contested"
                for old in matching: old["lifecycle_state"]="contested"; old["updated_at"]=now
            state["beliefs"].append(base)
            conflict_id=""
            if matching and not explicit_correction:
                ids=sorted({belief_id,*[str(r.get("belief_id")) for r in matching if r.get("belief_id")]})
                semantic=_digest(*ids)
                prior_conflict=next((r for r in state["conflict_sets"] if r.get("semantic_key")==semantic and r.get("status")=="active"),None)
                if prior_conflict: conflict_id=prior_conflict["conflict_id"]
                else:
                    conflict_id=f"conflict-{_digest(event_id,*ids)[:28]}"
                    state["conflict_sets"].append({"conflict_id":conflict_id,"semantic_key":semantic,"belief_ids":ids,"motivation_ids":[],"reason_code":"ordinary_candidate_competing_proposition","status":"active","created_at":now,"resolved_at":"","preferred_belief_id":"","history":[]})
            return {"status":"candidate_integrated","belief_id":belief_id,"created":True,"superseded_belief_ids":superseded,"conflict_id":conflict_id,"projection":self._projection(base,state)}
        return self._mutate(event_id,apply)

    @staticmethod
    def _projection(belief:Mapping[str,Any],state:Mapping[str,Any])->dict[str,Any]:
        belief_id=str(belief.get("belief_id") or "")
        active_conflicts=[r for r in (state.get("conflict_sets") or []) if r.get("status")=="active" and belief_id in (r.get("belief_ids") or [])]
        return {"type":"belief_revision","belief_id":belief_id,"content":_clean(belief.get("proposition"),420),"proposition":_clean(belief.get("proposition"),420),"confidence":_bounded(belief.get("confidence",.5)),"uncertainty_score":_bounded(belief.get("uncertainty",1.0)),"lifecycle_state":str(belief.get("lifecycle_state") or "active"),"conflict_count":len(active_conflicts),"use_in_conversation":str(belief.get("lifecycle_state") or "") == "active" and not active_conflicts,"epistemic_status":"revisable","recommended_action":"store_only","operator_authority_required_for_action":True,"authority_broadened":False,"action_executed":False,"source_content_exposed":False,"contract_version":BELIEF_CONTRACT_VERSION}

    def record_belief(self,event_id:str,*,proposition:str,confidence:float=.5,origin_type:str,origin_ref:str,scope_project_id:str="",belief_id:str="")->dict[str,Any]:
        proposition=_clean(proposition,600); origin_type=_clean(origin_type,80); origin_ref=_clean(origin_ref,240)
        if not proposition or not origin_type or not origin_ref: raise ValueError("proposition, origin_type, and origin_ref are required")
        semantic_key=_digest(proposition.casefold(),scope_project_id)
        def apply(state:dict[str,Any],now:str)->dict[str,Any]:
            existing=next((r for r in state["beliefs"] if r.get("semantic_key")==semantic_key and r.get("lifecycle_state") in {"active","contested"}),None)
            if existing: return {"status":"duplicate_belief_ignored","belief_id":existing["belief_id"],"created":False}
            item_id=_clean(belief_id,120) or f"belief-{uuid.uuid4().hex}"
            if any(r.get("belief_id")==item_id for r in state["beliefs"]): raise ValueError("belief_id already exists")
            base=_bounded(confidence)
            state["beliefs"].append({
                "belief_id":item_id,"semantic_key":semantic_key,"proposition":proposition,"prior_confidence":base,"confidence":base,
                "uncertainty":_bounded(1.0-abs(base-.5)*2.0),"lifecycle_state":"active","scope_project_id":_clean(scope_project_id,120),
                "origin":{"type":origin_type,"reference_digest":_digest(origin_ref),"occurred_at":now},"evidence":[],"created_at":now,"updated_at":now,
                "update_history":[{"event":"created","occurred_at":now,"conclusion":"Belief recorded with explicit uncertainty and no action authority."}],
                "authority":{"authorizes_action":False,"executes_action":False},
            })
            return {"status":"belief_created","belief_id":item_id,"created":True,"confidence":base}
        return self._mutate(event_id,apply)

    def add_evidence(self,event_id:str,*,belief_id:str,stance:str,weight:float,reliability:float,evidence_ref:str,source_type:str="observation",evidence_id:str="")->dict[str,Any]:
        belief_id=_clean(belief_id,120); stance=_clean(stance,40).lower(); evidence_ref=_clean(evidence_ref,300)
        if stance not in EVIDENCE_STANCES: raise ValueError("unsupported evidence stance")
        if not belief_id or not evidence_ref: raise ValueError("belief_id and evidence_ref are required")
        semantic_key=_digest(belief_id,stance,evidence_ref)
        def apply(state:dict[str,Any],now:str)->dict[str,Any]:
            belief=next((r for r in state["beliefs"] if r.get("belief_id")==belief_id),None)
            if not belief: raise KeyError("belief not found")
            duplicate=next((r for r in belief["evidence"] if r.get("semantic_key")==semantic_key),None)
            if duplicate: return {"status":"duplicate_evidence_ignored","belief_id":belief_id,"evidence_id":duplicate["evidence_id"]}
            before=belief.get("confidence")
            item_id=_clean(evidence_id,120) or f"evidence-{uuid.uuid4().hex}"
            belief["evidence"].append({"evidence_id":item_id,"semantic_key":semantic_key,"stance":stance,"weight":_bounded(weight),"reliability":_bounded(reliability),"source_type":_clean(source_type,80),"reference_digest":_digest(evidence_ref),"active":True,"created_at":now,"retracted_at":""})
            self._recompute(belief); belief["updated_at"]=now
            belief["update_history"]=(belief["update_history"]+[{"event":"evidence_update","occurred_at":now,"prior_confidence":before,"new_confidence":belief["confidence"],"uncertainty":belief["uncertainty"],"evidence_id":item_id,"stance":stance,"authored_conclusion":"Confidence changed according to bounded evidence weight; uncertainty remains explicit."}])[-64:]
            return {"status":"belief_evidence_applied","belief_id":belief_id,"evidence_id":item_id,"confidence":belief["confidence"],"uncertainty":belief["uncertainty"],"lifecycle_state":belief["lifecycle_state"]}
        return self._mutate(event_id,apply)

    def retract_evidence(self,event_id:str,*,belief_id:str,evidence_id:str,correction_ref:str)->dict[str,Any]:
        belief_id=_clean(belief_id,120); evidence_id=_clean(evidence_id,120); correction_ref=_clean(correction_ref,300)
        if not all((belief_id,evidence_id,correction_ref)): raise ValueError("belief_id, evidence_id, and correction_ref are required")
        def apply(state:dict[str,Any],now:str)->dict[str,Any]:
            belief=next((r for r in state["beliefs"] if r.get("belief_id")==belief_id),None)
            if not belief: raise KeyError("belief not found")
            evidence=next((r for r in belief["evidence"] if r.get("evidence_id")==evidence_id),None)
            if not evidence: raise KeyError("evidence not found")
            if not evidence.get("active"):
                return {"status":"evidence_already_retracted","belief_id":belief_id,"evidence_id":evidence_id,"active_influence":False,"confidence":belief.get("confidence"),"idempotent_retraction":True}
            before=belief.get("confidence")
            evidence["active"]=False; evidence["retracted_at"]=now; evidence["correction_ref_digest"]=_digest(correction_ref)
            self._recompute(belief); belief["updated_at"]=now
            belief["update_history"]=(belief["update_history"]+[{"event":"evidence_retracted","occurred_at":now,"evidence_id":evidence_id,"prior_confidence":before,"new_confidence":belief.get("confidence"),"authored_conclusion":"Corrected evidence remains in history but no longer influences active confidence."}])[-64:]
            affected=[]
            for conflict in state.get("conflict_sets") or []:
                if conflict.get("status")!="active" or belief_id not in (conflict.get("belief_ids") or []): continue
                if belief.get("lifecycle_state") not in {"retracted", "superseded"}:
                    belief["lifecycle_state"]="contested"
                viable=[row for row in state.get("beliefs") or [] if row.get("belief_id") in (conflict.get("belief_ids") or []) and row.get("lifecycle_state") in {"active","contested"}]
                conflict["needs_review"]=True
                conflict["history"]=(conflict.get("history",[])+[{"event":"evidence_retraction_review_required","occurred_at":now,"belief_id":belief_id,"viable_belief_count":len(viable),"authorizes_resolution":False}])[-32:]
                affected.append(conflict.get("conflict_id"))
            return {"status":"evidence_retracted","belief_id":belief_id,"evidence_id":evidence_id,"active_influence":False,"confidence":belief["confidence"],"lifecycle_state":belief.get("lifecycle_state"),"affected_conflict_ids":affected,"automatic_resolution":False}
        return self._mutate(event_id,apply)

    def create_conflict_set(self,event_id:str,*,belief_ids:Iterable[str],reason_code:str,motivation_ids:Iterable[str]=())->dict[str,Any]:
        ids=sorted({_clean(v,120) for v in belief_ids if _clean(v,120)})
        if len(ids)<2: raise ValueError("at least two beliefs are required")
        semantic_key=_digest(*ids)
        def apply(state:dict[str,Any],now:str)->dict[str,Any]:
            known={r.get("belief_id") for r in state["beliefs"]}
            if not set(ids).issubset(known): raise KeyError("one or more beliefs were not found")
            prior=next((r for r in state["conflict_sets"] if r.get("semantic_key")==semantic_key and r.get("status")=="active"),None)
            if prior: return {"status":"duplicate_conflict_ignored","conflict_id":prior["conflict_id"],"created":False}
            conflict_id=f"conflict-{_digest(event_id,*ids)[:28]}"
            state["conflict_sets"].append({"conflict_id":conflict_id,"semantic_key":semantic_key,"belief_ids":ids,"motivation_ids":sorted({_clean(v,120) for v in motivation_ids if _clean(v,120)}),"reason_code":_clean(reason_code,120),"status":"active","created_at":now,"resolved_at":"","preferred_belief_id":"","history":[]})
            return {"status":"conflict_created","conflict_id":conflict_id,"created":True}
        return self._mutate(event_id,apply)

    def evaluate_conflict(self,event_id:str,*,conflict_id:str)->dict[str,Any]:
        conflict_id=_clean(conflict_id,120)
        def apply(state:dict[str,Any],now:str)->dict[str,Any]:
            conflict=next((r for r in state["conflict_sets"] if r.get("conflict_id")==conflict_id),None)
            if not conflict: raise KeyError("conflict not found")
            beliefs=[r for r in state["beliefs"] if r.get("belief_id") in conflict["belief_ids"]]
            ranked=sorted(beliefs,key=lambda r:(-float(r.get("confidence") or 0.0),float(r.get("uncertainty") or 1.0),str(r.get("belief_id") or "")))
            margin=(float(ranked[0].get("confidence") or 0.0)-float(ranked[1].get("confidence") or 0.0)) if len(ranked)>1 else 0.0
            recommendation="retain_conflict_and_seek_evidence" if margin<.35 else "candidate_resolution_available"
            review={"review_id":f"conflict-review-{_digest(event_id,conflict_id)[:24]}","conflict_id":conflict_id,"recommendation":recommendation,"leading_belief_id":ranked[0].get("belief_id") if ranked else "","confidence_margin":round(margin,4),"occurred_at":now,"authorizes_action":False}
            conflict["history"]=(conflict["history"]+[review])[-32:]
            return {"status":"conflict_evaluated",**review}
        return self._mutate(event_id,apply)

    def resolve_conflict(self,event_id:str,*,conflict_id:str,preferred_belief_id:str,evidence_ref:str)->dict[str,Any]:
        conflict_id=_clean(conflict_id,120); preferred_belief_id=_clean(preferred_belief_id,120); evidence_ref=_clean(evidence_ref,300)
        if not all((conflict_id,preferred_belief_id,evidence_ref)): raise ValueError("conflict, preferred belief, and evidence are required")
        def apply(state:dict[str,Any],now:str)->dict[str,Any]:
            conflict=next((r for r in state["conflict_sets"] if r.get("conflict_id")==conflict_id),None)
            if not conflict: raise KeyError("conflict not found")
            if preferred_belief_id not in conflict["belief_ids"]: raise ValueError("preferred belief is not in conflict")
            for belief in state["beliefs"]:
                if belief.get("belief_id") in conflict["belief_ids"] and belief.get("belief_id")!=preferred_belief_id:
                    belief["lifecycle_state"]="superseded"; belief["updated_at"]=now
                    belief["update_history"]=(belief["update_history"]+[{"event":"conflict_resolution","occurred_at":now,"preferred_belief_id":preferred_belief_id,"evidence_ref_digest":_digest(evidence_ref),"authored_conclusion":"This belief remains historical but no longer influences active belief selection."}])[-64:]
            conflict.update({"status":"resolved","resolved_at":now,"preferred_belief_id":preferred_belief_id})
            return {"status":"conflict_resolved","conflict_id":conflict_id,"preferred_belief_id":preferred_belief_id,"action_authority_changed":False}
        return self._mutate(event_id,apply)

    def review_commitment(self,event_id:str,*,motivation_id:str,belief_ids:Iterable[str])->dict[str,Any]:
        motivation_id=_clean(motivation_id,120); ids=sorted({_clean(v,120) for v in belief_ids if _clean(v,120)})
        def apply(state:dict[str,Any],now:str)->dict[str,Any]:
            motivation=next((r for r in self.motivations.snapshot().get("motivations") or [] if r.get("motivation_id")==motivation_id),None)
            if not motivation: raise KeyError("motivation not found")
            beliefs=[r for r in state["beliefs"] if r.get("belief_id") in ids]
            active_conflicts=[r for r in state["conflict_sets"] if r.get("status")=="active" and set(r.get("belief_ids") or []) & set(ids)]
            average_uncertainty=sum(float(r.get("uncertainty") or 0.0) for r in beliefs)/len(beliefs) if beliefs else 1.0
            recommendation="reconsider" if active_conflicts or average_uncertainty>.55 else "retain"
            review={"review_id":f"commitment-review-{_digest(event_id,motivation_id)[:24]}","motivation_id":motivation_id,"belief_ids":ids,"recommendation":recommendation,"average_uncertainty":round(average_uncertainty,4),"active_conflict_count":len(active_conflicts),"occurred_at":now,"applied":False,"authorizes_action":False}
            state["commitment_reviews"]=(state["commitment_reviews"]+[review])[-self.history_limit:]
            return {"status":"commitment_reviewed",**review}
        return self._mutate(event_id,apply)

    def reconsider_commitment(self,event_id:str,*,motivation_id:str,decision:str,supporting_refs:Iterable[str])->dict[str,Any]:
        decision=_clean(decision,40).lower(); motivation_id=_clean(motivation_id,120)
        if decision not in {"retain","suspend","release"}: raise ValueError("unsupported commitment decision")
        snapshot=self.motivations.snapshot(); motivation=next((r for r in snapshot.get("motivations") or [] if r.get("motivation_id")==motivation_id),None)
        if not motivation: raise KeyError("motivation not found")
        lifecycle=None if decision=="retain" else ("suspended" if decision=="suspend" else "abandoned")
        result=self.motivations.update_motivation(f"belief-review:{event_id}",motivation_id,reason_code="belief_revision_commitment_reconsideration",event_type="commitment_reconsideration",lifecycle_state=lifecycle,authored_conclusion=f"The internal commitment was {decision}ed after explicit uncertainty and conflict review; no action was authorized.",supporting_refs=supporting_refs)
        return {"ok":True,"status":"commitment_reconsidered","result":{"motivation_id":motivation_id,"decision":decision,"lifecycle_state":result["result"]["lifecycle_state"],"action_authority_changed":False},"idempotent":bool(result.get("idempotent"))}

    def inspection_summary(self,*,item_limit:int=10)->dict[str,Any]:
        state=self._load(); active=[r for r in state["beliefs"] if r.get("lifecycle_state") in {"active","contested"}]; active.sort(key=lambda r:(-float(r.get("confidence") or 0),str(r.get("belief_id") or "")))
        conflicts=[r for r in state["conflict_sets"] if r.get("status")=="active"]
        return {"ok":True,"schema_version":BELIEF_SCHEMA_VERSION,"contract_version":BELIEF_CONTRACT_VERSION,"active_belief_count":len(active),"contested_belief_count":sum(1 for r in active if r.get("lifecycle_state")=="contested"),"active_conflict_count":len(conflicts),"beliefs":[{"belief_id":r.get("belief_id"),"proposition":r.get("proposition"),"confidence":r.get("confidence"),"uncertainty":r.get("uncertainty"),"lifecycle_state":r.get("lifecycle_state"),"evidence_count":sum(1 for e in r.get("evidence") or [] if e.get("active"))} for r in active[:max(1,int(item_limit))]],"conflicts":[{"conflict_id":r.get("conflict_id"),"belief_ids":list(r.get("belief_ids") or []),"reason_code":r.get("reason_code"),"status":r.get("status")} for r in conflicts[:8]],"recent_commitment_reviews":deepcopy(state["commitment_reviews"][-8:]),"authority_boundary":deepcopy(state["authority_boundary"]),"raw_chain_of_thought_stored":False,"provider_payloads_stored":False,"updated_at":state.get("updated_at","")}


def build_belief_revision_inspection(runtime_root:str|Path|None=None)->dict[str,Any]: return BeliefRevisionStore(runtime_root).inspection_summary()
