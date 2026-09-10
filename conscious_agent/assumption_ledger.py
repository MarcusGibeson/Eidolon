from __future__ import annotations
"""v1323 durable, evidence-linked assumption ledger for deliberative planning."""
from pathlib import Path
from typing import Any, Iterable, Mapping

from cognitive_coding_foundations import digest
from candidate_approaches import PLANNING_DENIED_AUTHORITY
from project_evidence_store import atomic_json, evidence_root, read_json, seal, valid

CONTRACT_VERSION='v1323.8'
STATUSES=('active','validated','invalidated','suspended','stale')
MAX_ASSUMPTIONS=64


def _path(ledger_id:str,runtime_root=None)->Path:
    return evidence_root('assumption_ledger',runtime_root)/'records'/f'{ledger_id}.json'

def _digests(values:Iterable[Any],limit:int=32)->list[str]:
    return sorted({str(v) for v in values if str(v)})[:limit]

def _make_assumption(raw:Mapping[str,Any],manifest:str)->dict[str,Any]:
    code=str(raw.get('code') or raw.get('assumption_code') or '').strip()[:96]
    if not code:raise ValueError('assumption_code_required')
    statement=str(raw.get('statement') or '').strip()
    statement_digest=str(raw.get('statement_digest') or '') or (digest(statement) if statement else '')
    if not statement_digest:raise ValueError('assumption_statement_or_digest_required')
    confidence=max(0.0,min(1.0,float(raw.get('confidence',0.5))))
    evidence=_digests(raw.get('evidence_digests') or ())
    method=str(raw.get('validation_method') or raw.get('validation_method_code') or 'unassigned').strip()[:96]
    invalidation=[digest(str(x)) for x in raw.get('invalidation_conditions') or () if str(x).strip()]
    invalidation+=_digests(raw.get('invalidation_condition_digests') or ())
    row={'assumption_code':code,'statement_digest':statement_digest,'status':'active','confidence':round(confidence,3),
         'evidence_digests':evidence,'validation_method_code':method,'invalidation_condition_digests':sorted(set(invalidation))[:32],
         'source_manifest_digest':manifest,'revision':1,'content_free':True,'raw_statement_persisted':False}
    row['assumption_digest']=digest(row);return row

def create_assumption_ledger(*,goal_digest:str,workspace_digest:str,source_manifest_digest:str,assumptions:Iterable[Mapping[str,Any]],runtime_root=None)->dict[str,Any]:
    goal=str(goal_digest or '');workspace=str(workspace_digest or '');manifest=str(source_manifest_digest or '')
    if not goal or not workspace or not manifest:raise ValueError('planning_lineage_required')
    rows=[];seen=set()
    for raw in list(assumptions)[:MAX_ASSUMPTIONS]:
        a=_make_assumption(raw,manifest)
        if a['assumption_code'] in seen:raise ValueError('duplicate_assumption_code')
        seen.add(a['assumption_code']);rows.append(a)
    if not rows:raise ValueError('assumption_required')
    ledger_id='assumptions_'+digest({'goal':goal,'workspace':workspace,'manifest':manifest,'rows':[x['assumption_digest'] for x in rows]})[:24]
    row=seal({'contract_version':CONTRACT_VERSION,'ledger_id':ledger_id,'goal_digest':goal,'workspace_digest':workspace,'source_manifest_digest':manifest,
              'assumptions':rows,'assumption_count':len(rows),'revision_count':0,'previous_ledger_digest':'','raw_statement_persisted':False,
              'action_executed':False,**PLANNING_DENIED_AUTHORITY})
    atomic_json(_path(ledger_id,runtime_root),row)
    return {'ok':True,'status':'assumption_ledger_ready','assumption_ledger':public_assumption_ledger(row),'action_executed':False,**PLANNING_DENIED_AUTHORITY}

