from __future__ import annotations
"""v1352 smallest-sufficient deterministic test selection with risk broadening."""
import hashlib,json,re
from pathlib import Path
from typing import Any,Mapping,Sequence
CONTRACT_VERSION='v1352.8';DENIED={'test_execution_authorized':False,'source_mutation_authorized':False,'provider_contact_authorized':False,'network_authorized':False,'release_authorized':False,'approval_granted':False,'independent_authority_granted':False}
def _d(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True,default=str).encode()).hexdigest()
def _root(r=None):p=Path(r or '.').resolve()/'phase6_test_selection';p.mkdir(parents=True,exist_ok=True);return p
def build_test_selection(*,source_manifest_digest:str,requirement_digests:Sequence[str],candidate_tests:Sequence[Mapping[str,Any]],shared_behavior:bool=False,authority_sensitive:bool=False,runtime_root=None)->dict[str,Any]:
 if not re.fullmatch(r'[a-f0-9]{64}',str(source_manifest_digest or '')):return {'ok':False,'status':'test_selection_source_lineage_required','action_executed':False,**DENIED}
 targets=sorted(set(str(x) for x in requirement_digests if re.fullmatch(r'[a-f0-9]{64}',str(x))))
 if not targets:return {'ok':False,'status':'test_selection_targets_required','action_executed':False,**DENIED}
 rows=[]
 for raw in candidate_tests:
  tid=str(raw.get('test_id') or '');covers=sorted(set(str(x) for x in raw.get('covers') or [] if str(x) in targets));cost=max(1,int(raw.get('cost') or 1))
  if re.fullmatch(r'[A-Za-z0-9_.:/-]{1,120}',tid) and covers:rows.append({'test_id':tid,'test_id_digest':_d(tid),'covers':covers,'cost':cost,'shared':bool(raw.get('shared')),'authority_sensitive':bool(raw.get('authority_sensitive'))})
 uncovered=set(targets);selected=[]
 while uncovered:
  options=[]
  for r in rows:
   gain=len(uncovered.intersection(r['covers']))
   if gain:options.append((-gain,r['cost']/gain,r['cost'],r['test_id'],r))
  if not options:break
  pick=min(options)[-1];selected.append(pick);uncovered-=set(pick['covers'])
 broaden=[]
 if shared_behavior:
  broaden=[r for r in rows if r['shared'] and r not in selected]
 if authority_sensitive:
  broaden += [r for r in rows if r['authority_sensitive'] and r not in selected and r not in broaden]
 final=selected+sorted(broaden,key=lambda r:r['test_id']);coverage_complete=not uncovered
 rec={'contract_version':CONTRACT_VERSION,'source_manifest_digest':source_manifest_digest,'target_count':len(targets),'coverage_complete':coverage_complete,'uncovered_requirement_digests':sorted(uncovered),'selected_test_digests':[r['test_id_digest'] for r in final],'selected_test_count':len(final),'focused_test_count':len(selected),'broadening_test_count':len(final)-len(selected),'shared_behavior_broadening':shared_behavior,'authority_sensitive_broadening':authority_sensitive,'estimated_cost':sum(r['cost'] for r in final),'selection_executes_tests':False,'action_executed':False,'content_free':True,**DENIED};rec['record_digest']=_d(rec);sid='tsel_'+rec['record_digest'][:24];(_root(runtime_root)/(sid+'.json')).write_text(json.dumps(rec,sort_keys=True),encoding='utf-8');return {'ok':coverage_complete,'status':'test_selection_complete' if coverage_complete else 'test_selection_incomplete','test_selection_id':sid,'test_selection':rec,'action_executed':False,**DENIED}
def load_test_selection(i:str,*,runtime_root=None):
 if not re.fullmatch(r'tsel_[a-f0-9]{24}',str(i or '')):return {}
 p=_root(runtime_root)/(i+'.json');
 if not p.is_file():return {}
 try:r=json.loads(p.read_text())
 except Exception:return {}
 d=r.pop('record_digest',None)
 if d!=_d(r):return {}
 r['record_digest']=d;return r
def process_test_selection_control(text:str,*,project_state=None,runtime_root=None,**_):
 if str(text or '').strip().lower() not in {'show test selection','inspect test selection','show verification tests'}:return {'active':False}
 i=str((project_state or {}).get('test_selection_id') or '');r=load_test_selection(i,runtime_root=runtime_root) if i else {};return {'active':True,'ok':bool(r),'status':'test_selection_found' if r else 'test_selection_missing','test_selection':r,'action_executed':False,**DENIED}
