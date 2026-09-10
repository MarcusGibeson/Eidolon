from __future__ import annotations
import json,os,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.dont_write_bytecode=True;os.environ['PYTHONDONTWRITEBYTECODE']='1'
for p in (ROOT,ROOT/'conscious_agent',ROOT/'tools'):
    if str(p) not in sys.path:sys.path.insert(0,str(p))
from v1271_fixture import prepared_long_chain
from long_running_work_sessions_foundations import *
C=[]
def req(v,l):
    if not v:raise AssertionError(l)
    C.append(l)
with tempfile.TemporaryDirectory(prefix='eidolon-v1271-found-') as td:
    c=prepared_long_chain(Path(td),now=1000.0);s=c['session'];sid=s['session_id']
    req(s['state']=='active','state_active');req(s['current_phase']=='prepared','phase_prepared');req(s['next_required_authorization']=='v1265_exact_candidate_authorization','next_auth_candidate');req(s['progress_is_durable'] is True,'durable_progress');req(s['summary_is_bounded'] is True,'bounded_summary_contract');req(s['attempted_distinct_from_completed'] is True,'attempt_completed_distinct')
    req(validate_long_running_work_session(s)['ok'],'session_valid');req(prepare_long_running_work_session(c['campaign']['campaign_id'],runtime_root=c['runtime'],now=1001.0)['operation_status']=='restored','deterministic_restore')
    a=record_progress_receipt(sid,runtime_root=c['runtime'],phase='candidate_execution',work_code='candidate_stage',outcome='attempted',elapsed_seconds=2.25,detail_codes=['authorization_required'],now=1002.0)
    req('candidate_stage' in a['attempted_work_codes'],'attempt_recorded');req('candidate_stage' not in a['completed_work_codes'],'attempt_not_completed');req(a['bounded_summaries'][-1]['content_free'],'summary_content_free')
    b=record_progress_receipt(sid,runtime_root=c['runtime'],phase='repair_authorization_required',work_code='candidate_stage',outcome='completed',elapsed_seconds=4.0,action_key='candidate_stage',now=1003.0)
    req('candidate_stage' in b['completed_work_codes'],'completed_recorded');req(b['action_receipts']['candidate_stage']==b['progress_receipts'][-1]['receipt_digest'],'action_receipt_bound')
    replay=record_progress_receipt(sid,runtime_root=c['runtime'],phase='repair_authorization_required',work_code='candidate_stage',outcome='completed',action_key='candidate_stage',now=1004.0);req(replay['operation_status']=='restored','duplicate_action_restored');req(replay['duplicate_action_suppressed'] is True,'duplicate_action_suppressed')
    for i in range(MAX_RECEIPTS+12):record_progress_receipt(sid,runtime_root=c['runtime'],phase='verification_and_repair',work_code=f'probe{i}',outcome='attempted',now=1100+i)
    bounded=load_long_running_work_session(sid,runtime_root=c['runtime']);req(len(bounded['progress_receipts'])==MAX_RECEIPTS,'receipt_ring_bounded');req(len(bounded['bounded_summaries'])==MAX_SUMMARIES,'summary_ring_bounded');req(bounded['receipt_count_total']>MAX_RECEIPTS,'total_count_preserved')
    plan=build_verification_harness_budget(['t1','t2','t3','t4'],phase_budget_seconds=90,estimated_seconds_per_test=30,max_chunk_tests=4);req(plan['split_required'],'budget_split_required');req(plan['global_timeout_increased'] is False,'no_global_timeout_increase');req(plan['chunk_count']==2,'budget_chunked')
    for k,v in AUTHORITY_FLAGS.items():req(s[k] is v,'authority_'+k)
print(json.dumps({'ok':True,'suite':'v1271.0-v1271.2-long-running-work-sessions-foundations','passed':len(C),'failed':0,'checks':C},sort_keys=True))
