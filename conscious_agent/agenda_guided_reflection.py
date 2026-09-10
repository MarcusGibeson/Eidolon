from __future__ import annotations

"""Provider-neutral one-step reflection intake from selected agenda attention."""

from copy import deepcopy
from datetime import datetime, timezone
import hashlib, os
from pathlib import Path
from typing import Any, Callable, Mapping

from autonomous_attention_agenda import AutonomousAttentionAgenda
from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
from motivation_agenda_arbitration import MotivationAgendaArbitrator

CONTRACT_VERSION = "v1107.3"
OUTCOMES = {"continue_attention", "defer", "resolved", "deliberate_silence"}

def _now() -> str: return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
def _clean(v: Any, n: int = 500) -> str: return " ".join(str(v or "").split())[:n]
def _digest(*parts: Any) -> str: return hashlib.sha256("\x1f".join(_clean(p,3000) for p in parts).encode()).hexdigest()
def _root() -> Path: return Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1]/"data").expanduser().resolve()/"cognition"
def _default() -> dict[str,Any]:
    return {"schema_version":"1","contract_version":CONTRACT_VERSION,"intakes":[],"processed_events":[],"revision":0,"updated_at":"","controls":{"max_intakes":256,"reflection_step_limit":1},"authority_boundary":{"can_browse":False,"can_execute":False,"can_modify_files":False,"can_manage_models":False,"can_authorize":False,"can_approve":False,"can_promote":False,"can_certify":False}}

class AgendaGuidedReflection:
    def __init__(self,runtime_root: str|Path|None=None,*,clock:Callable[[],str]|None=None):
        self.runtime_root=Path(runtime_root).expanduser().resolve() if runtime_root else _root(); self.path=self.runtime_root/"agenda_guided_reflection.json"; self.clock=clock or _now
        self.agenda=AutonomousAttentionAgenda(self.runtime_root); self.arbitration=MotivationAgendaArbitrator(self.runtime_root,agenda=self.agenda)
    def _load(self):
        s=load_json_file(self.path,_default(),expected_type=dict)
        if s.get("schema_version")!="1": s=_default()
        for k,v in _default().items(): s.setdefault(k,deepcopy(v))
        return s
    def snapshot(self): return deepcopy(self._load())
    def intake(self,event_id:str,*,receipt_id:str,outcome:str="continue_attention",reflection_summary:str="",eligible_for_intention:bool=False,deferral_reason:str="") -> dict[str,Any]:
        event_id=_clean(event_id,180); receipt_id=_clean(receipt_id,180); outcome=_clean(outcome,80)
        if not event_id or not receipt_id: raise ValueError("event_id and receipt_id are required")
        if outcome not in OUTCOMES: raise ValueError("unsupported reflection outcome")
        with metadata_mutation_lock(self.path,timeout_seconds=5):
            s=self._load(); prior=next((x for x in s["processed_events"] if x.get("event_id")==event_id),None)
            if prior:return {"ok":True,"status":"duplicate_event_ignored","result":deepcopy(prior["result"]),"idempotent":True}
            receipt=next((x for x in self.arbitration.snapshot().get("arbitration_receipts",[]) if x.get("receipt_id")==receipt_id),None)
            if not receipt or not receipt.get("selected_agenda_id"): result={"status":"deliberate_no_intake","reason":"selection_receipt_missing_or_silent","intake_id":""}
            elif int((receipt.get("reflection_handoff") or {}).get("reflection_step_limit") or 0)!=1: result={"status":"blocked_unbounded_handoff","reason":"reflection_step_limit_not_one","intake_id":""}
            else:
                agenda_id=str(receipt["selected_agenda_id"]); item=next((x for x in self.agenda.snapshot().get("agenda_items",[]) if x.get("agenda_id")==agenda_id and x.get("active_influence")),None)
                if not item: result={"status":"deliberate_no_intake","reason":"agenda_subject_inactive","intake_id":""}
                else:
                    key=_digest(receipt_id,agenda_id); existing=next((x for x in s["intakes"] if x.get("intake_key")==key),None)
                    if existing: result={"status":"duplicate_intake_ignored","intake_id":existing["intake_id"],"outcome":existing["outcome"]}
                    else:
                        summary=_clean(reflection_summary,1200); now=self.clock(); iid=f"agenda-reflection-{key[:24]}"
                        row={"intake_id":iid,"intake_key":key,"selection_receipt_id":receipt_id,"agenda_id":agenda_id,"subject_digest":item.get("subject_digest"),"origin_type":(item.get("origin") or {}).get("type"),"occurred_at":now,"reflection_step_count":1,"outcome":outcome,"summary_digest":_digest(summary) if summary else "","eligible_for_intention":bool(eligible_for_intention and outcome=="continue_attention"),"deferral_reason_code":_clean(deferral_reason,100),"provider_contacted":False,"hidden_reasoning_stored":False,"private_subject_exposed":False,"action_authority_granted":False,"generation_loop_created":False}
                        s["intakes"]=(s["intakes"]+[row])[-int(s["controls"]["max_intakes"]):]; result={"status":"reflection_intake_recorded","intake_id":iid,"outcome":outcome,"eligible_for_intention":row["eligible_for_intention"]}
            now=self.clock(); s["processed_events"]=(s["processed_events"]+[{"event_id":event_id,"event_digest":_digest(event_id),"occurred_at":now,"result":deepcopy(result),"content_free":True}])[-1024:]; s["revision"]+=1;s["updated_at"]=now;write_json_atomic(self.path,s,expected_type=dict,sort_keys=True)
            return {"ok":True,"status":result["status"],"result":result,"idempotent":False}
    def inspection_summary(self):
        s=self._load(); rows=s["intakes"]
        return {"ok":True,"contract_version":CONTRACT_VERSION,"revision":s["revision"],"intake_count":len(rows),"eligible_for_intention_count":sum(bool(x.get("eligible_for_intention")) for x in rows),"deliberate_silence_count":sum(x.get("outcome")=="deliberate_silence" for x in rows),"outcome_counts":{k:sum(x.get("outcome")==k for x in rows) for k in sorted(OUTCOMES)},"recent_intakes":[{k:x.get(k) for k in ("intake_id","selection_receipt_id","agenda_id","subject_digest","origin_type","occurred_at","reflection_step_count","outcome","eligible_for_intention")} for x in rows[-24:]],"controls":deepcopy(s["controls"]),"authority_boundary":deepcopy(s["authority_boundary"]),"provider_contacted":False,"external_browsing_performed":False,"hidden_reasoning_exposed":False,"private_subjects_exposed":False,"action_authority_changed":False,"runtime_mutated":False}

def build_agenda_guided_reflection_inspection(runtime_root=None): return AgendaGuidedReflection(runtime_root).inspection_summary()