def revise_assumption(ledger:Mapping[str,Any],*,assumption_code:str,outcome:str,evidence_digests:Iterable[str]=(),confidence:float|None=None,validation_method:str='',reason:str='',runtime_root=None)->dict[str,Any]:
    if outcome not in {'validated','invalidated','suspended'}:raise ValueError('assumption_outcome_invalid')
    code=str(assumption_code or '').strip();items=[dict(x) for x in ledger.get('assumptions') or []]
    target=next((x for x in items if x.get('assumption_code')==code),None)
    if target is None:raise ValueError('assumption_not_found')
    old_ledger_digest=str(ledger.get('record_digest') or digest(dict(ledger)))
    updated=[]
    for x in items:
        if x.get('assumption_code')!=code:updated.append(x);continue
        y=dict(x);y['status']=outcome;y['evidence_digests']=sorted(set(y.get('evidence_digests') or [])|set(_digests(evidence_digests)))
        if confidence is not None:y['confidence']=round(max(0.0,min(1.0,float(confidence))),3)
        if validation_method:y['validation_method_code']=str(validation_method)[:96]
        y['revision']=int(y.get('revision') or 1)+1;y['revision_reason_digest']=digest(str(reason or outcome));y['assumption_digest']=digest({k:v for k,v in y.items() if k!='assumption_digest'});updated.append(y)
    new_id='assumptions_'+digest({'previous':old_ledger_digest,'code':code,'outcome':outcome,'rows':[x['assumption_digest'] for x in updated]})[:24]
    row=seal({'contract_version':CONTRACT_VERSION,'ledger_id':new_id,'goal_digest':ledger.get('goal_digest'),'workspace_digest':ledger.get('workspace_digest'),
              'source_manifest_digest':ledger.get('source_manifest_digest'),'assumptions':updated,'assumption_count':len(updated),
              'revision_count':int(ledger.get('revision_count') or 0)+1,'previous_ledger_digest':old_ledger_digest,'raw_statement_persisted':False,
              'action_executed':False,**PLANNING_DENIED_AUTHORITY})
    atomic_json(_path(new_id,runtime_root),row)
    return {'ok':True,'status':'assumption_revised','assumption_ledger':public_assumption_ledger(row),'action_executed':False,**PLANNING_DENIED_AUTHORITY}

def public_assumption_ledger(row:Mapping[str,Any])->dict[str,Any]:
    return {'contract_version':CONTRACT_VERSION,'ledger_id':row.get('ledger_id'),'goal_digest':row.get('goal_digest'),'workspace_digest':row.get('workspace_digest'),
            'source_manifest_digest':row.get('source_manifest_digest'),'assumption_count':int(row.get('assumption_count') or 0),'revision_count':int(row.get('revision_count') or 0),
            'previous_ledger_digest':row.get('previous_ledger_digest') or '','assumptions':[{'assumption_code':x.get('assumption_code'),'status':x.get('status'),'confidence':x.get('confidence'),
              'evidence_count':len(x.get('evidence_digests') or []),'validation_method_code':x.get('validation_method_code'),'invalidation_condition_count':len(x.get('invalidation_condition_digests') or []),'revision':x.get('revision')} for x in row.get('assumptions') or []],
            'raw_statement_persisted':False,'read_only':True,'action_executed':False,**PLANNING_DENIED_AUTHORITY}

def load_assumption_ledger(ledger_id:str,*,runtime_root=None,include_private:bool=False)->dict[str,Any]:
    row=read_json(_path(str(ledger_id),runtime_root));
    if not row or not valid(row):return {}
    return row if include_private else public_assumption_ledger(row)

def assess_assumption_freshness(ledger:Mapping[str,Any],*,source_manifest_digest:str)->dict[str,Any]:
    current=str(ledger.get('source_manifest_digest') or '')==str(source_manifest_digest or '')
    return {'ok':True,'status':'current' if current else 'stale','current':current,'stale_assumption_count':0 if current else int(ledger.get('assumption_count') or 0),'action_executed':False,**PLANNING_DENIED_AUTHORITY}

def process_assumption_ledger_control(text:str,*,goal=None,project_understanding=None,assumptions=None,runtime_root=None,**_)->dict[str,Any]:
    if str(text or '').strip().lower() not in {'show assumption ledger','inspect assumption ledger'}:return {'active':False}
    if not goal:return {'active':True,'ok':False,'status':'planning_goal_required','action_executed':False,**PLANNING_DENIED_AUTHORITY}
    if not project_understanding:return {'active':True,'ok':False,'status':'project_understanding_required','action_executed':False,**PLANNING_DENIED_AUTHORITY}
    if not assumptions:return {'active':True,'ok':False,'status':'planning_assumptions_required','action_executed':False,**PLANNING_DENIED_AUTHORITY}
    return {'active':True,**create_assumption_ledger(goal_digest=goal.get('goal_digest'),workspace_digest=project_understanding.get('workspace_digest'),source_manifest_digest=project_understanding.get('source_manifest_digest'),assumptions=assumptions,runtime_root=runtime_root)}

__all__=['CONTRACT_VERSION','STATUSES','create_assumption_ledger','revise_assumption','public_assumption_ledger','load_assumption_ledger','assess_assumption_freshness','process_assumption_ledger_control']
