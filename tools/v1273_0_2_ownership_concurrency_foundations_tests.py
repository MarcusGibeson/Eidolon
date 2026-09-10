from __future__ import annotations
import json, os, sys, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.dont_write_bytecode=True;os.environ['PYTHONDONTWRITEBYTECODE']='1'
for p in (ROOT,ROOT/'conscious_agent',ROOT/'tools'):
    if str(p) not in sys.path:sys.path.insert(0,str(p))
from v1273_fixture import prepared_ownership_chain
from ownership_concurrency_foundations import *
C=[]
def req(v,l):
    if not v: raise AssertionError(l)
    C.append(l)

with tempfile.TemporaryDirectory(prefix='eidolon-v1273-found-') as td:
    c=prepared_ownership_chain(Path(td),now=1000.0);o=c['ownership'];oid=o['ownership_id'];target=c['campaign']['candidate_operation_id']
    req(validate_ownership_concurrency(o)['ok'],'record_valid')
    req(o['exactly_once_stage_claims'] is True,'exactly_once_contract')
    req(o['expired_claim_requires_reconciliation'] is True,'expiry_reconciliation_contract')
    req(o['late_results_are_fenced'] is True,'late_result_fence_contract')
    req(o['underlying_exact_authorization_still_required'] is True,'underlying_authority_preserved')
    restored=prepare_ownership_concurrency(c['recovery']['recovery_id'],runtime_root=c['runtime'],now=1001.0)
    req(restored['operation_status']=='restored','prepare_idempotent')
    a=acquire_operation_ownership(oid,runtime_root=c['runtime'],operation_code='candidate_stage',target_id=target,owner_id='worker-a',claimant_kind='process',lease_seconds=30,now=1010.0)
    req(a['execution_allowed'] is True,'first_owner_executes')
    req(a['epoch']==1,'first_epoch')
    req(len(a['owner_key'])==64 and 'worker-a' not in json.dumps(load_ownership_concurrency(oid,runtime_root=c['runtime'])),'raw_owner_not_persisted')
    same=acquire_operation_ownership(oid,runtime_root=c['runtime'],operation_code='candidate_stage',target_id=target,owner_id='worker-a',claimant_kind='process',lease_seconds=30,now=1011.0)
    req(same['operation_status']=='ownership_already_held_by_claimant','same_owner_duplicate_identified')
    req(same['execution_allowed'] is False,'same_owner_duplicate_reentry_suppressed')
    req(same['epoch']==1 and same['fence_token']==a['fence_token'],'same_owner_same_fence')
    other=acquire_operation_ownership(oid,runtime_root=c['runtime'],operation_code='candidate_stage',target_id=target,owner_id='tab-b',claimant_kind='browser_tab',lease_seconds=30,now=1012.0)
    req(other['operation_status']=='owned_elsewhere','live_owner_blocks_other')
    req(other['execution_allowed'] is False,'duplicate_execution_denied')
    hb=renew_operation_ownership(oid,runtime_root=c['runtime'],operation_code='candidate_stage',target_id=target,owner_id='worker-a',epoch=1,fence_token=a['fence_token'],lease_seconds=30,now=1020.0)
    req(hb['renewed'] is True and hb['lease_expires_at']==1050.0,'heartbeat_renews_bounded_lease')
    expired=acquire_operation_ownership(oid,runtime_root=c['runtime'],operation_code='candidate_stage',target_id=target,owner_id='queue-c',claimant_kind='queue_worker',lease_seconds=30,now=1060.0)
    req(expired['epoch']==2,'expired_transfer_new_epoch')
    req(expired['reconciliation_required'] is True,'expired_transfer_requires_reconciliation')
    req(expired['execution_allowed'] is False,'expired_transfer_cannot_execute_immediately')
    late=fence_operation_result(oid,runtime_root=c['runtime'],operation_code='candidate_stage',target_id=target,owner_id='worker-a',epoch=1,fence_token=a['fence_token'],now=1061.0)
    req(late['status']=='stale_owner_result_rejected','old_epoch_result_fenced')
    req(late['result_may_commit'] is False,'late_result_cannot_commit')
    active=activate_operation_after_reconciliation(oid,runtime_root=c['runtime'],operation_code='candidate_stage',target_id=target,owner_id='queue-c',epoch=2,fence_token=expired['fence_token'],reconciliation_code='no_inflight_effect',now=1062.0)
    req(active['execution_allowed'] is True,'successor_activated_after_reconciliation')
    cur=fence_operation_result(oid,runtime_root=c['runtime'],operation_code='candidate_stage',target_id=target,owner_id='queue-c',epoch=2,fence_token=expired['fence_token'],now=1063.0)
    req(cur['result_may_commit'] is True,'current_owner_result_accepted')
    done=complete_operation_ownership(oid,runtime_root=c['runtime'],operation_code='candidate_stage',target_id=target,owner_id='queue-c',epoch=2,fence_token=expired['fence_token'],completion_code='candidate_stage_completed',durable_lineage_digest='a'*64,result_digest='b'*64,now=1064.0)
    req(done['completed'] is True,'terminal_completion_recorded')
    duplicate=acquire_operation_ownership(oid,runtime_root=c['runtime'],operation_code='candidate_stage',target_id=target,owner_id='retry-d',claimant_kind='retry_worker',lease_seconds=30,now=1065.0)
    req(duplicate['operation_status']=='already_completed','terminal_completion_suppresses_retry')
    req(duplicate['execution_allowed'] is False,'completed_never_reexecutes')
    pub=public_ownership_concurrency(load_ownership_concurrency(oid,runtime_root=c['runtime']),now=1065.0)
    req(pub['completed_claim_count']==1,'public_completed_count')
    req(pub['owner_ids_persisted'] is False,'public_no_owner_ids')
    req(pub['bounded_summary_count']<=MAX_SUMMARIES,'bounded_summaries')
    for k,v in AUTHORITY_FLAGS.items(): req(pub[k] is v,'authority_'+k)
print(json.dumps({'ok':True,'suite':'v1273.0-v1273.2-ownership-concurrency-foundations','passed':len(C),'failed':0,'checks':C},sort_keys=True))
