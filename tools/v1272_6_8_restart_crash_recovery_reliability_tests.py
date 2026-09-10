from __future__ import annotations
import json, os, sys, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.dont_write_bytecode=True;os.environ['PYTHONDONTWRITEBYTECODE']='1'
for p in (ROOT,ROOT/'conscious_agent',ROOT/'tools'):
    if str(p) not in sys.path:sys.path.insert(0,str(p))
from v1272_fixture import prepared_recovery_chain
from v1270_fixture import initial_provider
from v1269_fixture import approved_chain
from governed_self_update_foundations import prepare_governed_self_update
from long_running_work_sessions_reliability import claim_or_renew_work_session_lease
from restart_crash_recovery_foundations import begin_recovery_operation, load_restart_crash_recovery, _path
from restart_crash_recovery import reconcile_restart_crash_recovery
from restart_crash_recovery_reliability import *
C=[]
def req(v,l):
    if not v: raise AssertionError(l)
    C.append(l)

with tempfile.TemporaryDirectory(prefix='eidolon-v1272-rel-') as td:
    base=Path(td);c=prepared_recovery_chain(base/'restart',now=1000.0,lease_seconds=30);rid=c['recovery']['recovery_id'];sid=c['session']['session_id']
    lease=claim_or_renew_work_session_lease(sid,'desktop-worker',runtime_root=c['runtime'],now=1010.0);req(lease['lease_acquired'],'lease_acquired_before_crash')
    rec=recover_after_process_restart(rid,c['source'],runtime_root=c['runtime'],interruption_code='process_restart',now=1050.0)
    req(rec['ok'],'restart_recovery_ok')
    req(rec['stale_lease_recovered'] is True,'expired_lease_recovered_after_restart')
    req(rec['provider_replayed'] is False and rec['tests_replayed'] is False and rec['update_replayed'] is False,'restart_no_external_replay')
    req(rec['automatic_resume'] is False,'restart_not_auto_resume')

    # Ambiguous candidate execution fails closed. Simulate process death after running marker.
    c2=prepared_recovery_chain(base/'ambiguous',now=2000.0);rid2=c2['recovery']['recovery_id']
    entry=begin_recovery_operation(rid2,runtime_root=c2['runtime'],operation_code='candidate_stage',target_id=c2['campaign']['candidate_operation_id'],now=2001.0)
    from self_development_alpha_foundations import _stage_root
    from isolated_self_modification_foundations import load_self_modification,_record_path,_record_digest,_write_json
    lower=load_self_modification(c2['campaign']['candidate_operation_id'],runtime_root=_stage_root(c2['runtime'],'v1265'))
    lower=dict(lower);lower.update({'phase':'running','status':'isolated_self_modification_running','provider_contacted':False});lower['record_digest']=_record_digest(lower);_write_json(_record_path(c2['campaign']['candidate_operation_id'],_stage_root(c2['runtime'],'v1265')),lower)
    amb=recover_after_process_restart(rid2,c2['source'],runtime_root=c2['runtime'],interruption_code='process_crash',now=2010.0)
    req(amb['status']=='restart_crash_recovery_operator_reconciliation_required','ambiguous_fail_closed')
    req(amb['candidate_recovery']['ambiguous'] is True,'ambiguous_candidate_visible')
    req(amb['provider_replayed'] is False,'ambiguous_no_provider_retry')

    # A corrupt v1272 projection is quarantined and rebuilt from valid lower lineage,
    # but loss of the write-ahead journal itself forces review rather than invented history.
    c3=prepared_recovery_chain(base/'corrupt',now=3000.0);rid3=c3['recovery']['recovery_id']
    p=_path(rid3,c3['runtime']);p.write_text('{broken',encoding='utf-8')
    rebuilt=rebuild_recovery_from_authoritative_lineage(c3['session']['session_id'],runtime_root=c3['runtime'],now=3010.0)
    req(rebuilt['ok'],'corrupt_projection_rebuilt')
    req(rebuilt['quarantined'] is True,'corrupt_projection_quarantined')
    req(rebuilt['operator_reconciliation_required'] is True,'lost_journal_requires_review')
    req(rebuilt['external_effect_history_assumed'] is False,'no_invented_external_history')

    # v1269 update recovery is inspect-only from v1272; it never replays the update.
    u=approved_chain(base/'update');urt=base/'update-runtime'
    update=prepare_governed_self_update(u['packet']['review_id'],u['source'],self_modification_runtime_root=u['sm'],review_runtime_root=u['review_rt'],runtime_root=urt)
    ui=inspect_governed_update_restart_state(update['update_id'],u['source'],runtime_root=urt)
    req(ui['ok'],'update_restart_inspection_ok')
    req(ui['update_phase']=='prepared','update_prepared_visible')
    req(ui['update_executed_by_v1272'] is False,'v1272_never_executes_update')
    req(ui['authorization_reused_by_v1272'] is False,'v1272_never_reuses_update_auth')
    req(ui['successful_rollback_remains_separately_authorized'] is True,'rollback_separate')

    health=inspect_restart_crash_recovery_health(source_root=ROOT);req(health['ok'],'health_ready')
    handoff=build_restart_crash_recovery_operator_handoff(source_root=ROOT);req(handoff['ok'],'handoff_ready')
    req('cross_process_exactly_once_ownership_deferred_to_v1273' in handoff['known_limitations'],'v1273_boundary')
    req('process_kill_between_lower_stage_commit_and_v1272_receipt' in handoff['native_windows_review'],'windows_crash_window_handoff')
    req(handoff['next_bounded_unit']=='v1273 Ownership and Concurrency','next_v1273')
print(json.dumps({'ok':True,'suite':'v1272.6-v1272.8-restart-crash-recovery-reliability','passed':len(C),'failed':0,'checks':C},sort_keys=True))
