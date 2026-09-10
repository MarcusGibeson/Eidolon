#!/usr/bin/env python3
import hashlib,json,tempfile
from pathlib import Path
from conscious_agent.persistent_development_campaign import *
from conscious_agent.persistent_development_campaign_continuation import *
from conscious_agent.persistent_campaign_storage import *
from conscious_agent.persistent_campaign_resume_reconciliation import *
from conscious_agent.persistent_campaign_resume_materialization import *
from conscious_agent.persistent_campaign_resume_materialization_checkpoint import build_persistent_campaign_resume_materialization_checkpoint
ROOT=Path(__file__).resolve().parents[1];checks=[]
def req(v,m=""):checks.append(bool(v));assert v,m
def h(s):return hashlib.sha256(s.encode()).hexdigest()
def fixtures(td):
 c=create_campaign_charter(campaign_id="c1",source_baseline_digest=h("src"),scope_digest=h("scope"),goal_digests=[h("g")],limits={"max_work_items":2,"max_sessions":3,"max_elapsed_seconds":100,"max_disk_bytes":1000,"max_token_budget":200});r=create_campaign_review(charter=c,decision="approve",operator_decision_digest=h("a"));l=create_campaign_ledger(charter=c,review=r);s=create_campaign_session_snapshot(charter=c,review=r,ledger=l,session_id="s1",session_index=1,state="paused");sr=create_campaign_storage_record(charter=c,review=r,ledger=l,snapshot=s,operator_storage_digest=h("store"));persist_campaign_storage_record(runtime_root=td,record=sr);rest=restore_campaign_storage_record(runtime_root=td,campaign_id="c1",expected_record_digest=sr["storage_record_digest"],current_source_digest=h("src"));rr=create_restoration_review(restoration=rest,decision="approve",operator_decision_digest=h("restore"));recon=create_resume_reconciliation(restoration=rest,restoration_review=rr,current_charter_digest=c["charter_digest"],current_review_digest=r["review_digest"],current_ledger_digest=l["ledger_digest"],current_snapshot_digest=s["snapshot_digest"]);er=create_resume_eligibility_review(reconciliation=recon,decision="approve",operator_decision_digest=h("resume"));return recon,er
with tempfile.TemporaryDirectory() as td:
 recon,er=fixtures(td);contract=create_resume_materialization_contract(reconciliation=recon,eligibility_review=er,session_id="s2",session_generation=2,operator_materialization_digest=h("m"));req(contract["status"]=="materialization_ready")
 lease=acquire_resume_lease(runtime_root=td,contract=contract,lease_owner_digest=h("owner"),now_epoch=1000);req(lease["status"]=="lease_acquired")
 req(acquire_resume_lease(runtime_root=td,contract=contract,lease_owner_digest=h("other"),now_epoch=1001)["status"]=="blocked")
 mat=materialize_resumed_session(runtime_root=td,contract=contract,lease_receipt=lease);req(mat["status"]=="resumed_session_materialized_not_executing");req(mat["work_execution_eligible"]);req(not mat["work_executed"]);req(not mat["authority_granted"])
 restart=reconcile_materialized_session(runtime_root=td,campaign_id="c1",expected_session_digest=mat["resumed_session_digest"],expected_lease_digest=lease["lease_digest"]);req(restart["status"]=="restored_execution_eligible_not_executing")
 req(reconcile_materialized_session(runtime_root=td,campaign_id="c1",expected_session_digest=h("wrong"),expected_lease_digest=lease["lease_digest"])["status"]=="blocked")
 tam=dict(contract);tam["session_id"]="x";req(acquire_resume_lease(runtime_root=Path(td)/"tam",contract=tam,lease_owner_digest=h("o"))["status"]=="blocked")
 req(create_resume_materialization_contract(reconciliation=recon,eligibility_review=er,session_id="../bad",session_generation=2,operator_materialization_digest=h("m"))["status"]=="blocked")
 req(create_resume_materialization_contract(reconciliation=recon,eligibility_review=er,session_id="s2",session_generation=0,operator_materialization_digest=h("m"))["status"]=="blocked")
 req(create_resume_materialization_contract(reconciliation=recon,eligibility_review=er,session_id="s2",session_generation=2,operator_materialization_digest=h("m"),lease_ttl_seconds=1)["status"]=="blocked")
 bad_er=dict(er);bad_er["status"]="rejected";req(create_resume_materialization_contract(reconciliation=recon,eligibility_review=bad_er,session_id="s2",session_generation=2,operator_materialization_digest=h("m"))["status"]=="blocked")
 rel=release_resume_lease(runtime_root=td,campaign_id="c1",expected_lease_digest=lease["lease_digest"],operator_release_digest=h("release"));req(rel["status"]=="lease_released")
 req(materialize_resumed_session(runtime_root=td,contract=contract,lease_receipt=lease)["status"]=="blocked")
with tempfile.TemporaryDirectory() as td:
 recon,er=fixtures(td);c=create_resume_materialization_contract(reconciliation=recon,eligibility_review=er,session_id="s2",session_generation=2,operator_materialization_digest=h("m"),lease_ttl_seconds=30);l1=acquire_resume_lease(runtime_root=td,contract=c,lease_owner_digest=h("o1"),now_epoch=1000);req(l1["status"]=="lease_acquired");req(acquire_resume_lease(runtime_root=td,contract=c,lease_owner_digest=h("o2"),now_epoch=1031)["status"]=="blocked");req(acquire_resume_lease(runtime_root=td,contract=c,lease_owner_digest=h("o2"),now_epoch=1031,stale_takeover_digest=h("takeover"))["status"]=="lease_acquired")
with tempfile.TemporaryDirectory() as td:
 cp=build_persistent_campaign_resume_materialization_checkpoint(source_root=ROOT,runtime_root=td);req(cp["ok"]);req(cp["passed"]==cp["total"]);req(not cp["work_executed"]);req(not cp["authority_granted"])
print(json.dumps({"ok":all(checks),"passed":sum(checks),"total":len(checks),"contract_version":"v1186.8"},sort_keys=True))
