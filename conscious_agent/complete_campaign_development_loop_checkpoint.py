from __future__ import annotations
"""Read-only v1188.2 Complete Campaign Development Loop Foundations checkpoint."""
import hashlib, json
from pathlib import Path
from typing import Any, Mapping
from checkpoint_registry import inspect_checkpoint_registry
from complete_campaign_development_loop import STAGES, create_campaign_development_stage, integrate_complete_campaign_development_loop, complete_campaign_development_loop_public_summary
CONTRACT_VERSION="v1188.2"
def _h(v:str)->str:return hashlib.sha256(v.encode()).hexdigest()
def _sign(row:Mapping[str,Any],field:str)->dict[str,Any]:
 x=dict(row); x[field]=hashlib.sha256(json.dumps(x,sort_keys=True,separators=(",",":"),ensure_ascii=True).encode()).hexdigest(); return x
def _fixtures():
 c=_sign({"contract_version":"v1185.2","campaign_id":"campaign-v1188","scope_digest":_h("scope"),"goal_digests":[_h("goal")],"content_free":True},"charter_digest")
 r=_sign({"contract_version":"v1185.2","campaign_id":"campaign-v1188","decision":"approve","status":"campaign_approved","content_free":True},"review_digest")
 s=_sign({"contract_version":"v1185.5","campaign_id":"campaign-v1188","campaign_state":"active","session_id":"session-1","content_free":True},"session_snapshot_digest")
 w=_sign({"contract_version":"v1185.5","campaign_id":"campaign-v1188","selected_work_item_ids":["work-1"],"status":"selected_not_executed","content_free":True},"selection_digest")
 rows=[]; prev=""
 for stage in STAGES:
  row=create_campaign_development_stage(campaign_id="campaign-v1188",work_item_id="work-1",stage=stage,status="completed",artifact_digest=_h(stage),previous_stage_digest=prev,operator_review_digest=_h(stage+":review") if stage=="approval" else "")
  rows.append(row); prev=row["stage_receipt_digest"]
 return c,r,s,w,rows

def build_complete_campaign_development_loop_checkpoint(*,source_root:str|Path|None=None,runtime_root:str|Path|None=None)->dict[str,Any]:
 source=Path(source_root or Path(__file__).resolve().parents[1]).resolve(); checks=[]
 def req(v):checks.append(bool(v))
 c,r,s,w,rows=_fixtures(); loop=integrate_complete_campaign_development_loop(campaign_charter=c,campaign_review=r,session_snapshot=s,work_selection=w,stages=rows); summary=complete_campaign_development_loop_public_summary(loop)
 req(loop["complete_loop"]); req(loop["status"]=="complete_review_required"); req(loop["stage_count"]==10); req(loop["error_count"]==0); req(summary["content_free"]); req(not loop["production_source_modified"]); req(not loop["sandbox_modified"]); req(not loop["execution_invoked"]); req(not loop["learning_applied"]); req(not loop["authority_granted"])
 req(integrate_complete_campaign_development_loop(campaign_charter=c,campaign_review=r,session_snapshot=s,work_selection=w,stages=rows[:-1])["status"]=="blocked")
 bad=dict(rows[2]); bad["artifact_digest"]="0"*64; req("tampered_stage_receipt" in integrate_complete_campaign_development_loop(campaign_charter=c,campaign_review=r,session_snapshot=s,work_selection=w,stages=[*rows[:2],bad,*rows[3:]])["errors"])
 wrong=[dict(x) for x in rows]; wrong[3]["previous_stage_digest"]="f"*64; req("stage_link_mismatch" in integrate_complete_campaign_development_loop(campaign_charter=c,campaign_review=r,session_snapshot=s,work_selection=w,stages=wrong)["errors"])
 noapproval=[dict(x) for x in rows]; noapproval[4]=create_campaign_development_stage(campaign_id="campaign-v1188",work_item_id="work-1",stage="approval",status="completed",artifact_digest=_h("approval"),previous_stage_digest=rows[3]["stage_receipt_digest"]); req("missing_stage_approval" in integrate_complete_campaign_development_loop(campaign_charter=c,campaign_review=r,session_snapshot=s,work_selection=w,stages=noapproval)["errors"])
 rejected=dict(r); rejected["decision"]="reject"; rejected["status"]="campaign_rejected"; rejected.pop("review_digest"); rejected=_sign(rejected,"review_digest"); req("campaign_not_approved" in integrate_complete_campaign_development_loop(campaign_charter=c,campaign_review=rejected,session_snapshot=s,work_selection=w,stages=rows)["errors"])
 registry=inspect_checkpoint_registry(source_root=source); row=next((x for x in registry["checkpoints"] if x["checkpoint_id"]=="complete-campaign-development-loop-checkpoint"),{}); req(row.get("builder")=="build_complete_campaign_development_loop_checkpoint"); req(registry["duplicate_checkpoint_ids"]==[])
 return {"ok":all(checks),"contract_version":CONTRACT_VERSION,"checkpoint_id":"complete-campaign-development-loop:v1188.2","passed":sum(checks),"total":len(checks),"read_only":True,"post_available":False,"content_free":True,"summary":summary,"production_source_modified":False,"sandbox_modified":False,"execution_invoked":False,"provider_contacted":False,"model_contacted":False,"learning_applied":False,"authority_granted":False,"desktop_verification_deferred_until_v1200":True}
