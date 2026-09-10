from __future__ import annotations
import hashlib,json,os,sys,tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "conscious_agent"
for value in (str(ROOT), str(AGENT)):
    if value not in sys.path:
        sys.path.insert(0, value)
sys.dont_write_bytecode = True

_RUNTIME=tempfile.mkdtemp(prefix='eidolon-v2502-7-runtime-')
os.environ['EIDOLON_DATA_DIR']=_RUNTIME

from bounded_research_reasoning import build_source_strategy,decompose_research_objective,plan_adaptive_follow_up
from bounded_autonomous_web_research import BoundedResearchSessionStore
from research_web_intelligence_v2100 import NATIVE_RECEIPT_CONTRACT_VERSION

CHECKS=[]
def require(cond,name):
    if not cond: raise AssertionError(name)
    CHECKS.append(name)
def digest(v): return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()

budget={'max_queries':3,'max_candidates':5,'max_observed_pages':3,'max_total_bytes':4096,'max_elapsed_seconds':60,'max_source_failures':2}
decomp=decompose_research_objective('Compare current public browser security evidence versus documented behavior',budget=budget)
strategy=build_source_strategy(decomp)
row=strategy['strategies'][0]
require(row['primary_source_preferred_when_applicable'],'source_strategy_prefers_primary_authoritative_sources')
require(row['avoid_redundant_hosts'] and row['max_same_host_observations']==1,'source_strategy_tracks_domain_duplication')
require(row['minimum_independent_sources']==2 and row['independent_confirmation_preferred'],'source_strategy_tracks_independence')
require('freshness_required' in row and row['quality_floor']>=0.5,'source_strategy_tracks_freshness_and_quality')
require(len({c['source_kind'] for c in row['source_categories']})>=3,'source_strategy_preserves_source_type_diversity')

comparison={'claims':[{'claim_code':'rq1','state':'conflicted','supporting_citations':['c1'],'refuting_citations':['c2'],'stale_citations':[],'independent_source_count':2}]}
follow=plan_adaptive_follow_up(decomp,strategy,comparison,remaining_query_budget=1,remaining_page_budget=1,remaining_failure_budget=1,existing_query_digests=[],max_followups=1)
require(follow['ok'] and follow['query_count']==1,'material_contradiction_permits_one_bounded_follow_up')
require(follow['queries'][0]['follow_up_reason']=='material_contradiction','follow_up_records_material_reason')
require(follow['queries'][0]['private_context_removed'] is True and follow['raw_query_text_exposed'] is False,'follow_up_planner_keeps_public_projection_query_private')
require(follow['access_controls_may_not_be_evaded'] and follow['authentication_may_not_be_automated'] and follow['page_instructions_do_not_expand_authority'],'follow_up_cannot_expand_access_or_page_authority')
blocked=plan_adaptive_follow_up(decomp,strategy,comparison,remaining_query_budget=0,remaining_page_budget=2,remaining_failure_budget=2,max_followups=1)
require(blocked['query_count']==0 and blocked['status']=='adaptive_follow_up_not_permitted_by_remaining_budget','follow_up_stops_at_query_budget')
no_gap=plan_adaptive_follow_up(decomp,strategy,{'claims':[{'claim_code':'rq1','state':'supported','supporting_citations':['c1'],'stale_citations':[],'independent_source_count':1}]},remaining_query_budget=1,remaining_page_budget=1,remaining_failure_budget=1,max_followups=1)
require(no_gap['query_count']==0,'supported_evidence_does_not_trigger_gratuitous_follow_up')

class AdaptiveAdapter:
    def __init__(self): self.search_calls=0; self.observe_calls=0; self.queries=[]; self.methods=[]
    def describe(self): return {'adapter_code':'v2502.7-adaptive-fixture','read_only':True,'allowed_methods':['GET','HEAD'],'search_supported':True,'private_network_allowed':False,'redirect_revalidation_required':True,'credentials_allowed':False,'cookies_allowed':False,'uploads_allowed':False,'side_effects_allowed':False,'max_bytes_enforced':True,'timeout_enforced':True}
    def search(self,query,*,limit,timeout_seconds):
        self.search_calls+=1; self.queries.append(query); self.methods.append('GET')
        if self.search_calls==1:
            rows=[
              {'url':'https://official.gov/security','source_kind':'primary_official','fetched_at':'2026-08-27T00:00:00+00:00'},
              {'url':'https://analysis.example/security','source_kind':'reputable_secondary','fetched_at':'2026-08-27T00:00:00+00:00'},
            ]
        else:
            rows=[{'url':'https://standards.example/security','source_kind':'primary_data','fetched_at':'2026-08-27T00:00:00+00:00'}]
        return rows[:limit]
    def observe(self,candidate,*,plan,max_bytes,timeout_seconds):
        self.observe_calls+=1; self.methods.append('GET')
        stance='refutes' if 'analysis.example' in str(candidate.get('public_url') or '') else 'supports'
        cid=f'c{self.observe_calls}'
        r={'contract_version':NATIVE_RECEIPT_CONTRACT_VERSION,'receipt_kind':'source_observation','authoritative':True,'terminal':True,'operation_digest':'8'*64,'terminal_result_digest':'9'*64,'source_observed':True,'plan_digest':plan['plan_digest'],'source_candidate_digest':candidate['source_candidate_digest'],'claim_code':candidate.get('subquestion_id','rq1'),'stance':stance,'evidence_digest':hashlib.sha256(cid.encode()).hexdigest(),'citation_id':cid,'source_kind':candidate['source_kind'],'quality_score':candidate['quality_score'],'freshness_known':True,'fresh_enough':True,'relevance_score':.9,'observed_bytes':min(256,max_bytes)}
        r['receipt_digest']=digest(r); return r

