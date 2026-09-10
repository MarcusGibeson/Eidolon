from __future__ import annotations
import hashlib,json,os,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));sys.dont_write_bytecode=True
os.environ["EIDOLON_DATA_DIR"]=tempfile.mkdtemp(prefix="eidolon-v2501-8-")
from conscious_agent.bounded_autonomous_web_research import BoundedResearchSessionStore
from conscious_agent.research_web_intelligence_v2100 import NATIVE_RECEIPT_CONTRACT_VERSION
checks=[]
def req(v,n):checks.append(n);assert v,n
def digest(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),default=str).encode()).hexdigest()
class Adapter:
 def __init__(self):self.search_calls=0;self.observe_calls=0;self.queries=[]
 def describe(self):return {"adapter_code":"v2501.8-fixture","read_only":True,"allowed_methods":["GET","HEAD"],"search_supported":True,"private_network_allowed":False,"redirect_revalidation_required":True,"credentials_allowed":False,"cookies_allowed":False,"uploads_allowed":False,"side_effects_allowed":False,"max_bytes_enforced":True,"timeout_enforced":True}
 def search(self,query,*,limit,timeout_seconds):
  self.search_calls+=1;self.queries.append(query)
  return [{"url":"https://official.gov/report?tracking=gone","source_kind":"primary_official","fetched_at":"2026-08-26T00:00:00+00:00"},{"url":"https://analysis.example/report","source_kind":"reputable_secondary","fetched_at":"2026-08-26T00:00:00+00:00"}][:limit]
 def observe(self,candidate,*,plan,max_bytes,timeout_seconds):
  self.observe_calls+=1;stance="supports" if self.observe_calls==1 else "refutes";cid=f"c{self.observe_calls}"
  r={"contract_version":NATIVE_RECEIPT_CONTRACT_VERSION,"receipt_kind":"source_observation","authoritative":True,"terminal":True,"operation_digest":"8"*64,"terminal_result_digest":"9"*64,"source_observed":True,"plan_digest":plan["plan_digest"],"source_candidate_digest":candidate["source_candidate_digest"],"claim_code":candidate.get("subquestion_id","rq1"),"stance":stance,"evidence_digest":hashlib.sha256(cid.encode()).hexdigest(),"citation_id":cid,"source_kind":candidate["source_kind"],"quality_score":candidate["quality_score"],"freshness_known":True,"fresh_enough":True,"relevance_score":.9,"observed_bytes":min(256,max_bytes)};r["receipt_digest"]=digest(r);return r
store=BoundedResearchSessionStore(Path(os.environ["EIDOLON_DATA_DIR"]));adapter=Adapter()
objective="Compare my wife Melissa's private browser notes with current public browser security evidence"
created=store.create_session("create",objective=objective,budget={"max_queries":2,"max_candidates":4,"max_observed_pages":2,"max_total_bytes":2048,"max_elapsed_seconds":30});session=created["result"]
req(created["ok"] and session["progress_stage"]=="awaiting_session_authorization","session_starts_with_visible_progress_state")
req(objective not in json.dumps(created) and session["query_text_exposed"] is False,"private_objective_and_queries_absent_from_public_session")
auth=store.authorize_session("auth",session_id=session["session_id"],session_digest=session["session_digest"],public_query_confirmed=True)
run=store.execute_session("execute",session_id=session["session_id"],authorization_digest=auth["result"]["authorization_digest"],adapter=adapter)
req(run["ok"] and run["result"]["session"]["progress_stage"]=="completed" and run["result"]["session"]["progress_percent"]==100,"integrated_workflow_reaches_completion")
req(adapter.search_calls==1 and adapter.observe_calls==2,"bounded_search_and_observation_counts_respected")
req(all("melissa" not in q.casefold() and "wife" not in q.casefold() and "private" not in q.casefold() for q in adapter.queries),"private_context_never_enters_public_search")
report=run["result"]["report"]
req(report["unresolved_disagreements"] and report["contradicted_claim_codes"]==["rq1"],"cross_source_conflict_reaches_operator_report")
req(report["raw_page_content_persisted"] is False and report["raw_query_text_exposed"] is False and report["private_objective_exposed"] is False,"report_privacy_boundary_visible")
serialized_report=json.dumps(report,sort_keys=True)
req(all(query not in serialized_report for query in adapter.queries),"exact_public_query_text_absent_from_report")
replay_calls=(adapter.search_calls,adapter.observe_calls);replay=store.execute_session("execute",session_id=session["session_id"],authorization_digest=auth["result"]["authorization_digest"],adapter=adapter)
req(replay["idempotent"] and replay_calls==(adapter.search_calls,adapter.observe_calls),"completed_execution_replay_is_exactly_once")
inspect=store.inspection_summary();pub=inspect["sessions"][0]
req(pub["budget_remaining"]["observed_pages"]==0 and inspect["query_text_exposed"] is False,"budget_and_progress_visible_without_query_text")
# Simulate a process dying after the durable running transition. A restart must
# fail closed rather than reissue any public request whose outcome is unknown.
created2=store.create_session("create2",objective="Research separate public browser reliability evidence");s2=created2["result"];a2=store.authorize_session("auth2",session_id=s2["session_id"],session_digest=s2["session_digest"],public_query_confirmed=True)
state=json.loads(store.path.read_text());row=next(x for x in state["sessions"] if x["session_id"]==s2["session_id"]);row["state"]="running";row["progress_stage"]="searching";store.path.write_text(json.dumps(state,indent=2,sort_keys=True)+"\n")
fresh_adapter=Adapter();interrupted=BoundedResearchSessionStore(Path(os.environ["EIDOLON_DATA_DIR"])).execute_session("resume-after-crash",session_id=s2["session_id"],authorization_digest=a2["result"]["authorization_digest"],adapter=fresh_adapter)
req(not interrupted["ok"] and interrupted["status"]=="bounded_research_interrupted_failed_closed","interrupted_session_recovers_fail_closed")
req(fresh_adapter.search_calls==0 and fresh_adapter.observe_calls==0,"interrupted_external_operation_never_replayed")
req(all(not interrupted.get(k) for k in ("posting_allowed","messaging_allowed","account_creation_allowed","purchase_allowed","upload_allowed","private_network_allowed","authority_expanded")),"authority_remains_read_only_and_session_bounded")
print(json.dumps({"suite":"v2501.8-research-session-integration-ux","ok":True,"passed":len(checks),"failed":0,"checks":checks,"native_network_contacted":False},sort_keys=True))
