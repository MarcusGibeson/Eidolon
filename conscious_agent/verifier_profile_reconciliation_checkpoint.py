from __future__ import annotations
"""Read-only v1193.5 deterministic profile and budget reconciliation checkpoint."""
import hashlib, os
from pathlib import Path
from typing import Any
from verifier_profile_reconciliation import create_profile_result, reconcile_profile, public_profile_summary
from checkpoint_registry import inspect_checkpoint_registry
from package_integrity import package_privacy_summary_for_root
CONTRACT_VERSION="v1193.5";_CHECKPOINT_ID="verifier-profile-reconciliation:v1193.5"
_LIMITATIONS=("Profiles are reconciled from supplied content-free results; suites are not executed.","Historical debt remains separate and unresolved.","Fixture consolidation and global profile performance repair are deferred.","No verifier retirement or fixture deletion occurs.","Desktop Codex and native-provider review remain deferred until v1200.")
def _tree(root:Path):
 h=hashlib.sha256();n=0
 for base,dirs,files in os.walk(root):
  dirs[:]=[d for d in dirs if d not in {'data','sandbox','.git','.venv','venv','__pycache__','.pytest_cache','dist','build','reports'}]
  for name in sorted(files):
   p=Path(base)/name
   if p.suffix.lower() in {'.pyc','.pyo'}:continue
   try:b=p.read_bytes();rel=p.relative_to(root).as_posix()
   except OSError:continue
   n+=1;h.update(rel.encode());h.update(b'\0');h.update(hashlib.sha256(b).digest())
 return h.hexdigest(),n
def _rows(profile:str):
 base=(('v1193-focused','current_regression',65,65,30,12100,'passed',''),('v1192-checkpoint','retained_checkpoint',383,383,180,74200,'passed',''),('v1191-checkpoint','retained_checkpoint',176,176,120,33200,'passed',''),('v1190-checkpoint','retained_checkpoint',82,82,90,19400,'passed',''),('historical-fixtures','historical_debt',24,0,420,401000,'blocked','historical-checkpoints'))
 chosen=base[:1] if profile=='focused' else base
 return [create_profile_result(verifier_id=a,classification=b,profile=profile,sequence=i,expected_checks=c,actual_checks=d,budget_seconds=e,elapsed_milliseconds=f,outcome=g,debt_group=h) for i,(a,b,c,d,e,f,g,h) in enumerate(chosen)]
def build_verifier_profile_reconciliation_checkpoint(*,source_root:str|Path|None=None,runtime_root:str|Path|None=None)->dict[str,Any]:
 source=Path(source_root or Path(__file__).resolve().parents[1]).resolve();del runtime_root
 before,count=_tree(source);checks=[];req=lambda v:checks.append(bool(v))
 reports={}
 for profile,budget in [('focused',30),('quick',840),('full',870)]:
  rows=_rows(profile);expected=[r['verifier_id'] for r in rows];reports[profile]=reconcile_profile(profile=profile,expected_verifiers=expected,results=rows,profile_budget_seconds=budget)
 focused=public_profile_summary(reports['focused']);quick=public_profile_summary(reports['quick']);full=public_profile_summary(reports['full'])
 for v in (focused['global_profile_pass'] is True,quick['current_regressions_passed'] is True,quick['global_profile_pass'] is False,quick['inherited_nonpass_count']==1,full['historical_debt_separate'] is True,full['within_profile_budget'] is True):req(v)
 blocked={}
 good=_rows('quick');expected=[r['verifier_id'] for r in good]
 def case(name,rows=None,exp=None,budget=840,profile='quick'):
  blocked[name]=reconcile_profile(profile=profile,expected_verifiers=expected if exp is None else exp,results=good if rows is None else rows,profile_budget_seconds=budget)
 bad=[dict(r) for r in good];bad[1]['elapsed_milliseconds']=999;case('tamper',bad)
 bad=[dict(r) for r in good];bad[1]['prompt']='x';case('private-field',bad)
 bad=[dict(r) for r in good];bad[1]['authority_state']='granted';case('authority',bad)
 case('order-mismatch',exp=list(reversed(expected)));case('duplicate-expected',exp=expected+[expected[-1]]);case('mixed-profile',rows=_rows('full'));case('invalid-budget',budget=0)
 for value in blocked.values():req(value.get('status')=='blocked');req(bool(value.get('errors')));req(value.get('execution_invoked') is False);req(value.get('authority_granted') is False)
 registry=inspect_checkpoint_registry(source_root=source);req(any(r.get('checkpoint_id')=='verifier-profile-reconciliation-checkpoint' for r in registry.get('checkpoints',[])))
 privacy=package_privacy_summary_for_root(source);req(privacy.get('ok') is True)
 after,after_count=_tree(source);req(before==after);req(count==after_count)
 return {'ok':all(checks),'passed':sum(checks),'total':len(checks),'contract_version':CONTRACT_VERSION,'checkpoint_id':_CHECKPOINT_ID,'read_only':True,'post_available':False,'content_free':True,'summaries':{'focused':focused,'quick':quick,'full':full},'blocked_cases':{k:v.get('errors',[]) for k,v in blocked.items()},'limitations':list(_LIMITATIONS),'source_unchanged':before==after,'source_file_count':count,'runtime_mutated':False,'production_source_modified':False,'fixture_deleted':False,'verifier_retired':False,'global_profile_pass_claimed':False,'provider_contacted':False,'model_contacted':False,'thread_started':False,'process_started':False,'execution_invoked':False,'approval_consumed':False,'authority_granted':False}
