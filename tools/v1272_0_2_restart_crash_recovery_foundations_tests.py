from __future__ import annotations
import json, os, sys, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.dont_write_bytecode=True;os.environ['PYTHONDONTWRITEBYTECODE']='1'
for p in (ROOT,ROOT/'conscious_agent',ROOT/'tools'):
    if str(p) not in sys.path:sys.path.insert(0,str(p))
from v1272_fixture import prepared_recovery_chain
from restart_crash_recovery_foundations import *
C=[]
def req(v,l):
    if not v: raise AssertionError(l)
    C.append(l)

with tempfile.TemporaryDirectory(prefix='eidolon-v1272-found-') as td:
    c=prepared_recovery_chain(Path(td), now=1000.0, lease_seconds=30)
    r=c['recovery'];rid=r['recovery_id']
    req(r['state']=='healthy','state_healthy')
    req(r['restart_generation']==0,'restart_generation_zero')
    req(r['write_ahead_journal_required'] is True,'write_ahead_required')
    req(r['completion_requires_durable_lineage'] is True,'durable_lineage_required')
    req(r['ambiguous_external_effects_fail_closed'] is True,'ambiguous_fail_closed')
    req(r['restart_never_creates_authorization'] is True,'restart_no_authorization')
    req(validate_restart_crash_recovery(r)['ok'],'record_valid')
    restored=prepare_restart_crash_recovery(c['session']['session_id'],runtime_root=c['runtime'],now=1001.0)
    req(restored['operation_status']=='restored','prepare_idempotent')
    req(restored['recovery_id']==rid,'stable_recovery_id')
    entry=begin_recovery_operation(rid,runtime_root=c['runtime'],operation_code='candidate_stage',target_id=c['campaign']['candidate_operation_id'],now=1010.0)
    req(entry['state']=='started','journal_started')
    req(entry['generation']==1,'journal_generation_one')
    req(entry['duplicate_external_activity_allowed'] is False,'journal_duplicate_denied')
    same=begin_recovery_operation(rid,runtime_root=c['runtime'],operation_code='candidate_stage',target_id=c['campaign']['candidate_operation_id'],now=1011.0)
    req(same['operation_status']=='existing_incomplete','incomplete_restored')
    req(same['generation']==1,'incomplete_generation_stable')
    finished=finish_recovery_operation(rid,runtime_root=c['runtime'],operation_code='candidate_stage',generation=1,state='authorization_required',outcome_code='candidate_authorization_required',now=1012.0)
    req(finished['state']=='authorization_required','authorization_required_recorded')
    entry2=begin_recovery_operation(rid,runtime_root=c['runtime'],operation_code='candidate_stage',target_id=c['campaign']['candidate_operation_id'],now=1013.0)
    req(entry2['generation']==2,'new_attempt_generation_after_nonexternal_auth_failure')
    finish_recovery_operation(rid,runtime_root=c['runtime'],operation_code='candidate_stage',generation=2,state='completed',outcome_code='candidate_stage_durable',durable_lineage_digest='a'*64,now=1014.0)
    done=begin_recovery_operation(rid,runtime_root=c['runtime'],operation_code='candidate_stage',target_id=c['campaign']['candidate_operation_id'],now=1015.0)
    req(done['operation_status']=='already_completed','completed_stage_suppresses_replay')
    req(done['duplicate_external_activity_allowed'] is False,'completed_replay_denied')
    outage=note_recovery_interruption(rid,runtime_root=c['runtime'],interruption_code='provider_outage',now=1020.0)
    req(outage['provider_state']=='unavailable','provider_outage_state')
    returned=note_recovery_interruption(rid,runtime_root=c['runtime'],interruption_code='provider_return',now=1021.0)
    req(returned['provider_state']=='available','provider_return_state')
    restart=note_recovery_interruption(rid,runtime_root=c['runtime'],interruption_code='process_restart',now=1030.0)
    req(restart['restart_generation']==1,'restart_generation_incremented')
    dashboard=note_recovery_interruption(rid,runtime_root=c['runtime'],interruption_code='dashboard_closed',now=1031.0)
    req(dashboard['last_interruption_code']=='dashboard_closed','dashboard_close_recorded')
    req(dashboard['restart_generation']==1,'dashboard_close_not_false_machine_restart')
    machine=note_recovery_interruption(rid,runtime_root=c['runtime'],interruption_code='machine_interruption',now=1032.0)
    req(machine['restart_generation']==2,'machine_interruption_generation_incremented')
    public=public_restart_crash_recovery(load_restart_crash_recovery(rid,runtime_root=c['runtime']))
    req(public['operation_count']==2,'journal_count')
    req(public['recovery_receipt_count']>=6,'recovery_receipts_present')
    req(public['bounded_summary_count']<=MAX_RECOVERY_SUMMARIES,'bounded_summaries')
    req(public['content_free'] is True,'content_free')
    req(public['active_source_modified'] is False,'active_source_unmodified')

    try:
        begin_recovery_operation(rid,runtime_root=c['runtime'],operation_code='candidate_stage',target_id='contains private prose',now=1040.0)
        raise AssertionError('unsafe_target_rejected')
    except ValueError as exc:
        req(str(exc)=='invalid_restart_crash_recovery_target_id','unsafe_target_rejected')
    try:
        finish_recovery_operation(rid,runtime_root=c['runtime'],operation_code='candidate_stage',generation=2,state='completed',outcome_code='candidate_stage_durable',durable_lineage_digest='not-a-digest',now=1041.0)
        raise AssertionError('invalid_lineage_digest_rejected')
    except ValueError as exc:
        req(str(exc)=='invalid_restart_crash_recovery_durable_lineage_digest','invalid_lineage_digest_rejected')
    for k,v in AUTHORITY_FLAGS.items(): req(public[k] is v,'authority_'+k)
print(json.dumps({'ok':True,'suite':'v1272.0-v1272.2-restart-crash-recovery-foundations','passed':len(C),'failed':0,'checks':C},sort_keys=True))