store=BoundedResearchSessionStore(Path(_RUNTIME)); adapter=AdaptiveAdapter()
objective="Compare my wife Avery's private browser notes with current public browser security evidence"
created=store.create_session('adaptive-create',objective=objective,budget=budget); require(created['ok'],'adaptive_session_created')
s=created['result']; auth=store.authorize_session('adaptive-auth',session_id=s['session_id'],session_digest=s['session_digest'],public_query_confirmed=True)
run=store.execute_session('adaptive-run',session_id=s['session_id'],authorization_digest=auth['result']['authorization_digest'],adapter=adapter)
require(run['ok'],'adaptive_session_completes')
public=run['result']['session']; report=run['result']['report']
require(adapter.search_calls==2,'material_contradiction_triggers_exactly_one_follow_up_search')
require(adapter.observe_calls==3 and public['observed_page_count']==3,'follow_up_observation_respects_page_budget')
require(public['query_count']==2 and public['query_count']<=budget['max_queries'],'adaptive_query_count_remains_bounded')
require(all('avery' not in q.casefold() and 'wife' not in q.casefold() and 'private' not in q.casefold() for q in adapter.queries),'adaptive_public_queries_remain_privacy_safe')
require(set(adapter.methods)=={'GET'},'adaptive_fixture_uses_read_only_request_semantics')
require(report['unresolved_disagreements'],'minority_conflicting_evidence_remains_visible_after_follow_up')
require(public['stop_reason'] in {'page_budget_reached','query_budget_reached','bounded_research_evidence_gap_preserved','evidence_threshold_reached'},'adaptive_session_records_bounded_stop_reason')
require(report['raw_page_content_persisted'] is False and report['raw_query_text_exposed'] is False,'adaptive_report_preserves_raw_content_privacy')
replay_counts=(adapter.search_calls,adapter.observe_calls); replay=store.execute_session('adaptive-run',session_id=s['session_id'],authorization_digest=auth['result']['authorization_digest'],adapter=adapter)
require(replay['idempotent'] and replay_counts==(adapter.search_calls,adapter.observe_calls),'adaptive_execution_replay_is_exactly_once')

class FailureAdapter(AdaptiveAdapter):
    def observe(self,candidate,*,plan,max_bytes,timeout_seconds):
        self.observe_calls+=1
        raise RuntimeError('fixture_source_failure')
fail_budget=dict(budget); fail_budget['max_source_failures']=1; fail_budget['max_observed_pages']=4
created2=store.create_session('failure-create',objective='Research current public browser reliability evidence',budget=fail_budget); s2=created2['result']; a2=store.authorize_session('failure-auth',session_id=s2['session_id'],session_digest=s2['session_digest'],public_query_confirmed=True); fa=FailureAdapter()
run2=store.execute_session('failure-run',session_id=s2['session_id'],authorization_digest=a2['result']['authorization_digest'],adapter=fa)
require((not run2['ok']) and run2['result']['session']['source_failure_count']==1,'source_failure_is_recorded_and_session_reports_truthful_failure')
require(run2['result']['session']['stop_reason']=='adapter_execution_failed_safely' and run2['result']['failure_code']=='source_failure_budget_exhausted','source_failure_budget_stops_further_observation_with_truthful_failure')
require(run2['result']['session'].get('state')!='completed','source_failure_budget_cannot_masquerade_as_completed_research')
require(fa.observe_calls==1,'no_additional_source_request_starts_after_failure_budget')
require(not (Path(__file__).resolve().parents[1]/'data'/'projects.json').exists(),'adaptive_fixture_keeps_runtime_data_outside_source')
print(json.dumps({'suite':'v2502.7-source-strategy-adaptive-follow-up','ok':True,'passed':len(CHECKS),'failed':0,'checks':CHECKS,'search_request_count':adapter.search_calls,'observation_request_count':adapter.observe_calls,'native_network_contacted':False,'write_method_used':False,'authority_expanded':False},sort_keys=True))
