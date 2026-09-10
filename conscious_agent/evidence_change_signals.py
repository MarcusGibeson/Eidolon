from __future__ import annotations
"""Content-free v1118.0 evidence change signals for bounded belief reconsideration intake."""
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
CONTRACT_VERSION="v1118.0"; SCHEMA_VERSION="1"
CHANGE_TYPES={"evidence_added","evidence_corrected","evidence_retracted","evidence_stale","provenance_invalidated","contradiction_detected","confidence_changed","uncertainty_changed","scheduled_reconsideration_due"}
STATES={"active","corrected","retracted","superseded","stale","retired"}
def _now(): return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00","Z")
def _clean(v:Any,n=300): return " ".join(str(v or "").split())[:n]
def _digest(*p:Any): return hashlib.sha256("\x1f".join(_clean(x,2000) for x in p).encode()).hexdigest()
def _root(): return Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1]/"data").expanduser().resolve()/"cognition"
def _default(): return {"schema_version":SCHEMA_VERSION,"contract_version":CONTRACT_VERSION,"signals":[],"processed_events":[],"revision":0,"updated_at":"","authority_boundary":{"can_revise_belief":False,"can_select_attention":False,"can_create_proposal":False,"can_approve":False,"can_authorize":False,"can_execute":False,"can_browse":False,"can_contact_provider":False}}
class EvidenceChangeSignalStore:
    def __init__(self,runtime_root=None,*,clock:Callable[[],str]|None=None): self.runtime_root=Path(runtime_root).expanduser().resolve() if runtime_root else _root(); self.path=self.runtime_root/"evidence_change_signals.json"; self.clock=clock or _now
    def _load(self):
        s=load_json_file(self.path,_default(),expected_type=dict)
        for k,v in _default().items(): s.setdefault(k,deepcopy(v))
        return s
    def snapshot(self): return deepcopy(self._load())
    def register(self,event_id:str,*,belief_id:str,evidence_id:str,change_type:str,source_state:str="",confidence_delta:float=0.0,uncertainty_delta:float=0.0,contradiction_severity:float=0.0,scheduled_for:str="",structural_digest:str=""):
        event_id=_clean(event_id,180); belief_id=_clean(belief_id,220); evidence_id=_clean(evidence_id,220); change_type=_clean(change_type,80)
        if not event_id or not belief_id or change_type not in CHANGE_TYPES: raise ValueError("valid event_id, belief_id, and change_type required")
        clamp=lambda x:round(max(-1.0,min(float(x),1.0)),4)
        semantic=_digest(belief_id,evidence_id,change_type,source_state,confidence_delta,uncertainty_delta,contradiction_severity,scheduled_for,structural_digest)
        with metadata_mutation_lock(self.path,timeout_seconds=5):
            s=self._load(); prior=next((x for x in s["processed_events"] if x.get("event_id")==event_id),None)
            if prior:return {"ok":True,"status":"duplicate_event_ignored","result":deepcopy(prior["result"]),"idempotent":True}
            dup=next((x for x in s["signals"] if x.get("semantic_key")==semantic and x.get("state")=="active"),None)
            if dup: result={"status":"duplicate_signal_ignored","signal_id":dup["signal_id"]}
            else:
                now=self.clock(); sid=f"evidence-change-signal-{semantic[:24]}"; row={"signal_id":sid,"semantic_key":semantic,"belief_id":belief_id,"evidence_id":evidence_id,"change_type":change_type,"source_state":_clean(source_state,64),"confidence_delta":clamp(confidence_delta),"uncertainty_delta":clamp(uncertainty_delta),"contradiction_severity":round(max(0.0,min(float(contradiction_severity),1.0)),4),"scheduled_for":_clean(scheduled_for,64),"structural_digest":_clean(structural_digest,128),"state":"active","created_at":now,"updated_at":now,"history":[{"change":"registered","occurred_at":now,"content_free":True}],"belief_revision_id":"","attention_id":"","proposal_id":"","approval_id":"","authorization_id":"","action_id":""}; s["signals"].append(row); result={"status":"evidence_change_signal_registered","signal_id":sid}
            now=self.clock(); s["processed_events"].append({"event_id":event_id,"event_digest":_digest(event_id),"occurred_at":now,"result":deepcopy(result),"content_free":True}); s["revision"]+=1; s["updated_at"]=now; write_json_atomic(self.path,s,expected_type=dict,sort_keys=True); return {"ok":True,"status":result["status"],"result":result,"idempotent":False}
    def revise(self,event_id:str,signal_id:str,*,new_state:str,replacement_id:str=""):
        if new_state not in STATES-{"active"}: raise ValueError("invalid state")
        with metadata_mutation_lock(self.path,timeout_seconds=5):
            s=self._load(); prior=next((x for x in s["processed_events"] if x.get("event_id")==event_id),None)
            if prior:return {"ok":True,"status":"duplicate_event_ignored","result":deepcopy(prior["result"]),"idempotent":True}
            row=next((x for x in s["signals"] if x.get("signal_id")==signal_id),None)
            if not row: raise ValueError("unknown signal")
            now=self.clock(); row["state"]=new_state; row["replacement_id"]=_clean(replacement_id,220); row["updated_at"]=now; row["history"].append({"change":new_state,"occurred_at":now,"content_free":True}); result={"status":"evidence_change_signal_revised","signal_id":signal_id,"state":new_state}; s["processed_events"].append({"event_id":event_id,"event_digest":_digest(event_id),"occurred_at":now,"result":deepcopy(result),"content_free":True}); s["revision"]+=1; s["updated_at"]=now; write_json_atomic(self.path,s,expected_type=dict,sort_keys=True); return {"ok":True,"status":result["status"],"result":result,"idempotent":False}
    def inspection_summary(self):
        s=self._load(); counts={}
        for x in s["signals"]: counts[x.get("state")]=counts.get(x.get("state"),0)+1
        keys=("signal_id","belief_id","evidence_id","change_type","source_state","confidence_delta","uncertainty_delta","contradiction_severity","scheduled_for","structural_digest","state","replacement_id","belief_revision_id","attention_id","proposal_id","approval_id","authorization_id","action_id")
        return {"ok":True,"contract_version":CONTRACT_VERSION,"signal_count":len(s["signals"]),"state_counts":counts,"recent_signals":[{k:x.get(k) for k in keys} for x in s["signals"][-24:]],"authority_boundary":deepcopy(s["authority_boundary"]),"raw_messages_exposed":False,"prompts_exposed":False,"provider_payloads_exposed":False,"evidence_text_exposed":False,"hidden_reasoning_exposed":False,"runtime_mutated":False}
def build_evidence_change_signal_inspection(runtime_root=None): return EvidenceChangeSignalStore(runtime_root).inspection_summary()
