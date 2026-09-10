from __future__ import annotations
import json,os,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.dont_write_bytecode=True;os.environ['PYTHONDONTWRITEBYTECODE']='1'
for p in (ROOT,ROOT/'conscious_agent',ROOT/'tools'):
    if str(p) not in sys.path:sys.path.insert(0,str(p))
from v1277_fixture import prepared_observability_chain
from v1270_fixture import initial_provider,repair_provider
from long_running_work_sessions_foundations import build_verification_harness_budget
from restart_crash_recovery import record_provider_outage,record_provider_return
from ownership_concurrency_foundations import acquire_operation_ownership
from development_observability_foundations import load_development_observability,validate_development_observability
from development_observability import *
C=[]
def req(v,l):
    if not v:raise AssertionError(l)
    C.append(l)
with tempfile.TemporaryDirectory() as td:
 c=prepared_observability_chain(Path(td),now=100);oid=c['observability']['observability_id'];calls=[];repairs=[]
 req(sync_development_observability(oid,runtime_root=c['runtime'],now=101)['operation_status']=='observability_synchronized','sync')
 w=execute_observed_candidate(oid,c['source'],runtime_root=c['runtime'],authorization_phrase='go ahead',provider=initial_provider(calls));req(w['status']=='isolated_self_modification_exact_authorization_required','wrong_auth');req(len(calls)==0,'no_provider_wrong');req(w['private_payloads_persisted'] is False,'no_payload_wrong')
 st=development_observability_operator_status(oid,runtime_root=c['runtime']);req(st['current_phase']=='prepared','still_prepared');req(st['next_required_authorization']=='v1265_exact_candidate_authorization','auth_visible')
 stage=execute_observed_candidate(oid,c['source'],runtime_root=c['runtime'],authorization_phrase=c['campaign']['candidate_authorization_phrase'],provider=initial_provider(calls));req(stage['phase']=='repair_authorization_required','candidate_done');req(len(calls)==1,'provider_once')
 replay=execute_observed_candidate(oid,c['source'],runtime_root=c['runtime'],authorization_phrase=c['campaign']['candidate_authorization_phrase'],provider=initial_provider(calls));req(replay['long_session_duplicate_suppressed'],'candidate_dedupe');req(len(calls)==1,'no_provider_dup')
 over=build_verification_harness_budget(['a','b','c','d'],phase_budget_seconds=90,estimated_seconds_per_test=30);b=execute_observed_verification_and_review(oid,c['source'],runtime_root=c['runtime'],repair_authorization_phrase=stage['repair_authorization_phrase'],repair_provider=repair_provider(repairs),budget=over);req(b['status']=='verification_harness_budget_split_required','split_block');req(len(repairs)==0,'no_repair_split')
 good=build_verification_harness_budget(['selected_suite'],phase_budget_seconds=900,estimated_seconds_per_test=30);f=execute_observed_verification_and_review(oid,c['source'],runtime_root=c['runtime'],repair_authorization_phrase=stage['repair_authorization_phrase'],repair_provider=repair_provider(repairs),budget=good);req(f['phase']=='operator_review_required','review_ready');req(len(repairs)==1,'repair_once')
 replay2=execute_observed_verification_and_review(oid,c['source'],runtime_root=c['runtime'],repair_authorization_phrase=stage['repair_authorization_phrase'],repair_provider=repair_provider(repairs),budget=good);req(replay2['long_session_duplicate_suppressed'],'verify_dedupe');req(len(repairs)==1,'no_repair_dup')
 record_provider_outage(c['recovery']['recovery_id'],runtime_root=c['runtime']);record_provider_return(c['recovery']['recovery_id'],runtime_root=c['runtime']);acquire_operation_ownership(c['ownership']['ownership_id'],runtime_root=c['runtime'],operation_code='governed_update',target_id='campaign',owner_id='worker-a',now=500)
 synced=sync_development_observability(oid,runtime_root=c['runtime'],now=501);req(validate_development_observability(synced)['ok'],'valid_synced');counts=synced['aggregate_event_counts'];req(counts.get('phase_completed',0)>=2,'completion_visible');req(counts.get('budget_split_required',0)>=1,'budget_visible');req(counts.get('provider_outage',0)>=1,'outage_visible');req(counts.get('provider_return',0)>=1,'return_visible');req(counts.get('ownership_observed',0)>=1,'ownership_visible');req(counts.get('environment_evidence_observed',0)>=1,'environment_visible')
 before=synced['event_count_total'];req(sync_development_observability(oid,runtime_root=c['runtime'],now=502)['event_count_total']==before,'sync_idempotent');status=development_observability_operator_status(oid,runtime_root=c['runtime']);req(status['current_phase']=='operator_review_required','phase_status');req(status['next_required_authorization']=='operator_review_disposition','auth_status');req(status['campaign_phase']=='operator_review_required','campaign_status');req(status['ownership_present'],'ownership_status');req(status['environment_evidence_present'],'environment_status');req(status['operator_can_diagnose_without_private_content'],'content_free_status');req(status['observability_is_execution_authority'] is False,'no_auth')
print(json.dumps({'ok':True,'suite':'v1277.3-5-development-observability-integration','passed':len(C),'failed':0,'checks':C},sort_keys=True))
