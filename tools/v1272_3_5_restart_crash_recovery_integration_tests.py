from __future__ import annotations
import json, os, sys, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.dont_write_bytecode=True;os.environ['PYTHONDONTWRITEBYTECODE']='1'
for p in (ROOT,ROOT/'conscious_agent',ROOT/'tools'):
    if str(p) not in sys.path:sys.path.insert(0,str(p))
from v1272_fixture import prepared_recovery_chain
from v1270_fixture import initial_provider, repair_provider
from isolated_self_modification import execute_isolated_self_modification
from iterative_self_repair import execute_iterative_self_repair
from self_development_alpha import execute_self_development_alpha_candidate
from self_development_alpha_foundations import _stage_root, load_self_development_alpha_campaign
from long_running_work_sessions_foundations import build_verification_harness_budget
from restart_crash_recovery_foundations import begin_recovery_operation, load_restart_crash_recovery
from restart_crash_recovery import *
C=[]
def req(v,l):
    if not v: raise AssertionError(l)
    C.append(l)

def crash_after(_):
    raise RuntimeError('simulated_process_death_after_durable_stage')

with tempfile.TemporaryDirectory(prefix='eidolon-v1272-int-') as td:
    base=Path(td)
    c=prepared_recovery_chain(base/'a',now=1000.0);rid=c['recovery']['recovery_id'];pcalls=[];rcalls=[]
    wrong=execute_recoverable_candidate(rid,c['source'],runtime_root=c['runtime'],authorization_phrase='go ahead',provider=initial_provider(pcalls))
    req(wrong['status']=='isolated_self_modification_exact_authorization_required','generic_candidate_authority_rejected')
    req(len(pcalls)==0,'wrong_auth_no_provider')
    try:
        execute_recoverable_candidate(rid,c['source'],runtime_root=c['runtime'],authorization_phrase=c['campaign']['candidate_authorization_phrase'],provider=initial_provider(pcalls),post_stage_hook=crash_after)
        raise AssertionError('simulated_crash_missing')
    except RuntimeError as exc:
        req('simulated_process_death' in str(exc),'candidate_crash_simulated')
    req(len(pcalls)==1,'candidate_provider_called_once_before_crash')
    alpha=load_self_development_alpha_campaign(c['campaign']['campaign_id'],runtime_root=c['runtime'])
    req(alpha['phase']=='repair_authorization_required','candidate_alpha_durable_before_v1272_receipt')
    recon=reconcile_restart_crash_recovery(rid,c['source'],runtime_root=c['runtime'],now=1100.0)
    req(recon['ok'],'candidate_reconcile_ok')
    req(recon['candidate_recovery']['completed'],'candidate_reconciled_completed')
    req(recon['duplicate_provider_activity_created'] is False,'candidate_reconcile_no_provider_replay')
    replay=execute_recoverable_candidate(rid,c['source'],runtime_root=c['runtime'],authorization_phrase=c['campaign']['candidate_authorization_phrase'],provider=initial_provider(pcalls))
    req(replay['restart_duplicate_suppressed'] is True,'candidate_replay_suppressed')
    req(len(pcalls)==1,'candidate_provider_still_once')
    alpha=load_self_development_alpha_campaign(c['campaign']['campaign_id'],runtime_root=c['runtime'])
    budget=build_verification_harness_budget(['selected_suite'],phase_budget_seconds=900,estimated_seconds_per_test=30)
    try:
        execute_recoverable_verification_and_review(rid,c['source'],runtime_root=c['runtime'],repair_authorization_phrase=alpha['repair_authorization_phrase'],repair_provider=repair_provider(rcalls),budget=budget,post_stage_hook=crash_after)
        raise AssertionError('verification_crash_missing')
    except RuntimeError as exc:
        req('simulated_process_death' in str(exc),'verification_crash_simulated')
    req(len(rcalls)==1,'repair_provider_called_once_before_crash')
    alpha=load_self_development_alpha_campaign(c['campaign']['campaign_id'],runtime_root=c['runtime'])
    req(alpha['phase']=='operator_review_required','verification_alpha_durable_before_v1272_receipt')
    recon2=reconcile_restart_crash_recovery(rid,c['source'],runtime_root=c['runtime'],now=1200.0)
    req(recon2['verification_recovery']['completed'],'verification_reconciled_completed')
    replay2=execute_recoverable_verification_and_review(rid,c['source'],runtime_root=c['runtime'],repair_authorization_phrase='',repair_provider=repair_provider(rcalls),budget=budget)
    req(replay2['restart_duplicate_suppressed'] is True,'verification_replay_suppressed')
    req(len(rcalls)==1,'repair_provider_still_once')
    status=restart_crash_recovery_operator_status(rid,runtime_root=c['runtime'])
    req(status['current_phase']=='operator_review_required','operator_phase_visible')
    req(status['next_required_authorization']=='operator_review_disposition','operator_next_authority_visible')
    req(status['automatic_retry'] is False and status['automatic_resume'] is False,'operator_status_no_auto')

    # Stronger lower-stage crash window: v1265 sealed, alpha not yet advanced.
    c2=prepared_recovery_chain(base/'b',now=2000.0);rid2=c2['recovery']['recovery_id'];calls2=[]
    e=begin_recovery_operation(rid2,runtime_root=c2['runtime'],operation_code='candidate_stage',target_id=c2['campaign']['candidate_operation_id'],now=2001.0)
    low=execute_isolated_self_modification(c2['campaign']['candidate_operation_id'],c2['source'],runtime_root=_stage_root(c2['runtime'],'v1265'),authorization_phrase=c2['campaign']['candidate_authorization_phrase'],provider=initial_provider(calls2))
    req(low['phase']=='sealed','lower_candidate_sealed')
    req(load_self_development_alpha_campaign(c2['campaign']['campaign_id'],runtime_root=c2['runtime'])['phase']=='prepared','alpha_not_yet_advanced')
    recon3=reconcile_restart_crash_recovery(rid2,c2['source'],runtime_root=c2['runtime'],now=2010.0)
    req(recon3['candidate_recovery']['status']=='candidate_recovered_from_v1265_lineage','lower_candidate_lineage_reconciled')
    req(len(calls2)==1,'lower_candidate_no_provider_replay')
    alpha2=load_self_development_alpha_campaign(c2['campaign']['campaign_id'],runtime_root=c2['runtime'])
    req(alpha2['phase']=='repair_authorization_required','alpha_advanced_from_sealed_lower')

    # Stronger lower verification crash window: v1267 passed, alpha not yet advanced.
    rcalls2=[]
    begin_recovery_operation(rid2,runtime_root=c2['runtime'],operation_code='verification_stage',target_id=alpha2['repair_id'],now=2020.0)
    lowrepair=execute_iterative_self_repair(
        alpha2['repair_id'],c2['source'],
        self_modification_runtime_root=_stage_root(c2['runtime'],'v1265'),
        test_selection_runtime_root=_stage_root(c2['runtime'],'v1266'),
        runtime_root=_stage_root(c2['runtime'],'v1267'),
        authorization_phrase=alpha2['repair_authorization_phrase'],provider=repair_provider(rcalls2),
    )
    req(lowrepair['phase']=='passed','lower_verification_passed')
    req(load_self_development_alpha_campaign(c2['campaign']['campaign_id'],runtime_root=c2['runtime'])['phase']=='repair_authorization_required','alpha_not_yet_advanced_after_lower_verification')
    lower_test_runs=int((lowrepair.get('verification') or {}).get('test_run_count') or 0)
    recon4=reconcile_restart_crash_recovery(rid2,c2['source'],runtime_root=c2['runtime'],now=2030.0)
    req(recon4['verification_recovery']['status']=='verification_recovered_from_v1267_lineage','lower_verification_lineage_reconciled')
    req(recon4['verification_recovery']['tests_replayed'] is False,'lower_verification_no_test_replay')
    req(recon4['verification_recovery']['provider_replayed'] is False,'lower_verification_no_provider_replay')
    req(len(rcalls2)==1,'lower_verification_provider_still_once')
    req(lower_test_runs>=1,'lower_verification_original_tests_observed')
    req(load_self_development_alpha_campaign(c2['campaign']['campaign_id'],runtime_root=c2['runtime'])['phase']=='operator_review_required','alpha_advanced_from_passed_lower_verification')

    # Provider outage discovered before a stage pauses cleanly and return does not auto-execute.
    c3=prepared_recovery_chain(base/'c',now=3000.0);rid3=c3['recovery']['recovery_id']
    outage=record_provider_outage(rid3,runtime_root=c3['runtime']);req(outage['provider_state']=='unavailable','outage_recorded')
    returned=record_provider_return(rid3,runtime_root=c3['runtime']);req(returned['provider_state']=='available','return_recorded')
    resumed=resume_restart_crash_recovery(rid3,c3['source'],runtime_root=c3['runtime']);req(resumed['resume_applied'],'provider_return_resume_available')
    req(resumed['underlying_authorization_reused'] is False,'resume_does_not_reuse_authority')
    req(resumed['fresh_stage_authorization_still_required'] is True,'fresh_stage_authority_still_required')
print(json.dumps({'ok':True,'suite':'v1272.3-v1272.5-restart-crash-recovery-integration','passed':len(C),'failed':0,'checks':C},sort_keys=True))
