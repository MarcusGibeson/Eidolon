from __future__ import annotations
"""v1277.3-v1277.5 integration with the v1270-v1274 development lineage."""
import time
from pathlib import Path
from typing import Any,Callable,Mapping
from self_development_alpha_foundations import _runtime_root,load_self_development_alpha_campaign
from long_running_work_sessions import execute_long_running_candidate,execute_long_running_verification_and_review,long_running_operator_status
from long_running_work_sessions_foundations import load_long_running_work_session
from restart_crash_recovery_foundations import recovery_id_for_session,load_restart_crash_recovery
from ownership_concurrency_foundations import ownership_id_for_recovery,load_ownership_concurrency
from environment_awareness_foundations import environment_id_for_ownership,load_environment_awareness
from development_observability_foundations import *
CONTRACT_VERSION='v1277.5'
def _marker(kind,digest):
    from development_observability_foundations import _digest
    return _digest({'kind':str(kind),'digest':str(digest)})
def _lineage(obs,runtime_root):
    runtime=_runtime_root(runtime_root);sid=str(obs.get('session_id') or '');cid=str(obs.get('campaign_id') or '');sd=str(obs.get('source_manifest_digest') or '')
    s=load_long_running_work_session(sid,runtime_root=runtime);c=load_self_development_alpha_campaign(cid,runtime_root=runtime);rid=recovery_id_for_session(sid,cid,sd);r=load_restart_crash_recovery(rid,runtime_root=runtime);oid=ownership_id_for_recovery(rid,sd);o=load_ownership_concurrency(oid,runtime_root=runtime);eid=environment_id_for_ownership(oid,sd);e=load_environment_awareness(eid,runtime_root=runtime)
    return {'session':s,'campaign':c,'recovery':r,'ownership':o,'environment':e,'recovery_id':rid,'ownership_id':oid,'environment_id':eid}
def sync_development_observability(observability_id,*,runtime_root,now=None):
    runtime=_runtime_root(runtime_root);row=load_development_observability(observability_id,runtime_root=runtime)
    if not validate_development_observability(row).get('ok'):raise ValueError('valid_development_observability_required')
    lin=_lineage(row,runtime);s=lin['session']
    for rec in s.get('progress_receipts') or []:
        d=str(rec.get('receipt_digest') or '')
        if not d:continue
        out=str(rec.get('outcome') or 'attempted');ev={'completed':'phase_completed','attempted':'phase_attempted','blocked':'phase_blocked','cancelled':'cancelled','skipped':'progress_observed'}.get(out,'progress_observed');mapped='completed' if out=='completed' else ('blocked' if out=='blocked' else ('cancelled' if out=='cancelled' else 'attempted'))
        record_observability_event(observability_id,runtime_root=runtime,event_code=ev,phase=str(rec.get('phase') or 'blocked'),outcome=mapped,work_code=str(rec.get('work_code') or 'progress'),elapsed_seconds=float(rec.get('elapsed_seconds') or 0.0),detail_codes=list(rec.get('detail_codes') or []),lineage_marker=_marker('session_receipt',d),now=now)
    r=lin['recovery']
    if r:
        for rec in r.get('recovery_receipts') or []:
            d=str(rec.get('receipt_digest') or '')
            if not d:continue
            reasons=[str(x) for x in rec.get('reason_codes') or []];code='provider_outage' if 'provider_outage' in reasons else ('provider_return' if 'provider_return' in reasons else 'recovery_observed')
            record_observability_event(observability_id,runtime_root=runtime,event_code=code,phase=str(s.get('current_phase') or 'blocked'),outcome='observed',work_code='recovery',detail_codes=[str(rec.get('receipt_code') or 'recovery_event'),*reasons],lineage_marker=_marker('recovery_receipt',d),now=now)
    o=lin['ownership']
    if o:
        for ev in o.get('events') or []:
            d=str(ev.get('event_digest') or '')
            if not d:continue
            record_observability_event(observability_id,runtime_root=runtime,event_code='ownership_observed',phase=str(s.get('current_phase') or 'blocked'),outcome='observed',work_code='ownership',detail_codes=[str(ev.get('event_code') or 'ownership_event'),*list(ev.get('reason_codes') or [])],lineage_marker=_marker('ownership_event',d),now=now)
    e=lin['environment']
    if e and e.get('record_digest'):
        record_observability_event(observability_id,runtime_root=runtime,event_code='environment_evidence_observed',phase=str(s.get('current_phase') or 'blocked'),outcome='observed',work_code='environment',detail_codes=['evidence_digest_only'],lineage_marker=_marker('environment_record',str(e.get('record_digest'))),now=now)
    status=long_running_operator_status(str(row.get('session_id') or ''),runtime_root=runtime);cur=load_development_observability(observability_id,runtime_root=runtime);auth=str(status.get('next_required_authorization') or 'operator_reconciliation');phase=str(status.get('current_phase') or cur.get('current_phase') or 'blocked')
    if auth!=str(cur.get('next_required_authorization') or ''):
        record_observability_event(observability_id,runtime_root=runtime,event_code='authorization_required',phase=phase,outcome='observed',work_code='authorization',detail_codes=[auth],lineage_marker=_marker('authorization',f"{phase}:{auth}:{status.get('campaign_phase')}"),next_required_authorization=auth,now=now)
    return {**load_development_observability(observability_id,runtime_root=runtime),'operation_status':'observability_synchronized'}
