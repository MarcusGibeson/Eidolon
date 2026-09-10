from __future__ import annotations
"""v1108.6 durable accounting for initiative proposals explicitly surfaced by normal chat."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib, os
from pathlib import Path
from typing import Callable
from initiative_communication_restraint import InitiativeCommunicationRestraint
from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock

CONTRACT_VERSION = "v1108.6"
_ALLOWED = {"shown", "not_shown", "interrupted", "superseded"}

def _now(): return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
def _clean(v, n=500): return " ".join(str(v or "").split())[:n]
def _digest(*parts): return hashlib.sha256("\x1f".join(_clean(x, 3000) for x in parts).encode()).hexdigest()
def _root(): return Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1]/"data").expanduser().resolve()/"cognition"
def _default():
    return {"schema_version":"1","contract_version":CONTRACT_VERSION,"receipts":[],"processed_events":[],"revision":0,"updated_at":"","controls":{"max_receipts":256},"state_separation":{"proposal_is_surface_receipt":False,"surface_receipt_is_message":False,"message_is_authorization":False,"authorization_is_execution":False},"authority_boundary":{"can_generate":False,"can_send":False,"can_notify":False,"can_browse":False,"can_execute":False,"can_authorize":False,"can_modify_files":False,"can_manage_models":False,"can_approve":False,"can_promote":False,"can_certify":False}}

class SurfacedInitiativeReconciliationStore:
    def __init__(self, runtime_root=None, *, clock:Callable[[],str]|None=None):
        self.runtime_root=Path(runtime_root).expanduser().resolve() if runtime_root else _root(); self.path=self.runtime_root/"surfaced_initiative_reconciliation.json"; self.clock=clock or _now; self.restraint=InitiativeCommunicationRestraint(self.runtime_root)
    def _load(self):
        state=load_json_file(self.path,_default(),expected_type=dict)
        if state.get("schema_version")!="1": state=_default()
        for k,v in _default().items(): state.setdefault(k,deepcopy(v))
        return state
    def snapshot(self): return deepcopy(self._load())
    def record(self,event_id,*,decision_id,outcome,normal_chat_turn_id="",conversation_session_id="",explicit_surface_event=False):
        event_id=_clean(event_id,180); decision_id=_clean(decision_id,180); outcome=_clean(outcome,40)
        if not event_id or not decision_id: raise ValueError("event_id and decision_id required")
        if outcome not in _ALLOWED: raise ValueError("unsupported surface outcome")
        with metadata_mutation_lock(self.path,timeout_seconds=5):
            state=self._load(); prior=next((x for x in state["processed_events"] if x.get("event_id")==event_id),None)
            if prior: return {"ok":True,"status":"duplicate_surface_event_ignored","receipt":deepcopy(prior["receipt"]),"idempotent":True}
            decision=next((x for x in self.restraint.snapshot().get("decisions",[]) if x.get("decision_id")==decision_id),None)
            valid=bool(decision and decision.get("outcome")=="eligible_to_surface" and explicit_surface_event)
            if outcome=="shown" and (not normal_chat_turn_id or not valid): final="not_shown"; reason="explicit_normal_chat_surface_evidence_missing"
            elif not decision: final="not_shown"; reason="timing_decision_missing"
            elif decision.get("outcome")!="eligible_to_surface": final="not_shown"; reason="proposal_not_eligible"
            else: final=outcome; reason="normal_chat_surface_reconciled"
            now=self.clock(); rid=f"initiative-surface-{_digest(event_id,decision_id,final,normal_chat_turn_id)[:24]}"
            row={"receipt_id":rid,"decision_id":decision_id,"proposal_id":(decision or {}).get("proposal_id",""),"outcome":final,"reason_code":reason,"normal_chat_turn_digest":_digest(normal_chat_turn_id) if normal_chat_turn_id else "","conversation_session_digest":_digest(conversation_session_id) if conversation_session_id else "","explicit_surface_event":bool(explicit_surface_event),"occurred_at":now,"active":final=="shown","message_generated":False,"message_sent":False,"notification_sent":False,"authority_granted":False,"content_free":True}
            state["receipts"]=(state["receipts"]+[row])[-int(state["controls"]["max_receipts"]):]; state["processed_events"]=(state["processed_events"]+[{"event_id":event_id,"receipt":deepcopy(row)}])[-1024:]; state["revision"]+=1; state["updated_at"]=now; write_json_atomic(self.path,state,expected_type=dict,sort_keys=True)
            return {"ok":True,"status":final,"receipt":row,"idempotent":False}
    def inspection_summary(self):
        state=self._load(); rows=state["receipts"]; counts={k:sum(x.get("outcome")==k for x in rows) for k in _ALLOWED}
        return {"ok":True,"contract_version":CONTRACT_VERSION,"revision":state["revision"],"receipt_count":len(rows),"active_surface_count":sum(x.get("active") is True for x in rows),"outcome_counts":counts,"recent_receipts":deepcopy(rows[-24:]),"state_separation":deepcopy(state["state_separation"]),"authority_boundary":deepcopy(state["authority_boundary"]),"provider_contacted":False,"message_generated":False,"message_sent":False,"notification_sent":False,"external_action_executed":False,"hidden_reasoning_exposed":False,"private_content_exposed":False,"runtime_mutated":False}

def build_surfaced_initiative_reconciliation_inspection(runtime_root=None): return SurfacedInitiativeReconciliationStore(runtime_root).inspection_summary()
