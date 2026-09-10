from __future__ import annotations
import json, os, sys, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.dont_write_bytecode=True;os.environ['PYTHONDONTWRITEBYTECODE']='1'
for p in (ROOT,ROOT/'conscious_agent',ROOT/'tools'):
    if str(p) not in sys.path:sys.path.insert(0,str(p))
from v1273_fixture import prepared_ownership_chain
from v1270_fixture import initial_provider, repair_provider
from self_development_alpha_foundations import load_self_development_alpha_campaign
from long_running_work_sessions_foundations import build_verification_harness_budget
from ownership_concurrency_foundations import *
from ownership_concurrency import *
C=[]
def req(v,l):
    if not v: raise AssertionError(l)
    C.append(l)

with tempfile.TemporaryDirectory(prefix='eidolon-v1273-int-') as td:
    base=Path(td);c=prepared_ownership_chain(base/'normal',now=1000.0);oid=c['ownership']['ownership_id'];pcalls=[];rcalls=[]
    wrong=execute_owned_candidate(oid,c['source'],runtime_root=c['runtime'],owner_id='process-a',authorization_phrase='go ahead',provider=initial_provider(pcalls),now=1010.0,completion_now=1011.0)
    req(len(pcalls)==0,'generic_auth_no_provider')
    req(wrong['ownership_execution_completed'] is False,'auth_failure_not_completed')
    alpha=load_self_development_alpha_campaign(c['campaign']['campaign_id'],runtime_root=c['runtime'])
    good=execute_owned_candidate(oid,c['source'],runtime_root=c['runtime'],owner_id='process-a',authorization_phrase=alpha['candidate_authorization_phrase'],provider=initial_provider(pcalls),now=1020.0,completion_now=1021.0)
    req(len(pcalls)==1,'candidate_provider_once')
    req(good['ownership_execution_completed'] is True,'candidate_owned_completion')
    dup=execute_owned_candidate(oid,c['source'],runtime_root=c['runtime'],owner_id='tab-b',authorization_phrase=alpha['candidate_authorization_phrase'],provider=initial_provider(pcalls),claimant_kind='browser_tab',now=1022.0)
    req(dup['duplicate_external_activity_suppressed'] is True,'candidate_tab_duplicate_suppressed')
    req(len(pcalls)==1,'candidate_provider_still_once')
    alpha=load_self_development_alpha_campaign(c['campaign']['campaign_id'],runtime_root=c['runtime'])
    budget=build_verification_harness_budget(['selected_suite'],phase_budget_seconds=900,estimated_seconds_per_test=30)
    ver=execute_owned_verification_and_review(oid,c['source'],runtime_root=c['runtime'],owner_id='queue-a',repair_authorization_phrase=alpha['repair_authorization_phrase'],repair_provider=repair_provider(rcalls),budget=budget,claimant_kind='queue_worker',now=1030.0,completion_now=1031.0)
    req(len(rcalls)==1,'verification_provider_once')
    req(ver['ownership_execution_completed'] is True,'verification_owned_completion')
    verdup=execute_owned_verification_and_review(oid,c['source'],runtime_root=c['runtime'],owner_id='retry-b',repair_authorization_phrase='anything',repair_provider=repair_provider(rcalls),budget=budget,claimant_kind='retry_worker',now=1032.0)
    req(verdup['duplicate_external_activity_suppressed'] is True,'verification_retry_suppressed')
    req(len(rcalls)==1,'verification_provider_still_once')

    # Expired owner before any v1272 stage entry: successor reconciles and may
    # enter the stage, but exact v1265 authorization is still independently checked.
    c2=prepared_ownership_chain(base/'expired-clean',now=2000.0);oid2=c2['ownership']['ownership_id'];target2=c2['campaign']['candidate_operation_id'];calls2=[]
    first=acquire_operation_ownership(oid2,runtime_root=c2['runtime'],operation_code='candidate_stage',target_id=target2,owner_id='dead-process',lease_seconds=10,now=2001.0)
    req(first['execution_allowed'] is True,'dead_owner_initial_claim')
    transferred=execute_owned_candidate(oid2,c2['source'],runtime_root=c2['runtime'],owner_id='replacement',authorization_phrase='go ahead',provider=initial_provider(calls2),lease_seconds=10,now=2020.0,completion_now=2021.0)
    req(len(calls2)==0,'transferred_still_requires_exact_auth')
    req(transferred['ownership_execution_completed'] is False,'transferred_wrong_auth_not_completed')

    # Crash after durable v1265/v1272 stage result but before v1273 ownership completion.
    c3=prepared_ownership_chain(base/'late',now=3000.0);oid3=c3['ownership']['ownership_id'];calls3=[]
    alpha3=load_self_development_alpha_campaign(c3['campaign']['campaign_id'],runtime_root=c3['runtime'])
    late=execute_owned_candidate(oid3,c3['source'],runtime_root=c3['runtime'],owner_id='slow-owner',authorization_phrase=alpha3['candidate_authorization_phrase'],provider=initial_provider(calls3),lease_seconds=10,now=3001.0,completion_now=3020.0)
    req(len(calls3)==1,'slow_owner_provider_once')
    req(late['late_result_fenced'] is True,'expired_slow_result_fenced')
    req(late['durable_v1272_result_retained_for_successor_reconciliation'] is True,'durable_v1272_result_retained')
    successor=execute_owned_candidate(oid3,c3['source'],runtime_root=c3['runtime'],owner_id='successor',authorization_phrase='not_reused',provider=initial_provider(calls3),lease_seconds=10,now=3021.0)
    req(successor['duplicate_external_activity_suppressed'] is True,'successor_reconciles_completed_stage')
    req(len(calls3)==1,'successor_does_not_replay_provider')
    status=ownership_concurrency_operator_status(oid3,runtime_root=c3['runtime'],now=3022.0)
    req(status['completed_claim_count']==1,'operator_sees_completed_claim')
    req(status['automatic_execution_after_transfer'] is False,'operator_transfer_not_auto_execute')
print(json.dumps({'ok':True,'suite':'v1273.3-v1273.5-ownership-concurrency-integration','passed':len(C),'failed':0,'checks':C},sort_keys=True))
