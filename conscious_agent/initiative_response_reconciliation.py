from __future__ import annotations
"""v1108.7 bounded response and retirement lifecycle for surfaced initiatives."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib, os
from pathlib import Path
from typing import Callable
from surfaced_initiative_reconciliation import SurfacedInitiativeReconciliationStore
from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock

CONTRACT_VERSION="v1108.7"
_ALLOWED={"acknowledged","dismissed","interrupted","superseded","deferred","retired"}
_TERMINAL={"acknowledged","dismissed","superseded","retired"}
def _now(): return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00","Z")
def _clean(v,n=500): return " ".join(str(v or "").split())[:n]
def _digest(*parts): return hashlib.sha256("\x1f".join(_clean(x,3000) for x in parts).encode()).hexdigest()
def _root(): return Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1]/"data").expanduser().resolve()/"cognition"
def _default(): return {"schema_version":"1","contract_version":CONTRACT_VERSION,"outcomes":[],"processed_events":[],"revision":0,"updated_at":"","controls":{"max_outcomes":256,"max_active_deferred":24},"authority_boundary":{"can_generate":False,"can_send":False,"can_retry":False,"can_notify":False,"can_browse":False,"can_execute":False,"can_authorize":False,"can_modify_files":False,"can_manage_models":False,"can_approve":False,"can_promote":False,"can_certify":False}}
class InitiativeResponseReconciliationStore:
 def __init__(self,runtime_root=None,*,clock:Callable[[],str]|None=None): self.runtime_root=Path(runtime_root).expanduser().resolve() if runtime_root else _root(); self.path=self.runtime_root/"initiative_response_reconciliation.json"; self.clock=clock or _now; self.surfaces=SurfacedInitiativeReconciliationStore(self.runtime_root)
 def _load(self):
  state=load_json_file(self.path,_default(),expected_type=dict)
  if state.get("schema_version")!="1": state=_default()
  for k,v in _default().items(): state.setdefault(k,deepcopy(v))
  return state
 def snapshot(self): return deepcopy(self._load())
 def reconcile(self,event_id,*,surface_receipt_id,outcome,explicit_user_signal=False,meaningful_context_change=False):
  event_id=_clean(event_id,180); surface_receipt_id=_clean(surface_receipt_id,180); outcome=_clean(outcome,40)
  if not event_id or not surface_receipt_id: raise ValueError("event_id and surface_receipt_id required")
  if outcome not in _ALLOWED: raise ValueError("unsupported response outcome")
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   state=self._load(); prior=next((x for x in state["processed_events"] if x.get("event_id")==event_id),None)
   if prior:return {"ok":True,"status":"duplicate_response_event_ignored","outcome":deepcopy(prior["outcome"]),"idempotent":True}
   surface=next((x for x in self.surfaces.snapshot().get("receipts",[]) if x.get("receipt_id")==surface_receipt_id),None)
   existing=next((x for x in reversed(state["outcomes"]) if x.get("surface_receipt_id")==surface_receipt_id),None)
   final=outcome; reason="response_reconciled"
   if not surface or surface.get("outcome")!="shown": final="retired"; reason="shown_surface_missing"
   elif existing and existing.get("terminal"): final=existing.get("outcome","retired"); reason="terminal_outcome_preserved"
   elif outcome in {"acknowledged","dismissed"} and not explicit_user_signal: final="deferred"; reason="explicit_user_signal_required"
   elif outcome=="interrupted" and not meaningful_context_change: final="deferred"; reason="interruption_without_state_change"
   now=self.clock(); oid=f"initiative-response-{_digest(event_id,surface_receipt_id,final,reason)[:24]}"; row={"outcome_id":oid,"surface_receipt_id":surface_receipt_id,"proposal_id":(surface or {}).get("proposal_id",""),"outcome":final,"reason_code":reason,"terminal":final in _TERMINAL,"active":final in {"deferred","interrupted"},"explicit_user_signal":bool(explicit_user_signal),"meaningful_context_change":bool(meaningful_context_change),"occurred_at":now,"retry_scheduled":False,"message_sent":False,"authority_granted":False,"content_free":True}
   state["outcomes"]=(state["outcomes"]+[row])[-int(state["controls"]["max_outcomes"]):]; state["processed_events"]=(state["processed_events"]+[{"event_id":event_id,"outcome":deepcopy(row)}])[-1024:]; state["revision"]+=1; state["updated_at"]=now; write_json_atomic(self.path,state,expected_type=dict,sort_keys=True); return {"ok":True,"status":final,"outcome":row,"idempotent":False}
 def inspection_summary(self):
  state=self._load(); rows=state["outcomes"]; counts={k:sum(x.get("outcome")==k for x in rows) for k in _ALLOWED}
  return {"ok":True,"contract_version":CONTRACT_VERSION,"revision":state["revision"],"outcome_count":len(rows),"active_outcome_count":sum(x.get("active") is True for x in rows),"terminal_outcome_count":sum(x.get("terminal") is True for x in rows),"outcome_counts":counts,"recent_outcomes":deepcopy(rows[-24:]),"authority_boundary":deepcopy(state["authority_boundary"]),"provider_contacted":False,"message_sent":False,"notification_sent":False,"automatic_retry":False,"external_action_executed":False,"hidden_reasoning_exposed":False,"private_content_exposed":False,"runtime_mutated":False}
def build_initiative_response_reconciliation_inspection(runtime_root=None): return InitiativeResponseReconciliationStore(runtime_root).inspection_summary()
