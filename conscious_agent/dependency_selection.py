from __future__ import annotations
"""v1348 offline dependency-selection judgment with content-minimized evidence."""
import hashlib,json,re,time
from pathlib import Path
from typing import Any,Mapping,Sequence
from cognitive_coding_foundations import DENIED_AUTHORITY,digest
from ordinary_chat_development_campaign import _atomic_json,_read_json,_store_root
CONTRACT_VERSION='v1348.8';MAX_EVIDENCE_AGE_DAYS=3650
DEPENDENCY_DENIED_AUTHORITY={**DENIED_AUTHORITY,'network_authorized':False,'dependency_installation_authorized':False,'lockfile_mutation_authorized':False,'source_mutation_authorized':False,'source_application_authorized':False,'package_publication_authorized':False,'installation_authorized':False,'promotion_authorized':False,'release_authorized':False,'independent_authority_granted':False}
def _root(runtime_root=None):return _store_root(runtime_root)/'phase5_dependency_selection'
def _path(op,runtime_root=None):
 if not re.fullmatch(r'depsel_[a-f0-9]{24}',str(op or '')):raise ValueError('invalid_dependency_selection_id')
 return _root(runtime_root)/'records'/f'{op}.json'
def _load(op,runtime_root=None):
 row=_read_json(_path(op,runtime_root));return row if row and row.get('record_digest')==digest({k:v for k,v in row.items() if k!='record_digest'}) else {}
def _save(row,runtime_root=None):row.pop('record_digest',None);row['record_digest']=digest(row);_atomic_json(_path(row['dependency_selection_id'],runtime_root),row);return row

def inspect_dependency_context(source_root:str|Path)->dict[str,Any]:
 root=Path(source_root).resolve(strict=True);files=[]
 for name in ('pyproject.toml','requirements.txt','requirements-dev.txt','package.json','package-lock.json','pnpm-lock.yaml','yarn.lock','Pipfile','poetry.lock'):
  p=root/name
  if p.is_file() and p.stat().st_size<=2*1024*1024:files.append(p)
 out={'contract_version':CONTRACT_VERSION,'dependency_metadata_file_count':len(files),'dependency_context_digest':digest([(p.relative_to(root).as_posix(),hashlib.sha256(p.read_bytes()).hexdigest()) for p in files]),'inspection_only':True,'registry_contacted':False,'dependency_installed':False,**DEPENDENCY_DENIED_AUTHORITY};out['inspection_digest']=digest(out);return out
def _candidate_digest(c:Mapping[str,Any])->str:
 safe={k:c.get(k) for k in ('version','existing','license','security_status','maintenance_age_days','footprint_kb','platforms','offline_ready','capability_score','provenance_verified','evidence_age_days')};return digest(safe)
def evaluate_dependency_candidates(candidates:Sequence[Mapping[str,Any]],*,target_platform:str='windows',allowed_licenses:Sequence[str]=('MIT','BSD-3-Clause','Apache-2.0','PSF-2.0'),max_footprint_kb:int=250000,min_capability_score:float=.75,max_evidence_age_days:int=180)->dict[str,Any]:
 rows=[]
 for c in candidates:
  reasons=[];lic=str(c.get('license') or 'unknown');security=str(c.get('security_status') or 'unknown');platforms={str(x).lower() for x in (c.get('platforms') or [])};eage=int(c.get('evidence_age_days',999999));mage=int(c.get('maintenance_age_days',999999));foot=int(c.get('footprint_kb',999999999));score=float(c.get('capability_score',0.0));existing=bool(c.get('existing'));offline=bool(c.get('offline_ready'));prov=bool(c.get('provenance_verified'))
  if not prov:reasons.append('provenance_unverified')
  if lic not in set(allowed_licenses):reasons.append('license_unacceptable_or_unknown')
  if security!='clear':reasons.append('security_state_not_clear')
  if eage<0 or eage>max_evidence_age_days:reasons.append('evidence_stale')
  if mage<0 or mage>MAX_EVIDENCE_AGE_DAYS:reasons.append('maintenance_state_unacceptable')
  if foot<0 or foot>max_footprint_kb:reasons.append('footprint_budget_exceeded')
  if target_platform.lower() not in platforms:reasons.append('target_platform_unverified')
  if not offline:reasons.append('offline_suitability_unverified')
  if score<min_capability_score:reasons.append('capability_fit_insufficient')
  viable=not reasons;rank=(1 if existing else 0,score,-foot,-mage) if viable else (-1,0,0,0)
  rows.append({'candidate_digest':_candidate_digest(c),'existing':existing,'viable':viable,'reasons':reasons,'rank':rank,'evidence_digest':str(c.get('evidence_digest') or digest({'candidate':_candidate_digest(c),'age':eage}))})
 viable=[r for r in rows if r['viable']];chosen=max(viable,key=lambda r:r['rank']) if viable else None
 out={'contract_version':CONTRACT_VERSION,'candidate_count':len(rows),'viable_candidate_count':len(viable),'selected_candidate_digest':chosen['candidate_digest'] if chosen else '','selected_existing_dependency':bool(chosen and chosen['existing']),'selection_status':'selected_existing_dependency' if chosen and chosen['existing'] else ('selected_candidate' if chosen else 'no_viable_candidate'),'rejected_reason_counts':{reason:sum(reason in r['reasons'] for r in rows) for reason in sorted({x for r in rows for x in r['reasons']})},'candidate_evidence_digest':digest([(r['candidate_digest'],r['evidence_digest'],r['viable'],r['reasons']) for r in rows]),'inspection_only':True,'registry_contacted':False,'dependency_installed':False,**DEPENDENCY_DENIED_AUTHORITY};out['evaluation_digest']=digest(out);return out
