from __future__ import annotations
"""v1366 deterministic diagnosis for concurrency/recovery defects."""
import hashlib, json, re
from typing import Any, Mapping, Sequence
CONTRACT_VERSION='v1366.8'
DENIED={'source_mutation_authorized':False,'provider_contact_authorized':False,'network_authorized':False,'release_authorized':False,'approval_granted':False,'independent_authority_granted':False,'application_authorized':False}
KINDS={'duplicate_work','stale_ownership','lock_contention','race','crash_recovery'}
REPAIRS={'generation_compare_and_swap','idempotency_key','bounded_lock_timeout','serialized_transition','orphan_reconcile'}
def _d(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True,default=str).encode()).hexdigest()
def _simulate(kind:str, events:Sequence[Mapping[str,Any]], repair:str|None=None)->dict[str,Any]:
    owners={}; completed=set(); lock_owner=None; violations=[]; waits=0
    for i,e in enumerate(events):
        op=str(e.get('op') or ''); job=str(e.get('job') or 'job'); worker=str(e.get('worker') or ''); gen=int(e.get('generation') or 0)
        if op=='claim':
            prior=owners.get(job)
            if prior and prior!=(worker,gen):
                if repair in {'generation_compare_and_swap','idempotency_key'}: continue
                violations.append('duplicate_claim')
            else: owners[job]=(worker,gen)
        elif op=='complete':
            prior=owners.get(job)
            if prior!=(worker,gen):
                if repair=='generation_compare_and_swap': continue
                violations.append('stale_completion')
            if job in completed:
                if repair=='idempotency_key': continue
                violations.append('duplicate_completion')
            completed.add(job)
        elif op=='lock':
            if lock_owner and lock_owner!=worker:
                waits+=1
                if repair=='bounded_lock_timeout': continue
                violations.append('lock_contention_unbounded')
            else: lock_owner=worker
        elif op=='unlock':
            if lock_owner==worker: lock_owner=None
        elif op=='read_modify_write':
            if repair!='serialized_transition' and e.get('interleaved') is True: violations.append('lost_update_race')
        elif op=='owner_crash':
            if owners.get(job)==(worker,gen):
                if repair=='orphan_reconcile': owners.pop(job,None)
                else: violations.append('orphaned_ownership')
        elif op=='reconcile':
            if repair=='orphan_reconcile': owners.pop(job,None)
    return {'violation_codes':sorted(set(violations)),'violation_count':len(violations),'wait_count':waits,'completed_count':len(completed),'state_digest':_d({'owners':owners,'completed':sorted(completed),'lock_owner':lock_owner})}
def diagnose_concurrency(*,kind:str,events:Sequence[Mapping[str,Any]],candidate_repairs:Sequence[str]=())->dict[str,Any]:
    k=str(kind or '').strip()
    if k not in KINDS or not events or len(events)>128:return {'ok':False,'status':'concurrency_evidence_invalid','action_executed':False,**DENIED}
    before=_simulate(k,events)
    if not before['violation_count']:
        rec={'contract_version':CONTRACT_VERSION,'kind':k,'reproduced':False,'status':'not_reproduced','event_count':len(events),'event_digest':_d(list(events)),'repair_verified':False,'content_free':True,'action_executed':False,**DENIED};rec['record_digest']=_d(rec);return {'ok':True,'status':'not_reproduced','concurrency_diagnosis':rec,'action_executed':False,**DENIED}
    repairs=[]
    for r in candidate_repairs:
        r=str(r)
        if r not in REPAIRS or any(x['repair']==r for x in repairs):continue
        after=_simulate(k,events,r); repairs.append({'repair':r,'repair_digest':_d(r),'violation_count_after':after['violation_count'],'verified':after['violation_count']==0,'state_digest':after['state_digest']})
    winner=next((x for x in repairs if x['verified']),None)
    rec={'contract_version':CONTRACT_VERSION,'kind':k,'reproduced':True,'status':'repair_verified' if winner else 'defect_reproduced','event_count':len(events),'event_digest':_d(list(events)),'before_violation_codes':before['violation_codes'],'before_violation_count':before['violation_count'],'repair_trials':repairs,'repair_verified':bool(winner),'verified_repair':winner['repair'] if winner else None,'selected_source_modified':False,'deterministic_schedule':True,'content_free':True,'action_executed':False,**DENIED};rec['record_digest']=_d(rec)
    return {'ok':True,'status':rec['status'],'concurrency_diagnosis':rec,'action_executed':False,**DENIED}
def process_concurrency_diagnosis_control(text:str,*,project_state=None,**_):
    if str(text or '').strip().lower() not in {'show concurrency diagnosis','inspect concurrency diagnosis','show concurrency repair'}:return {'active':False}
    rec=dict((project_state or {}).get('concurrency_diagnosis') or {});return {'active':True,'ok':bool(rec),'status':'concurrency_diagnosis_found' if rec else 'concurrency_diagnosis_missing','concurrency_diagnosis':rec,'action_executed':False,**DENIED}
