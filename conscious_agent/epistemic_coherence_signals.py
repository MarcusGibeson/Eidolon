from __future__ import annotations
"""Content-free v1119.0 epistemic coherence signals across established structural records."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib, os
from pathlib import Path
from typing import Any, Callable
try:
    from json_storage import load_json_file, write_json_atomic
    from metadata_mutation_coordination import metadata_mutation_lock
except ImportError:
    from json_storage import load_json_file, write_json_atomic
    from metadata_mutation_coordination import metadata_mutation_lock
CONTRACT_VERSION="v1119.0"; SCHEMA_VERSION="1"
SIGNAL_TYPES={"structural_contradiction","semantic_duplication","stale_dependency","confidence_mismatch","uncertainty_mismatch","unsupported_claim","lineage_gap"}
RECORD_TYPES={"evidence","knowledge","belief","identity_claim","self_model_claim"}
STATES={"active","corrected","retracted","merged","superseded","stale","retired"}
def _now(): return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00","Z")
def _clean(v:Any,n=300): return " ".join(str(v or "").split())[:n]
def _digest(*p:Any): return hashlib.sha256("\x1f".join(_clean(x,2000) for x in p).encode()).hexdigest()
def _root(): return Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1]/"data").expanduser().resolve()/"cognition"
def _default(): return {"schema_version":SCHEMA_VERSION,"contract_version":CONTRACT_VERSION,"signals":[],"processed_events":[],"revision":0,"updated_at":"","authority_boundary":{"can_mutate_evidence":False,"can_mutate_knowledge":False,"can_mutate_belief":False,"can_mutate_self_model":False,"can_select_attention":False,"can_create_proposal":False,"can_approve":False,"can_authorize":False,"can_execute":False}}
class EpistemicCoherenceSignalStore:
    def __init__(self,runtime_root=None,*,clock:Callable[[],str]|None=None): self.runtime_root=Path(runtime_root).expanduser().resolve() if runtime_root else _root(); self.path=self.runtime_root/"epistemic_coherence_signals.json"; self.clock=clock or _now
    def _load(self):
        s=load_json_file(self.path,_default(),expected_type=dict)
        for k,v in _default().items(): s.setdefault(k,deepcopy(v))
        return s
    def snapshot(self): return deepcopy(self._load())
    def register(self,event_id:str,*,signal_type:str,left_record_type:str,left_record_id:str,right_record_type:str="",right_record_id:str="",dependency_ids:list[str]|None=None,left_confidence:float=.5,right_confidence:float=.5,severity:float=.5,uncertainty:float=.5,sensitivity:str="normal",structural_digest:str=""):
        event_id=_clean(event_id,180); signal_type=_clean(signal_type,80); left_record_type=_clean(left_record_type,40); right_record_type=_clean(right_record_type,40); left_record_id=_clean(left_record_id,220); right_record_id=_clean(right_record_id,220)
        if not event_id or signal_type not in SIGNAL_TYPES or left_record_type not in RECORD_TYPES or not left_record_id: raise ValueError("valid event, signal type, and left lineage required")
        if right_record_type and right_record_type not in RECORD_TYPES: raise ValueError("invalid right record type")
        deps=sorted(set(_clean(x,220) for x in (dependency_ids or []) if _clean(x,220)))
        clamp=lambda x:round(max(0.0,min(float(x),1.0)),4)
        semantic=_digest(signal_type,left_record_type,left_record_id,right_record_type,right_record_id,*deps,structural_digest)
        with metadata_mutation_lock(self.path,timeout_seconds=5):
            s=self._load(); prior=next((x for x in s["processed_events"] if x.get("event_id")==event_id),None)
            if prior:return {"ok":True,"status":"duplicate_event_ignored","result":deepcopy(prior["result"]),"idempotent":True}
            dup=next((x for x in s["signals"] if x.get("semantic_key")==semantic and x.get("state")=="active"),None)
            if dup: result={"status":"duplicate_signal_ignored","signal_id":dup["signal_id"]}
            else:
                now=self.clock(); sid=f"epistemic-coherence-signal-{semantic[:24]}"; row={"signal_id":sid,"semantic_key":semantic,"signal_type":signal_type,"left_record_type":left_record_type,"left_record_id":left_record_id,"right_record_type":right_record_type,"right_record_id":right_record_id,"dependency_ids":deps,"left_confidence":clamp(left_confidence),"right_confidence":clamp(right_confidence),"severity":clamp(severity),"uncertainty":clamp(uncertainty),"sensitivity":_clean(sensitivity,32),"structural_digest":_clean(structural_digest,128),"state":"active","created_at":now,"updated_at":now,"history":[{"change":"registered","occurred_at":now,"content_free":True}],"repair_id":"","attention_id":"","proposal_id":"","approval_id":"","authorization_id":"","action_id":""}; s["signals"].append(row); result={"status":"epistemic_coherence_signal_registered","signal_id":sid}
            now=self.clock(); s["processed_events"].append({"event_id":event_id,"event_digest":_digest(event_id),"occurred_at":now,"result":deepcopy(result),"content_free":True}); s["revision"]+=1; s["updated_at"]=now; write_json_atomic(self.path,s,expected_type=dict,sort_keys=True); return {"ok":True,"status":result["status"],"result":result,"idempotent":False}
    def revise(self,event_id:str,signal_id:str,*,new_state:str,replacement_id:str=""):
        if new_state not in STATES-{"active"}: raise ValueError("invalid state")
        with metadata_mutation_lock(self.path,timeout_seconds=5):
            s=self._load(); prior=next((x for x in s["processed_events"] if x.get("event_id")==event_id),None)
            if prior:return {"ok":True,"status":"duplicate_event_ignored","result":deepcopy(prior["result"]),"idempotent":True}
            row=next((x for x in s["signals"] if x.get("signal_id")==signal_id),None)
            if not row: raise ValueError("unknown signal")
            now=self.clock(); row["state"]=new_state; row["replacement_id"]=_clean(replacement_id,220); row["updated_at"]=now; row["history"].append({"change":new_state,"occurred_at":now,"content_free":True}); result={"status":"epistemic_coherence_signal_revised","signal_id":signal_id,"state":new_state}; s["processed_events"].append({"event_id":event_id,"event_digest":_digest(event_id),"occurred_at":now,"result":deepcopy(result),"content_free":True}); s["revision"]+=1; s["updated_at"]=now; write_json_atomic(self.path,s,expected_type=dict,sort_keys=True); return {"ok":True,"status":result["status"],"result":result,"idempotent":False}
    def inspection_summary(self):
        s=self._load(); counts={}
        for x in s["signals"]: counts[x.get("state")]=counts.get(x.get("state"),0)+1
        keys=("signal_id","signal_type","left_record_type","left_record_id","right_record_type","right_record_id","dependency_ids","left_confidence","right_confidence","severity","uncertainty","sensitivity","structural_digest","state","replacement_id","repair_id","attention_id","proposal_id","approval_id","authorization_id","action_id")
        return {"ok":True,"contract_version":CONTRACT_VERSION,"signal_count":len(s["signals"]),"state_counts":counts,"recent_signals":[{k:x.get(k) for k in keys} for x in s["signals"][-24:]],"authority_boundary":deepcopy(s["authority_boundary"]),"raw_messages_exposed":False,"prompts_exposed":False,"provider_payloads_exposed":False,"evidence_text_exposed":False,"knowledge_text_exposed":False,"belief_text_exposed":False,"self_model_text_exposed":False,"hidden_reasoning_exposed":False,"runtime_mutated":False}
def build_epistemic_coherence_signal_inspection(runtime_root=None): return EpistemicCoherenceSignalStore(runtime_root).inspection_summary()
