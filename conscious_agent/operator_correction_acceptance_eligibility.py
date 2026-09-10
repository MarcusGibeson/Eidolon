from __future__ import annotations
"""v1142.0 durable, content-free operator correction and acceptance eligibility."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib, os
from pathlib import Path
from typing import Any, Callable
from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock

CONTRACT_VERSION = "v1142.0"
SCHEMA_VERSION = "1"
DECISION_KINDS = {"correction", "acceptance", "rejection", "clarification", "qualification", "withdrawal"}
TARGET_KINDS = {"belief", "goal", "motivation", "self_model", "reasoning_policy", "project_assumption", "proposal", "decision"}
STATES = {"eligible", "awaiting_target", "awaiting_lineage", "requires_operator_review", "suppressed", "superseded", "retracted", "retired"}
AUTHORITY_KEYS = ("can_mutate_belief","can_mutate_goal","can_mutate_motivation","can_mutate_self_model","can_delete_history","can_rewrite_operator_decision","can_execute","can_approve","can_authorize","can_install","can_promote","can_certify")

def _now(): return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00","Z")
def _clean(v: Any, n=240): return " ".join(str(v or "").split())[:n]
def _digest(*parts: Any): return hashlib.sha256("\x1f".join(_clean(p,4000) for p in parts).encode()).hexdigest()
def _root(): return Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1]/"data").expanduser().resolve()/"cognition"
def _default(): return {"schema_version":SCHEMA_VERSION,"contract_version":CONTRACT_VERSION,"records":[],"processed_events":[],"revision":0,"updated_at":"","authority_boundary":{k:False for k in AUTHORITY_KEYS}}

class OperatorCorrectionAcceptanceEligibilityStore:
    def __init__(self,runtime_root=None,*,clock:Callable[[],str]|None=None):
        self.runtime_root=Path(runtime_root).resolve() if runtime_root else _root(); self.path=self.runtime_root/"operator_correction_acceptance_eligibility.json"; self.clock=clock or _now
    def _load(self):
        s=load_json_file(self.path,_default(),expected_type=dict)
        for k,v in _default().items(): s.setdefault(k,deepcopy(v))
        return s
    def snapshot(self): return deepcopy(self._load())
    def register(self,event_id:str,*,operator_decision_id:str,decision_kind:str,target_kind:str,target_id:str,source_record_id:str,source_revision_id:str,project_digest:str="",scope_digest:str="",confidence:float=1.0,uncertainty:float=0.0,explicit_operator_decision:bool=True,contradiction_ids:list[str]|None=None,retraction_ids:list[str]|None=None,supersession_ids:list[str]|None=None,retirement_ids:list[str]|None=None):
        event_id=_clean(event_id,180); operator_decision_id=_clean(operator_decision_id); decision_kind=_clean(decision_kind,80); target_kind=_clean(target_kind,80); target_id=_clean(target_id); source_record_id=_clean(source_record_id); source_revision_id=_clean(source_revision_id)
        if not event_id or not operator_decision_id: raise ValueError("event and operator decision identifiers required")
        if decision_kind not in DECISION_KINDS or target_kind not in TARGET_KINDS: raise ValueError("recognized decision and target kinds required")
        contradictions=sorted({_clean(x) for x in contradiction_ids or [] if _clean(x)}); retractions=sorted({_clean(x) for x in retraction_ids or [] if _clean(x)}); supersessions=sorted({_clean(x) for x in supersession_ids or [] if _clean(x)}); retirements=sorted({_clean(x) for x in retirement_ids or [] if _clean(x)})
        lineage_complete=bool(target_id and source_record_id and source_revision_id)
        state="eligible"; reason="exact_operator_decision_and_target_lineage"
        if retirements: state,reason="retired","retirement_lineage"
        elif retractions or decision_kind=="withdrawal": state,reason="retracted","operator_withdrawal_or_retraction"
        elif supersessions: state,reason="superseded","supersession_lineage"
        elif contradictions or not explicit_operator_decision: state,reason="suppressed","contradiction_or_nonexplicit_decision"
        elif not target_id: state,reason="awaiting_target","exact_target_required"
        elif not lineage_complete: state,reason="awaiting_lineage","exact_historical_lineage_required"
        structural=_digest(operator_decision_id,decision_kind,target_kind,target_id,source_record_id,source_revision_id,project_digest,scope_digest,*contradictions,*retractions,*supersessions,*retirements)
        with metadata_mutation_lock(self.path,timeout_seconds=5):
            s=self._load(); prior=next((x for x in s["processed_events"] if x.get("event_id")==event_id),None)
            if prior:return {"ok":True,**deepcopy(prior["result"]),"idempotent":True}
            duplicate=next((x for x in s["records"] if x.get("structural_digest")==structural and x.get("state") in {"eligible","awaiting_target","awaiting_lineage","requires_operator_review"}),None)
            if duplicate: result={"status":"duplicate_suppressed","eligibility_id":duplicate["eligibility_id"],"state":"suppressed"}
            else:
                now=self.clock(); eid=f"operator-correction-eligibility-{structural[:24]}"; row={"eligibility_id":eid,"operator_decision_id":operator_decision_id,"decision_kind":decision_kind,"target_kind":target_kind,"target_id":target_id,"source_record_id":source_record_id,"source_revision_id":source_revision_id,"project_digest":_clean(project_digest,128),"scope_digest":_clean(scope_digest,128),"confidence":max(0,min(float(confidence),1)),"uncertainty":max(0,min(float(uncertainty),1)),"explicit_operator_decision":bool(explicit_operator_decision),"historical_record_preserved":True,"original_state_mutated":False,"future_reasoning_mutated":False,"contradiction_ids":contradictions,"retraction_ids":retractions,"supersession_ids":supersessions,"retirement_ids":retirements,"state":state,"state_reason":reason,"structural_digest":structural,"created_at":now,"history":[{"change":"recorded","state":state,"occurred_at":now,"content_free":True}]}; s["records"].append(row); result={"status":"eligibility_recorded","eligibility_id":eid,"state":state}
            now=self.clock(); s["processed_events"].append({"event_id":event_id,"event_digest":_digest(event_id),"occurred_at":now,"result":deepcopy(result),"content_free":True}); s["revision"]+=1;s["updated_at"]=now;write_json_atomic(self.path,s,expected_type=dict,sort_keys=True);return {"ok":True,**result,"idempotent":False}
    def inspection_summary(self):
        s=self._load(); counts={}
        for r in s["records"]: counts[r.get("state")]=counts.get(r.get("state"),0)+1
        keys=("eligibility_id","operator_decision_id","decision_kind","target_kind","target_id","source_record_id","source_revision_id","project_digest","scope_digest","confidence","uncertainty","explicit_operator_decision","historical_record_preserved","original_state_mutated","future_reasoning_mutated","state","state_reason","structural_digest","contradiction_ids","retraction_ids","supersession_ids","retirement_ids")
        return {"ok":True,"contract_version":CONTRACT_VERSION,"record_count":len(s["records"]),"state_counts":counts,"recent_records":[{k:r.get(k) for k in keys} for r in s["records"][-32:]],"authority_boundary":deepcopy(s["authority_boundary"]),"raw_content_exposed":False,"operator_text_exposed":False,"reasoning_text_exposed":False,"historical_record_preserved":True,"state_mutated":False}

def build_operator_correction_acceptance_eligibility_inspection(runtime_root=None): return OperatorCorrectionAcceptanceEligibilityStore(runtime_root).inspection_summary()
