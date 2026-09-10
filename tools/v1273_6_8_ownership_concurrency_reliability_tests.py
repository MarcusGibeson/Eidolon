from __future__ import annotations
import json, multiprocessing as mp, os, sys, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.dont_write_bytecode=True;os.environ['PYTHONDONTWRITEBYTECODE']='1'
for p in (ROOT,ROOT/'conscious_agent',ROOT/'tools'):
    if str(p) not in sys.path:sys.path.insert(0,str(p))
from v1273_fixture import prepared_ownership_chain
from ownership_concurrency_foundations import *
from ownership_concurrency_foundations import _path
from ownership_concurrency_reliability import *

def race_claim(args):
    root,oid,target,owner=args
    sys.path[:0]=[str(ROOT),str(ROOT/'conscious_agent'),str(ROOT/'tools')]
    from ownership_concurrency_foundations import acquire_operation_ownership
    r=acquire_operation_ownership(oid,runtime_root=root,operation_code='candidate_stage',target_id=target,owner_id=owner,claimant_kind='process',lease_seconds=30,now=1010.0)
    return {'owner':owner,'status':r.get('operation_status'),'execute':r.get('execution_allowed'),'fence_token':r.get('fence_token'),'epoch':r.get('epoch')}

def main():
    C=[]
    def req(v,l):
        if not v: raise AssertionError(l)
        C.append(l)
    with tempfile.TemporaryDirectory(prefix='eidolon-v1273-rel-') as td:
        base=Path(td);c=prepared_ownership_chain(base/'race',now=1000.0);oid=c['ownership']['ownership_id'];target=c['campaign']['candidate_operation_id']
        # Spawn is deliberate: it mirrors Windows process semantics instead of
        # inheriting state through fork.
        ctx=mp.get_context('spawn')
        with ctx.Pool(4) as pool:
            rows=pool.map(race_claim,[(str(c['runtime']),oid,target,f'proc-{i}') for i in range(4)])
        winners=[x for x in rows if x['execute']]
        req(len(winners)==1,'multiprocess_exactly_one_live_owner')
        req(sum(1 for x in rows if x['status']=='owned_elsewhere')==3,'multiprocess_losers_fenced')
        owner=winners[0]['owner'];current=winners[0]
        duplicate_same=acquire_operation_ownership(oid,runtime_root=c['runtime'],operation_code='candidate_stage',target_id=target,owner_id=owner,lease_seconds=30,now=1011.0)
        req(duplicate_same['execution_allowed'] is False,'same_process_retry_reentry_suppressed')
        req(duplicate_same['operation_status']=='ownership_already_held_by_claimant','same_process_retry_identified')
        exp=recover_expired_ownership_claims(oid,runtime_root=c['runtime'],now=1050.0)
        req(exp['expired_claim_count']==1,'expired_claim_detected')
        req(exp['automatic_transfer_performed'] is False,'expiry_detection_no_auto_transfer')
        req(exp['v1272_reconciliation_required_before_successor_execution'] is True,'expiry_requires_recovery_reconciliation')
        transfer=transfer_expired_operation_ownership(oid,c['source'],runtime_root=c['runtime'],operation_code='candidate_stage',target_id=target,successor_owner_id='recovery-owner',lease_seconds=30,now=1051.0)
        req(transfer['status']=='ownership_transfer_reconciled_for_stage_entry','explicit_transfer_reconciled')
        req(transfer['execution_allowed'] is True,'clean_transfer_can_enter_stage')
        late=fence_operation_result(oid,runtime_root=c['runtime'],operation_code='candidate_stage',target_id=target,owner_id=owner,epoch=int(current['epoch']),fence_token=current['fence_token'],now=1052.0)
        req(late['status']=='stale_owner_result_rejected','late_old_process_result_rejected')

        c2=prepared_ownership_chain(base/'corrupt',now=2000.0);oid2=c2['ownership']['ownership_id'];p=_path(oid2,c2['runtime']);p.write_text('{broken',encoding='utf-8')
        q=quarantine_invalid_ownership_projection(oid2,runtime_root=c2['runtime'],now=2010.0)
        req(q['quarantined'] is True,'invalid_projection_quarantined')
        req(q['ownership_history_reconstructed'] is False,'invalid_projection_history_not_invented')
        req(q['operator_reconciliation_required'] is True,'invalid_projection_requires_operator')

        health=inspect_ownership_concurrency_health(source_root=ROOT);req(health['ok'],'health_ready')
        handoff=build_ownership_concurrency_operator_handoff(source_root=ROOT);req(handoff['ok'],'handoff_ready')
        req('late_provider_tool_result_rejection' in handoff['capabilities'],'late_result_capability')
        req('network_partition_distributed_consensus_is_out_of_scope_for_local_v1273' in handoff['known_limitations'],'distributed_consensus_boundary')
        req('two_process_same_stage_claim_race' in handoff['native_windows_review'],'windows_process_race_handoff')
        req(handoff['next_bounded_unit']=='v1274 Environment Awareness','next_v1274')
    print(json.dumps({'ok':True,'suite':'v1273.6-v1273.8-ownership-concurrency-reliability','passed':len(C),'failed':0,'checks':C},sort_keys=True))

if __name__=='__main__':
    mp.freeze_support()
    main()
