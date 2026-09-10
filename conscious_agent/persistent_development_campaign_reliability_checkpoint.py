from __future__ import annotations
"""Read-only v1185.8 campaign reliability checkpoint."""
import hashlib,json
from pathlib import Path
from typing import Any
from checkpoint_registry import inspect_checkpoint_registry
from persistent_development_campaign import *
from persistent_development_campaign_continuation import *
from persistent_development_campaign_reliability import *
CONTRACT_VERSION="v1185.8"
def _h(s:str)->str:return hashlib.sha256(s.encode()).hexdigest()
def build_persistent_development_campaign_reliability_checkpoint(*,source_root:str|Path|None=None,runtime_root:str|Path|None=None)->dict[str,Any]:
 checks=[];req=lambda x:checks.append(bool(x))
 c=create_campaign_charter(campaign_id="c",source_baseline_digest=_h("source"),scope_digest=_h("scope"),goal_digests=[_h("goal")],limits={"max_work_items":2,"max_sessions":3,"max_elapsed_seconds":100,"max_disk_bytes":1000,"max_token_budget":200})
 r=create_campaign_review(charter=c,decision="approve",operator_decision_digest=_h("approve"));l=create_campaign_ledger(charter=c,review=r,work_items=[{"work_item_id":"w1","status":"queued","work_item_digest":_h("w1"),"content_free":True}])
 s=create_campaign_session_snapshot(charter=c,review=r,ledger=l,session_id="s1",session_index=1,state="active",consumed={"sessions":1});s["source_baseline_digest"]=_h("source");u=dict(s);u.pop("snapshot_digest",None);s["snapshot_digest"]=hashlib.sha256(json.dumps(u,sort_keys=True,separators=(",",":"),ensure_ascii=True,default=str).encode()).hexdigest()
 q=create_work_selection_review(snapshot=s,ledger=l,candidate_work_item_ids=["w1"],decision="approve",operator_decision_digest=_h("q"));sel=create_bounded_work_selection(charter=c,snapshot=s,ledger=l,selection_review=q,max_items=1)
 b=create_campaign_budget_receipt(charter=c,snapshot=s,observed={"work_items":1,"sessions":1,"elapsed_seconds":10,"disk_bytes":100,"token_budget":20});a=create_stale_work_assessment(snapshot=s,selection=sel,current_source_digest=_h("source"),work_states={"w1":"current"});rec=create_campaign_recovery_receipt(snapshot=s,budget_receipt=b,stale_assessment=a,reason="process_restart",prior_runtime_digest=_h("old"),restarted_runtime_digest=_h("new"));summary=reliability_public_summary(b,a,rec)
 for x in [b["status"]=="budget_within_limits",a["status"]=="work_current",rec["status"]=="recovery_review_required",summary["content_free"],not summary["work_executed"],not summary["durable_resume_performed"],not summary["authority_granted"]]:req(x)
 req(create_campaign_budget_receipt(charter=c,snapshot=s,observed={"elapsed_seconds":101})["status"]=="budget_exhausted")
 req(create_stale_work_assessment(snapshot=s,selection=sel,current_source_digest=_h("drift"),work_states={"w1":"stale"})["status"]=="reconciliation_required")
 reg=inspect_checkpoint_registry(source_root=source_root);row=next((x for x in reg["checkpoints"] if x["checkpoint_id"]=="persistent-development-campaign-reliability-checkpoint"),{});req(row.get("builder")=="build_persistent_development_campaign_reliability_checkpoint");req(reg["duplicate_checkpoint_ids"]==[])
 return {"ok":all(checks),"contract_version":"v1185.8","checkpoint_id":"persistent-development-campaign-reliability:v1185.8","passed":sum(checks),"total":len(checks),"read_only":True,"content_free":True,"summary":summary,"production_source_modified":False,"sandbox_modified":False,"execution_invoked":False,"provider_contacted":False,"model_contacted":False,"authority_granted":False,"durable_resume_performed":False,"release_authorized":False,"desktop_verification_deferred_until_v1200":True}
