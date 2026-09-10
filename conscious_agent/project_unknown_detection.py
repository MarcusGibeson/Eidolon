from __future__ import annotations
"""v1319 calibrated unknown/stale/contradictory project-knowledge detection."""
from pathlib import Path
from project_evidence_store import *
from architecture_summaries import build_architecture_summaries,load_architecture_summaries
from change_history_understanding import build_change_history_understanding
CONTRACT_VERSION='v1319.8';STATES=('observed','inferred','assumed','unverified','stale','contradicted','suspended');CAP={'observed':0.95,'inferred':0.75,'assumed':0.45,'unverified':0.25,'stale':0.30,'contradicted':0.20,'suspended':0.10}
def _path(wid,runtime_root=None):return evidence_root('project_unknowns',runtime_root)/'records'/f'{wid}.json'
def make_claim(code,state,evidence_digests=(),confidence=None):
 if state not in STATES:raise ValueError('claim_state_invalid')
 ed=sorted({str(x) for x in evidence_digests if str(x)});c=CAP[state] if confidence is None else min(CAP[state],max(0.0,float(confidence)));return {'claim_code':str(code),'state':state,'confidence':round(c,3),'evidence_digests':ed,'unknown_is_false':False,'content_free':True}
def reconcile_claims(claims):
 out=[];by={}
 for raw in claims:
  c=dict(raw);code=str(c.get('claim_code') or '');
  if not code:continue
  if code in by and by[code].get('state')!=c.get('state'):
   prev=by[code];prev['state']='contradicted';prev['confidence']=CAP['contradicted'];prev['evidence_digests']=sorted(set(prev.get('evidence_digests',[]))|set(c.get('evidence_digests',[])))
  else:by[code]=c
 return list(by.values())
def build_project_unknown_detection(source_root:str|Path,*,runtime_root=None,now_unix:int|None=None):
 root=Path(source_root).resolve();ap=build_architecture_summaries(root,runtime_root=runtime_root,now_unix=now_unix)['architecture_summaries'];wid=ap['workspace_digest'];hist=build_change_history_understanding(root,runtime_root=runtime_root,now_unix=now_unix)['change_history'];claims=[make_claim('source_manifest_current','observed',[ap['source_manifest_digest']]),make_claim('architecture_explained','inferred',[digest(ap)]),make_claim('live_runtime_matches_source','unverified',[]),make_claim('measured_test_coverage_complete','unverified',[]),make_claim('historical_intent_fully_known','inferred' if hist.get('evidence_count') else 'unverified',[digest(hist)] if hist.get('evidence_count') else [])]
 row=seal({'contract_version':CONTRACT_VERSION,'workspace_digest':wid,'source_manifest_digest':ap['source_manifest_digest'],'claims':claims,'claim_count':len(claims),'unknown_count':sum(c['state'] in {'unverified','stale','contradicted','suspended'} for c in claims),'unknown_is_false':False,'guesses_resolved_as_facts':False,'action_executed':False,**DENIED_AUTHORITY});atomic_json(_path(wid,runtime_root),row);return {'ok':True,'status':'project_unknowns_ready','project_unknowns':public_project_unknowns(row),'action_executed':False,**DENIED_AUTHORITY}
def public_project_unknowns(row):return {'contract_version':CONTRACT_VERSION,'workspace_digest':row.get('workspace_digest'),'source_manifest_digest':row.get('source_manifest_digest'),'claim_count':int(row.get('claim_count',0)),'unknown_count':int(row.get('unknown_count',0)),'claim_states':[{'claim_code':c.get('claim_code'),'state':c.get('state'),'confidence':c.get('confidence')} for c in row.get('claims') or []],'unknown_is_false':False,'guesses_resolved_as_facts':False,'read_only':True,'action_executed':False,**DENIED_AUTHORITY}
def load_project_unknowns(wid,*,runtime_root=None,include_private=False):
 row=read_json(_path(wid,runtime_root));return (row if include_private else public_project_unknowns(row)) if row and valid(row) else {}
def mark_claims_stale(wid,*,runtime_root=None):
 row=load_project_unknowns(wid,runtime_root=runtime_root,include_private=True)
 if not row:return {}
 row['claims']=[{**c,'state':'stale','confidence':min(float(c.get('confidence',0)),CAP['stale'])} for c in row.get('claims') or []];row['unknown_count']=len(row['claims']);row=seal({k:v for k,v in row.items() if k!='record_digest'});atomic_json(_path(wid,runtime_root),row);return public_project_unknowns(row)
def process_project_unknown_control(text:str,*,project_root=None,runtime_root=None):
 if str(text or '').strip().lower() not in {'inspect project unknowns','show project unknowns'}:return {'active':False}
 if not project_root:return {'active':True,'ok':False,'status':'project_root_required','action_executed':False,**DENIED_AUTHORITY}
 return {'active':True,**build_project_unknown_detection(project_root,runtime_root=runtime_root)}
__all__=['CONTRACT_VERSION','STATES','CAP','make_claim','reconcile_claims','build_project_unknown_detection','load_project_unknowns','mark_claims_stale','process_project_unknown_control']
