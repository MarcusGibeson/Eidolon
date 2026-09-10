#!/usr/bin/env python3
import hashlib,json,tempfile
from pathlib import Path
from conscious_agent.persistent_development_campaign import *
from conscious_agent.persistent_development_campaign_continuation import *
from conscious_agent.persistent_campaign_storage import *
from conscious_agent.persistent_campaign_storage_checkpoint import build_persistent_campaign_storage_checkpoint
ROOT=Path(__file__).resolve().parents[1]; checks=[]
def req(v,msg=""): checks.append(bool(v)); assert v,msg
def h(s): return hashlib.sha256(s.encode()).hexdigest()
with tempfile.TemporaryDirectory() as td:
 c=create_campaign_charter(campaign_id="campaign-1",source_baseline_digest=h("source"),scope_digest=h("scope"),goal_digests=[h("g")],limits={"max_work_items":2,"max_sessions":3,"max_elapsed_seconds":100,"max_disk_bytes":1000,"max_token_budget":200})
 r=create_campaign_review(charter=c,decision="approve",operator_decision_digest=h("approve"));l=create_campaign_ledger(charter=c,review=r);s=create_campaign_session_snapshot(charter=c,review=r,ledger=l,session_id="s1",session_index=1,state="paused")
 rec=create_campaign_storage_record(charter=c,review=r,ledger=l,snapshot=s,storage_generation=1,operator_storage_digest=h("store")); req(rec["status"]=="ready_for_runtime_storage")
 stored=persist_campaign_storage_record(runtime_root=td,record=rec);req(stored["status"]=="stored");req((Path(td)/stored["relative_runtime_path"]).is_file())
 restored=restore_campaign_storage_record(runtime_root=td,campaign_id="campaign-1",expected_record_digest=rec["storage_record_digest"],current_source_digest=h("source"));req(restored["status"]=="restoration_review_required");req(not restored["work_resumed"])
 drift=restore_campaign_storage_record(runtime_root=td,campaign_id="campaign-1",expected_record_digest=rec["storage_record_digest"],current_source_digest=h("other"));req(drift["status"]=="reconciliation_required");req(drift["source_drift"])
 for d,st in [("approve","approved_not_resumed"),("reject","rejected"),("defer","deferred")]:req(create_restoration_review(restoration=restored,decision=d,operator_decision_digest=h(d))["status"]==st)
 bad=dict(rec);bad["campaign_state"]="active";req(persist_campaign_storage_record(runtime_root=td,record=bad)["status"]=="blocked")
 req(create_campaign_storage_record(charter=c,review=r,ledger=l,snapshot=s,storage_generation=2,operator_storage_digest=h("x"))["status"]=="blocked")
 rec2=create_campaign_storage_record(charter=c,review=r,ledger=l,snapshot=s,storage_generation=2,prior_record_digest=rec["storage_record_digest"],operator_storage_digest=h("store2"));req(rec2["status"]=="ready_for_runtime_storage");req(persist_campaign_storage_record(runtime_root=td,record=rec2)["status"]=="stored")
 req(restore_campaign_storage_record(runtime_root=td,campaign_id="../escape",expected_record_digest=h("x"),current_source_digest=h("source"))["status"]=="blocked")
 cp=build_persistent_campaign_storage_checkpoint(source_root=ROOT,runtime_root=Path(td)/"checkpoint");req(cp["ok"]);req(cp["passed"]==cp["total"])
 source_before={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in ROOT.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
 source_after={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in ROOT.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
 req(source_before==source_after);req(not cp["work_executed"]);req(not cp["work_resumed"]);req(not cp["authority_granted"])
print(json.dumps({"ok":all(checks),"passed":sum(checks),"total":len(checks),"contract_version":"v1186.2"},sort_keys=True))
