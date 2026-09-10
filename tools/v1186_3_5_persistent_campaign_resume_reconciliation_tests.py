#!/usr/bin/env python3
import hashlib,tempfile,json
from pathlib import Path
from conscious_agent.persistent_development_campaign import *
from conscious_agent.persistent_development_campaign_continuation import *
from conscious_agent.persistent_campaign_storage import *
from conscious_agent.persistent_campaign_resume_reconciliation import *
from conscious_agent.persistent_campaign_resume_reconciliation_checkpoint import build_persistent_campaign_resume_reconciliation_checkpoint
ROOT=Path(__file__).resolve().parents[1];checks=[]
def req(v,m=""):checks.append(bool(v));assert v,m
def h(s):return hashlib.sha256(s.encode()).hexdigest()
with tempfile.TemporaryDirectory() as td:
 c=create_campaign_charter(campaign_id="c1",source_baseline_digest=h("src"),scope_digest=h("scope"),goal_digests=[h("g")],limits={"max_work_items":2,"max_sessions":3,"max_elapsed_seconds":100,"max_disk_bytes":1000,"max_token_budget":200});r=create_campaign_review(charter=c,decision="approve",operator_decision_digest=h("a"));l=create_campaign_ledger(charter=c,review=r);s=create_campaign_session_snapshot(charter=c,review=r,ledger=l,session_id="s1",session_index=1,state="paused")
 sr=create_campaign_storage_record(charter=c,review=r,ledger=l,snapshot=s,operator_storage_digest=h("store"));req(persist_campaign_storage_record(runtime_root=td,record=sr)["status"]=="stored")
 rest=restore_campaign_storage_record(runtime_root=td,campaign_id="c1",expected_record_digest=sr["storage_record_digest"],current_source_digest=h("src"));rr=create_restoration_review(restoration=rest,decision="approve",operator_decision_digest=h("restore"));recon=create_resume_reconciliation(restoration=rest,restoration_review=rr,current_charter_digest=c["charter_digest"],current_review_digest=r["review_digest"],current_ledger_digest=l["ledger_digest"],current_snapshot_digest=s["snapshot_digest"]);req(recon["status"]=="resume_review_required")
 for d,st in [("approve","eligible_not_resumed"),("reject","rejected"),("defer","deferred")]:req(create_resume_eligibility_review(reconciliation=recon,decision=d,operator_decision_digest=h(d))["status"]==st)
 bad=dict(recon);bad["campaign_id"]="tamper";req(create_resume_eligibility_review(reconciliation=bad,decision="approve",operator_decision_digest=h("x"))["status"]=="blocked")
 drift=restore_campaign_storage_record(runtime_root=td,campaign_id="c1",expected_record_digest=sr["storage_record_digest"],current_source_digest=h("drift"));drr=create_restoration_review(restoration=drift,decision="approve",operator_decision_digest=h("d"));dr=create_resume_reconciliation(restoration=drift,restoration_review=drr,current_charter_digest=c["charter_digest"],current_review_digest=r["review_digest"],current_ledger_digest=l["ledger_digest"],current_snapshot_digest=s["snapshot_digest"]);req(dr["status"]=="operator_reconciliation_required");req(create_resume_eligibility_review(reconciliation=dr,decision="approve",operator_decision_digest=h("x"))["status"]=="blocked");req(create_resume_eligibility_review(reconciliation=dr,decision="approve",operator_decision_digest=h("x"),acknowledge_source_drift=True)["status"]=="eligible_not_resumed")
 req(create_resume_reconciliation(restoration=rest,restoration_review=rr,current_charter_digest="bad",current_review_digest=r["review_digest"],current_ledger_digest=l["ledger_digest"],current_snapshot_digest=s["snapshot_digest"])["status"]=="blocked")
 cp=build_persistent_campaign_resume_reconciliation_checkpoint(source_root=ROOT,runtime_root=Path(td)/"cp");req(cp["ok"]);req(cp["passed"]==cp["total"]);req(not cp["work_resumed"]);req(not cp["authority_granted"])
print(json.dumps({"ok":all(checks),"passed":sum(checks),"total":len(checks),"contract_version":"v1186.5"},sort_keys=True))
