from __future__ import annotations
import json,os,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.dont_write_bytecode=True;os.environ['PYTHONDONTWRITEBYTECODE']='1'
for p in (ROOT,ROOT/'conscious_agent',ROOT/'tools'):
    if str(p) not in sys.path:sys.path.insert(0,str(p))
from v1271_fixture import prepared_long_chain
from v1270_fixture import initial_provider,repair_provider
from long_running_work_sessions import *
from long_running_work_sessions_foundations import *
from isolated_self_modification_foundations import source_only_manifest
C=[]
def req(v,l):
    if not v:raise AssertionError(l)
    C.append(l)
with tempfile.TemporaryDirectory(prefix='eidolon-v1271-int-') as td:
    c=prepared_long_chain(Path(td));sid=c['session']['session_id'];calls=[];repairs=[]
    wrong=execute_long_running_candidate(sid,c['source'],runtime_root=c['runtime'],authorization_phrase='go ahead',provider=initial_provider(calls));req(wrong['status']=='isolated_self_modification_exact_authorization_required','generic_candidate_auth_blocked');req(len(calls)==0,'provider_not_called_wrong_auth')
    status=long_running_operator_status(sid,runtime_root=c['runtime']);req(status['work_attempted_not_completed']==['candidate_stage'],'attempt_visible');req(status['next_required_authorization']=='v1265_exact_candidate_authorization','candidate_auth_still_required')
    paused=pause_long_running_work_session(sid,runtime_root=c['runtime']);req(paused['state']=='paused','pause_recorded')
    try:execute_long_running_candidate(sid,c['source'],runtime_root=c['runtime'],authorization_phrase=c['campaign']['candidate_authorization_phrase'],provider=initial_provider(calls));raise AssertionError('paused_execution_not_blocked')
    except RuntimeError:C.append('paused_execution_blocked')
    resumed=resume_long_running_work_session(sid,runtime_root=c['runtime']);req(resumed['state']=='active','resume_recorded');req(resumed['underlying_authorization_reused'] is False,'resume_no_authority_reuse')
    stage=execute_long_running_candidate(sid,c['source'],runtime_root=c['runtime'],authorization_phrase=c['campaign']['candidate_authorization_phrase'],provider=initial_provider(calls));req(stage['phase']=='repair_authorization_required','candidate_completed');req(len(calls)==1,'one_provider_call')
    replay=execute_long_running_candidate(sid,c['source'],runtime_root=c['runtime'],authorization_phrase=c['campaign']['candidate_authorization_phrase'],provider=initial_provider(calls));req(replay['long_session_duplicate_suppressed'] is True,'candidate_resume_duplicate_suppressed');req(len(calls)==1,'no_duplicate_provider')
    over=build_verification_harness_budget(['a','b','c','d'],phase_budget_seconds=90,estimated_seconds_per_test=30);blocked=execute_long_running_verification_and_review(sid,c['source'],runtime_root=c['runtime'],repair_authorization_phrase=stage['repair_authorization_phrase'],repair_provider=repair_provider(repairs),budget=over);req(blocked['status']=='verification_harness_budget_split_required','monolithic_budget_blocked');req(len(repairs)==0,'budget_block_no_repair_provider')
    budget=build_verification_harness_budget(['selected_suite'],phase_budget_seconds=900,estimated_seconds_per_test=30);final=execute_long_running_verification_and_review(sid,c['source'],runtime_root=c['runtime'],repair_authorization_phrase=stage['repair_authorization_phrase'],repair_provider=repair_provider(repairs),budget=budget);req(final['phase']=='operator_review_required','verification_review_ready');req(len(repairs)==1,'one_repair_provider_call')
    replay2=execute_long_running_verification_and_review(sid,c['source'],runtime_root=c['runtime'],repair_authorization_phrase=stage['repair_authorization_phrase'],repair_provider=repair_provider(repairs),budget=budget);req(replay2['long_session_duplicate_suppressed'] is True,'verification_resume_duplicate_suppressed');req(len(repairs)==1,'no_duplicate_repair_provider')
    status=long_running_operator_status(sid,runtime_root=c['runtime']);req(status['current_phase']=='operator_review_required','operator_phase_visible');req(status['next_required_authorization']=='operator_review_disposition','operator_next_action_visible');req('candidate_stage' in status['work_completed'] and 'verification_stage' in status['work_completed'],'completed_stages_visible');req(source_only_manifest(c['source'])['source_manifest_digest']==c['before'],'active_source_unchanged')
print(json.dumps({'ok':True,'suite':'v1271.3-v1271.5-long-running-work-sessions-integration','passed':len(C),'failed':0,'checks':C},sort_keys=True))
