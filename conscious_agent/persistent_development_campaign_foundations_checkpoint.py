from __future__ import annotations
"""Read-only v1185.2 persistent development-campaign foundations checkpoint."""
import hashlib
from pathlib import Path
from typing import Any
from checkpoint_registry import inspect_checkpoint_registry
from persistent_development_campaign import *
CONTRACT_VERSION="v1185.2"
def _h(s:str)->str:return hashlib.sha256(s.encode()).hexdigest()
def build_persistent_development_campaign_foundations_checkpoint(*,source_root:str|Path|None=None,runtime_root:str|Path|None=None)->dict[str,Any]:
    checks=[]; req=lambda x:checks.append(bool(x))
    c=create_campaign_charter(campaign_id="campaign-alpha",source_baseline_digest=_h("source"),scope_digest=_h("scope"),goal_digests=[_h("g1"),_h("g2")],limits={"max_work_items":8,"max_sessions":4,"max_elapsed_seconds":3600})
    r=create_campaign_review(charter=c,decision="approve",operator_decision_digest=_h("operator")); l=create_campaign_ledger(charter=c,review=r); s=campaign_public_summary(c,r,l)
    for x in [c["status"]=="ready_for_review",r["status"]=="approved_not_started",l["status"]=="approved_empty_ledger",s["content_free"],not s["work_started"],not s["authority_granted"]]:req(x)
    for decision,status in [("reject","rejected"),("defer","deferred")]: req(create_campaign_review(charter=c,decision=decision,operator_decision_digest=_h(decision))["status"]==status)
    bad=dict(c);bad["scope_digest"]="0"*64;req("tampered_charter" in create_campaign_review(charter=bad,decision="approve",operator_decision_digest=_h("x"))["errors"])
    req(create_campaign_charter(campaign_id="x",source_baseline_digest="bad",scope_digest=_h("s"),goal_digests=[_h("g")],limits={"max_sessions":1})["status"]=="blocked")
    req(create_campaign_charter(campaign_id="x",source_baseline_digest=_h("b"),scope_digest=_h("s"),goal_digests=[_h("g"),_h("g")],limits={"max_sessions":1})["status"]=="blocked")
    reg=inspect_checkpoint_registry(source_root=source_root); row=next((x for x in reg["checkpoints"] if x["checkpoint_id"]=="persistent-development-campaign-foundations-checkpoint"),{})
    req(row.get("builder")=="build_persistent_development_campaign_foundations_checkpoint");req(reg["duplicate_checkpoint_ids"]==[])
    return {"ok":all(checks),"contract_version":CONTRACT_VERSION,"checkpoint_id":"persistent-development-campaign-foundations:v1185.2","passed":sum(checks),"total":len(checks),"read_only":True,"content_free":True,"summary":s,"production_source_modified":False,"sandbox_modified":False,"execution_invoked":False,"provider_contacted":False,"model_contacted":False,"approval_created":False,"authority_granted":False,"campaign_work_started":False,"release_authorized":False,"desktop_verification_deferred_until_v1200":True}
