from __future__ import annotations
"""v1353 deterministic declarative unit/contract test generation."""
import hashlib, json, re
from pathlib import Path
from typing import Any, Mapping, Sequence
CONTRACT_VERSION='v1353.8'
DENIED={'test_execution_authorized':False,'source_mutation_authorized':False,'provider_contact_authorized':False,'network_authorized':False,'release_authorized':False,'approval_granted':False,'independent_authority_granted':False}
KINDS={'invariant','schema','lifecycle','api'}
def _d(v:object)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True,default=str).encode()).hexdigest()
def _root(r=None)->Path:
 p=Path(r or '.').resolve()/'phase6_unit_contract_tests';p.mkdir(parents=True,exist_ok=True);return p
def _safe(v:str)->bool:return bool(re.fullmatch(r'[A-Za-z0-9_.:/-]{1,120}',v))
def _case_templates(kind:str)->tuple[tuple[str,str],...]:
 return {
  'invariant':(('holds_for_valid_input','pass'),('rejects_invalid_state','reject')),
  'schema':(('accepts_valid_shape','pass'),('rejects_missing_required','reject'),('rejects_wrong_type','reject')),
  'lifecycle':(('allows_declared_transition','pass'),('rejects_undeclared_transition','reject'),('preserves_idempotent_terminal','pass')),
  'api':(('accepts_declared_signature','pass'),('rejects_breaking_signature','reject'),('preserves_declared_result_contract','pass')),
 }[kind]
def build_unit_contract_test_plan(*,source_manifest_digest:str,contracts:Sequence[Mapping[str,Any]],runtime_root=None)->dict[str,Any]:
 if not re.fullmatch(r'[a-f0-9]{64}',str(source_manifest_digest or '')):return {'ok':False,'status':'unit_contract_source_lineage_required','action_executed':False,**DENIED}
 if not contracts or len(contracts)>256:return {'ok':False,'status':'unit_contract_count_invalid','action_executed':False,**DENIED}
 rows=[];cases=[];seen=set()
 for raw in contracts:
  cid=str(raw.get('contract_id') or '');kind=str(raw.get('kind') or '').lower();evidence=str(raw.get('evidence_digest') or '')
  if not _safe(cid) or cid in seen or kind not in KINDS or not re.fullmatch(r'[a-f0-9]{64}',evidence):return {'ok':False,'status':'unit_contract_definition_invalid','action_executed':False,**DENIED}
  seen.add(cid);cid_d=_d(cid);case_ids=[]
  for suffix,expectation in _case_templates(kind):
   case_id=f'{cid}:{suffix}';case={'case_id_digest':_d(case_id),'contract_id_digest':cid_d,'kind':kind,'expectation':expectation,'deterministic':True,'generated_code':False};cases.append(case);case_ids.append(case['case_id_digest'])
  rows.append({'contract_id_digest':cid_d,'kind':kind,'evidence_digest':evidence,'case_count':len(case_ids),'case_id_digests':case_ids})
 rec={'contract_version':CONTRACT_VERSION,'source_manifest_digest':source_manifest_digest,'contract_count':len(rows),'case_count':len(cases),'kinds_present':sorted({r['kind'] for r in rows}),'contracts':rows,'cases':cases,'deterministic':True,'generated_code':False,'content_free':True,'action_executed':False,**DENIED};rec['record_digest']=_d(rec);pid='uct_'+rec['record_digest'][:24];(_root(runtime_root)/(pid+'.json')).write_text(json.dumps(rec,sort_keys=True),encoding='utf-8');return {'ok':True,'status':'unit_contract_test_plan_ready','unit_contract_test_plan_id':pid,'unit_contract_test_plan':rec,'action_executed':False,**DENIED}
def load_unit_contract_test_plan(i:str,*,runtime_root=None)->dict[str,Any]:
 if not re.fullmatch(r'uct_[a-f0-9]{24}',str(i or '')):return {}
 p=_root(runtime_root)/(i+'.json')
 if not p.is_file():return {}
 try:r=json.loads(p.read_text(encoding='utf-8'))
 except Exception:return {}
 d=r.pop('record_digest',None)
 if d!=_d(r):return {}
 r['record_digest']=d;return r
def process_unit_contract_test_control(text:str,*,project_state=None,runtime_root=None,**_):
 if str(text or '').strip().lower() not in {'show unit contract tests','inspect unit contract tests','show generated contract tests'}:return {'active':False}
 i=str((project_state or {}).get('unit_contract_test_plan_id') or '');r=load_unit_contract_test_plan(i,runtime_root=runtime_root) if i else {};return {'active':True,'ok':bool(r),'status':'unit_contract_test_plan_found' if r else 'unit_contract_test_plan_missing','unit_contract_test_plan':r,'action_executed':False,**DENIED}
