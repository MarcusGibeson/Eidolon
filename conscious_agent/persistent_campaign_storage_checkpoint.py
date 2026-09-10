from __future__ import annotations
"""Read-only/source-isolated v1186.2 durable campaign storage checkpoint."""
import hashlib,tempfile
from pathlib import Path
from typing import Any
from checkpoint_registry import inspect_checkpoint_registry
from persistent_development_campaign import create_campaign_charter, create_campaign_review, create_campaign_ledger
from persistent_development_campaign_continuation import create_campaign_session_snapshot
from persistent_campaign_storage import *
CONTRACT_VERSION="v1186.2"
def _h(s:str)->str:return hashlib.sha256(s.encode()).hexdigest()
def build_persistent_campaign_storage_checkpoint(*,source_root:str|Path|None=None,runtime_root:str|Path|None=None)->dict[str,Any]:
    checks=[]; req=lambda x:checks.append(bool(x)); runtime=Path(runtime_root) if runtime_root else Path(tempfile.mkdtemp(prefix="eidolon-v1186-"))
    c=create_campaign_charter(campaign_id="campaign-alpha",source_baseline_digest=_h("source"),scope_digest=_h("scope"),goal_digests=[_h("goal")],limits={"max_work_items":2,"max_sessions":3,"max_elapsed_seconds":100,"max_disk_bytes":1000,"max_token_budget":200})
    r=create_campaign_review(charter=c,decision="approve",operator_decision_digest=_h("approve")); l=create_campaign_ledger(charter=c,review=r,work_items=[]); s=create_campaign_session_snapshot(charter=c,review=r,ledger=l,session_id="session-1",session_index=1,state="paused")
    rec=create_campaign_storage_record(charter=c,review=r,ledger=l,snapshot=s,storage_generation=1,operator_storage_digest=_h("store")); stored=persist_campaign_storage_record(runtime_root=runtime,record=rec); restored=restore_campaign_storage_record(runtime_root=runtime,campaign_id="campaign-alpha",expected_record_digest=rec["storage_record_digest"],current_source_digest=_h("source")); review=create_restoration_review(restoration=restored,decision="approve",operator_decision_digest=_h("restore")); summary=storage_public_summary(rec,stored,restored,review)
    for value in [rec["status"]=="ready_for_runtime_storage",stored["status"]=="stored",restored["status"]=="restoration_review_required",review["status"]=="approved_not_resumed",summary["content_free"],summary["runtime_written"],not summary["source_modified"],not summary["work_resumed"],not summary["automatic_resume"],not summary["authority_granted"]]:req(value)
    req(restore_campaign_storage_record(runtime_root=runtime,campaign_id="campaign-alpha",expected_record_digest=rec["storage_record_digest"],current_source_digest=_h("drift"))["status"]=="reconciliation_required")
    bad=dict(rec);bad["session_id"]="tampered";req(persist_campaign_storage_record(runtime_root=runtime,record=bad)["status"]=="blocked")
    reg=inspect_checkpoint_registry(source_root=source_root); row=next((x for x in reg["checkpoints"] if x["checkpoint_id"]=="persistent-campaign-storage-checkpoint"),{});req(row.get("builder")=="build_persistent_campaign_storage_checkpoint");req(reg["duplicate_checkpoint_ids"]==[])
    return {"ok":all(checks),"contract_version":CONTRACT_VERSION,"checkpoint_id":"persistent-campaign-storage:v1186.2","passed":sum(checks),"total":len(checks),"read_only_source":True,"runtime_storage_tested":True,"content_free":True,"summary":summary,"production_source_modified":False,"sandbox_modified":False,"work_executed":False,"work_resumed":False,"automatic_resume":False,"provider_contacted":False,"model_contacted":False,"authority_granted":False,"release_authorized":False,"desktop_verification_deferred_until_v1200":True}
