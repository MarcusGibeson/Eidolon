from __future__ import annotations
"""Read-only v1185.5 persistent campaign continuation checkpoint."""
import hashlib
from pathlib import Path
from typing import Any
from checkpoint_registry import inspect_checkpoint_registry
from persistent_development_campaign import create_campaign_charter, create_campaign_review, create_campaign_ledger
from persistent_development_campaign_continuation import *
CONTRACT_VERSION="v1185.5"
def _h(s:str)->str:return hashlib.sha256(s.encode()).hexdigest()
def build_persistent_development_campaign_continuation_checkpoint(*,source_root:str|Path|None=None,runtime_root:str|Path|None=None)->dict[str,Any]:
    checks=[]; req=lambda x:checks.append(bool(x))
    c=create_campaign_charter(campaign_id="campaign-alpha",source_baseline_digest=_h("source"),scope_digest=_h("scope"),goal_digests=[_h("g1")],limits={"max_work_items":3,"max_sessions":4,"max_elapsed_seconds":3600})
    r=create_campaign_review(charter=c,decision="approve",operator_decision_digest=_h("approve"))
    item={"work_item_id":"w1","status":"queued","work_item_digest":_h("w1"),"content_free":True}; l=create_campaign_ledger(charter=c,review=r,work_items=[item])
    snap=create_campaign_session_snapshot(charter=c,review=r,ledger=l,session_id="s1",session_index=1,state="ready",consumed={"sessions":1})
    review=create_work_selection_review(snapshot=snap,ledger=l,candidate_work_item_ids=["w1"],decision="approve",operator_decision_digest=_h("select"))
    sel=create_bounded_work_selection(charter=c,snapshot=snap,ledger=l,selection_review=review,max_items=1)
    trans=create_session_transition(snapshot=snap,requested_state="active",operator_transition_digest=_h("active")); summary=continuation_public_summary(snap,sel,trans)
    for x in [snap["status"]=="session_snapshot_ready",review["status"]=="selection_approved",sel["status"]=="bounded_selection_ready",trans["status"]=="transition_recorded",summary["content_free"],not summary["work_executed"],not summary["authority_granted"]]:req(x)
    req(create_session_transition(snapshot=snap,requested_state="completed",operator_transition_digest=_h("bad"))["status"]=="blocked")
    bad=dict(snap);bad["state"]="active";req("tampered_snapshot" in create_work_selection_review(snapshot=bad,ledger=l,candidate_work_item_ids=["w1"],decision="approve",operator_decision_digest=_h("x"))["errors"])
    reg=inspect_checkpoint_registry(source_root=source_root); row=next((x for x in reg["checkpoints"] if x["checkpoint_id"]=="persistent-development-campaign-continuation-checkpoint"),{})
    req(row.get("builder")=="build_persistent_development_campaign_continuation_checkpoint");req(reg["duplicate_checkpoint_ids"]==[])
    return {"ok":all(checks),"contract_version":CONTRACT_VERSION,"checkpoint_id":"persistent-development-campaign-continuation:v1185.5","passed":sum(checks),"total":len(checks),"read_only":True,"content_free":True,"summary":summary,"production_source_modified":False,"sandbox_modified":False,"execution_invoked":False,"provider_contacted":False,"model_contacted":False,"authority_granted":False,"campaign_work_started":False,"automatic_resume":False,"release_authorized":False,"desktop_verification_deferred_until_v1200":True}
