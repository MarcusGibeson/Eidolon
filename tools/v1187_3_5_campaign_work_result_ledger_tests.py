#!/usr/bin/env python3
import hashlib,json
from pathlib import Path
from conscious_agent.campaign_work_result_ledger import *
from conscious_agent.campaign_work_result_ledger_checkpoint import build_campaign_work_result_ledger_checkpoint
ROOT=Path(__file__).resolve().parents[1];checks=[]
def req(v,m=""):checks.append(bool(v));assert v,m
def h(s):return hashlib.sha256(s.encode()).hexdigest()
def signed(row,field):
 out=dict(row);out.pop(field,None);out[field]=hashlib.sha256(json.dumps(out,sort_keys=True,separators=(",",":"),ensure_ascii=True,default=str).encode()).hexdigest();return out
ledger=signed({"campaign_id":"c1","work_item_ids":["w1"],"status":"approved_bounded_ledger","content_free":True},"ledger_digest")
budget=signed({"campaign_id":"c1","observed":{"work_items":0,"elapsed_seconds":10,"disk_bytes":0,"token_budget":0},"limits":{"max_work_items":2,"max_elapsed_seconds":100,"max_disk_bytes":1000,"max_token_budget":100},"status":"within_budget","content_free":True},"budget_receipt_digest")
for result,state in (("passed","completed"),("failed","failed")):
 e=signed({"campaign_id":"c1","session_id":"s1","work_item_id":"w1","status":"executed","result_code":result,"work_executed":True,"content_free":True},"work_execution_receipt_digest")
 r=create_work_result_review(execution_receipt=e,decision="accept",operator_decision_digest=h(result));req(r["status"]=="accepted_for_ledger")
 u=create_ledger_update_receipt(ledger=ledger,budget_receipt=budget,execution_receipt=e,result_review=r,observed_cost={"work_items":1,"elapsed_seconds":5,"disk_bytes":0,"token_budget":2});req(u["status"]=="ledger_update_recorded");req(u["new_work_item_state"]==state);req(u["updated_consumption"]["work_items"]==1);req(not u["work_retried"]);req(not u["automatic_reselection"]);req(not u["authority_granted"]);req(work_result_ledger_public_summary(r,u)["content_free"])
e=signed({"campaign_id":"c1","session_id":"s1","work_item_id":"w1","status":"executed","result_code":"passed","work_executed":True,"content_free":True},"work_execution_receipt_digest")
for d,s in (("reject","rejected_result"),("defer","deferred_result")):req(create_work_result_review(execution_receipt=e,decision=d,operator_decision_digest=h(d))["status"]==s)
r=create_work_result_review(execution_receipt=e,decision="accept",operator_decision_digest=h("a"))
for kwargs in [
 {"ledger":dict(ledger,work_item_ids=["w2"]),"budget_receipt":budget,"execution_receipt":e,"result_review":r,"observed_cost":{"work_items":1}},
 {"ledger":ledger,"budget_receipt":budget,"execution_receipt":e,"result_review":r,"observed_cost":{"work_items":2}},
 {"ledger":ledger,"budget_receipt":budget,"execution_receipt":e,"result_review":r,"observed_cost":{"work_items":1,"elapsed_seconds":1000}},
]:req(create_ledger_update_receipt(**kwargs)["status"]=="blocked")
t=dict(e);t["result_code"]="failed";req(create_work_result_review(execution_receipt=t,decision="accept",operator_decision_digest=h("x"))["status"]=="blocked")
cp=build_campaign_work_result_ledger_checkpoint(source_root=ROOT);req(cp["ok"]);req(cp["passed"]==cp["total"]);req(not cp["authority_granted"])
print(json.dumps({"ok":all(checks),"passed":sum(checks),"total":len(checks),"contract_version":"v1187.5"},sort_keys=True))