def create_dependency_selection(*,candidates:Sequence[Mapping[str,Any]],source_workspace_digest:str,target_platform:str='windows',runtime_root=None,**constraints)->dict[str,Any]:
 evaluation=evaluate_dependency_candidates(candidates,target_platform=target_platform,**constraints);spec={'contract':CONTRACT_VERSION,'source':source_workspace_digest,'target':target_platform,'evaluation':evaluation['evaluation_digest']};op='depsel_'+digest(spec)[:24];existing=_load(op,runtime_root)
 if existing:return {'ok':existing.get('selection_status')!='no_viable_candidate','status':'dependency_selection_already_exists','dependency_selection':public_dependency_selection(existing),'action_executed':False,**DEPENDENCY_DENIED_AUTHORITY}
 row={'contract_version':CONTRACT_VERSION,'dependency_selection_id':op,'source_workspace_digest':source_workspace_digest,'target_platform':target_platform,'selection_status':evaluation['selection_status'],'candidate_count':evaluation['candidate_count'],'viable_candidate_count':evaluation['viable_candidate_count'],'selected_candidate_digest':evaluation['selected_candidate_digest'],'selected_existing_dependency':evaluation['selected_existing_dependency'],'candidate_evidence_digest':evaluation['candidate_evidence_digest'],'evaluation_digest':evaluation['evaluation_digest'],'rejected_reason_counts':evaluation['rejected_reason_counts'],'action_executed':False,**DEPENDENCY_DENIED_AUTHORITY};_save(row,runtime_root);ok=row['selection_status']!='no_viable_candidate';return {'ok':ok,'status':'dependency_candidate_selected' if ok else 'dependency_selection_blocked','dependency_selection':public_dependency_selection(row),'action_executed':False,**DEPENDENCY_DENIED_AUTHORITY}
def public_dependency_selection(row:Mapping[str,Any])->dict[str,Any]:
 if not row:return {}
 return {k:row.get(k) for k in ('contract_version','dependency_selection_id','source_workspace_digest','target_platform','selection_status','candidate_count','viable_candidate_count','selected_candidate_digest','selected_existing_dependency','candidate_evidence_digest','evaluation_digest','rejected_reason_counts','action_executed')}|{'raw_candidate_name_exposed':False,'registry_contacted':False,'dependency_installed':False,**DEPENDENCY_DENIED_AUTHORITY}
def load_dependency_selection(op:str,*,runtime_root=None):return public_dependency_selection(_load(op,runtime_root))
def process_dependency_selection_control(text:str,*,project_state=None,runtime_root=None,**_):
 if str(text or '').strip().lower() not in {'show dependency selection','inspect dependency selection','show dependency evaluation'}:return {'active':False}
 op=str((project_state or {}).get('dependency_selection_id') or '');row=load_dependency_selection(op,runtime_root=runtime_root) if op else {};return {'active':True,'ok':bool(row),'status':'dependency_selection_found' if row else 'dependency_selection_missing','dependency_selection':row,'action_executed':False,**DEPENDENCY_DENIED_AUTHORITY}