def execute_observed_candidate(observability_id,source_root,*,runtime_root,authorization_phrase,provider):
    runtime=_runtime_root(runtime_root);obs=load_development_observability(observability_id,runtime_root=runtime)
    if not validate_development_observability(obs).get('ok'):raise ValueError('valid_development_observability_required')
    record_observability_event(observability_id,runtime_root=runtime,event_code='phase_started',phase='candidate_execution',outcome='started',work_code='candidate_stage');start=time.monotonic();res=execute_long_running_candidate(str(obs.get('session_id') or ''),source_root,runtime_root=runtime,authorization_phrase=authorization_phrase,provider=provider);elapsed=time.monotonic()-start;sync=sync_development_observability(observability_id,runtime_root=runtime)
    return {**res,'observability_id':observability_id,'observability_elapsed_seconds':elapsed,'observability_record_digest':sync.get('record_digest'),'private_payloads_persisted':False}
def execute_observed_verification_and_review(observability_id,source_root,*,runtime_root,repair_authorization_phrase,repair_provider,budget=None):
    runtime=_runtime_root(runtime_root);obs=load_development_observability(observability_id,runtime_root=runtime)
    if not validate_development_observability(obs).get('ok'):raise ValueError('valid_development_observability_required')
    if budget and budget.get('monolithic_run_within_budget') is False:build_harness_budget_signal(observability_id,runtime_root=runtime,phase='verification_and_repair',predicted_seconds=float(budget.get('predicted_seconds') or budget.get('predicted_total_seconds') or budget.get('estimated_total_seconds') or 0),budget_seconds=float(budget.get('phase_budget_seconds') or 0))
    record_observability_event(observability_id,runtime_root=runtime,event_code='phase_started',phase='verification_and_repair',outcome='started',work_code='verification_stage');start=time.monotonic();res=execute_long_running_verification_and_review(str(obs.get('session_id') or ''),source_root,runtime_root=runtime,repair_authorization_phrase=repair_authorization_phrase,repair_provider=repair_provider,budget=budget);elapsed=time.monotonic()-start;sync=sync_development_observability(observability_id,runtime_root=runtime)
    return {**res,'observability_id':observability_id,'observability_elapsed_seconds':elapsed,'observability_record_digest':sync.get('record_digest'),'private_payloads_persisted':False}
def development_observability_operator_status(observability_id,*,runtime_root,now=None):
    sync_development_observability(observability_id,runtime_root=runtime_root,now=now);row=load_development_observability(observability_id,runtime_root=runtime_root);public=public_development_observability(row);lin=_lineage(row,runtime_root);public.update({'campaign_phase':lin['campaign'].get('phase') if lin['campaign'] else 'unknown','session_state':lin['session'].get('state') if lin['session'] else 'unknown','recovery_state':lin['recovery'].get('state') if lin['recovery'] else 'not_prepared','ownership_present':bool(lin['ownership']),'environment_evidence_present':bool(lin['environment']),'operator_can_diagnose_without_private_content':True});return public
__all__=['CONTRACT_VERSION','sync_development_observability','execute_observed_candidate','execute_observed_verification_and_review','development_observability_operator_status']
