from __future__ import annotations
"""Read-only v1193.2 Verifier Ownership and Historical-Debt Foundations checkpoint."""
import hashlib, os
from pathlib import Path
from typing import Any
from verifier_ownership import create_verifier_record, build_ownership_registry, public_ownership_summary
from checkpoint_registry import inspect_checkpoint_registry
from package_integrity import package_privacy_summary_for_root
CONTRACT_VERSION="v1193.2"; _CHECKPOINT_ID="verifier-ownership:v1193.2"
_LIMITATIONS=("Ownership is source-declared and content-free.","Historical debt is classified, not yet removed.","Quick/full profile execution and budget reconciliation are deferred.","No fixture deletion or verifier retirement occurs.","Desktop Codex and native-provider review remain deferred until v1200.")
def _tree(root:Path):
 h=hashlib.sha256();n=0
 for base,dirs,files in os.walk(root):
  dirs[:]=[d for d in dirs if d not in {'data','sandbox','.git','.venv','venv','__pycache__','.pytest_cache','dist','build','reports'}]
  for name in sorted(files):
   p=Path(base)/name
   if p.suffix.lower() in {'.pyc','.pyo'}: continue
   try:b=p.read_bytes();rel=p.relative_to(root).as_posix()
   except OSError:continue
   n+=1;h.update(rel.encode());h.update(b'\0');h.update(hashlib.sha256(b).digest())
 return h.hexdigest(),n

def _records():
 specs=(
 ('v1193-focused','release','current_regression','tools/v1193_0_2_verifier_ownership_tests.py','1193.2','verifier-ownership',60,30,('focused','quick','full'),'','low'),
 ('v1192-checkpoint','cognition','retained_checkpoint','tools/v1192_9_evidence_compaction_checkpoint_tests.py','1192.9','evidence-compaction',383,180,('quick','full'),'','low'),
 ('v1191-checkpoint','runtime','retained_checkpoint','tools/v1191_9_responsiveness_background_work_checkpoint_tests.py','1191.9','responsiveness',176,120,('quick','full'),'','low'),
 ('v1190-checkpoint','conversation','retained_checkpoint','tools/v1190_9_unified_experience_checkpoint_tests.py','1190.9','unified-experience',82,90,('quick','full'),'','low'),
 ('historical-fixtures','platform','historical_debt','tools/release_verify.py','1180-1189','historical-checkpoints',24,420,('quick','full'),'v1190.9 quick review','high'),
 ('cleanup-prefix','release','historical_debt','tools/release_verify.py#cleanup','1190.9','profile-cleanup',1,30,('full',),'v1190.9 final profile','medium'),
 )
 return [create_verifier_record(verifier_id=a,owner=b,classification=c,suite_path=d,source_version=e,fixture_group=f,expected_checks=g,budget_seconds=h,profile_membership=i,inherited_from=j,debt_severity=k) for a,b,c,d,e,f,g,h,i,j,k in specs]

def build_verifier_ownership_checkpoint(*,source_root:str|Path|None=None,runtime_root:str|Path|None=None)->dict[str,Any]:
 source=Path(source_root or Path(__file__).resolve().parents[1]).resolve(); del runtime_root
 before,count=_tree(source); checks=[]; req=lambda v:checks.append(bool(v))
 records=_records(); report=build_ownership_registry(records); summary=public_ownership_summary(report)
 for value in (report.get('status')=='registered',summary.get('record_count')==6,summary.get('owner_count')==5,summary.get('current_regression_count')==1,summary.get('retained_checkpoint_count')==3,summary.get('historical_debt_count')==2,summary.get('debt_separated') is True,summary.get('profile_budgets_seconds',{}).get('focused')==30,summary.get('profile_budgets_seconds',{}).get('quick')==840,summary.get('profile_budgets_seconds',{}).get('full')==870):req(value)
 blocked={}
 def case(name,mutate):
  rows=[dict(r) for r in records]; mutate(rows); blocked[name]=build_ownership_registry(rows)
 def resign(r):
  import json;r.pop('record_digest',None);r['record_digest']=hashlib.sha256(json.dumps(r,sort_keys=True,separators=(',',':'),ensure_ascii=True,default=str).encode()).hexdigest()
 case('duplicate-id',lambda r:(r[1].__setitem__('verifier_id',r[0]['verifier_id']),resign(r[1])))
 case('invalid-owner',lambda r:(r[1].__setitem__('owner','nobody'),resign(r[1])))
 case('missing-origin',lambda r:(r[4].__setitem__('inherited_from',''),resign(r[4])))
 case('private-field',lambda r:(r[1].__setitem__('prompt','secret'),resign(r[1])))
 case('authority',lambda r:(r[1].__setitem__('authority_state','granted'),resign(r[1])))
 case('tamper',lambda r:r[1].__setitem__('budget_seconds',999))
 for value in blocked.values():req(value.get('status')=='blocked');req(bool(value.get('errors')));req(value.get('execution_invoked') is False);req(value.get('authority_granted') is False)
 registry=inspect_checkpoint_registry(source_root=source); req(any(r.get('checkpoint_id')=='verifier-ownership-checkpoint' for r in registry.get('checkpoints',[])))
 privacy=package_privacy_summary_for_root(source);req(privacy.get('ok') is True)
 after,after_count=_tree(source);req(before==after);req(count==after_count)
 return {'ok':all(checks),'passed':sum(checks),'total':len(checks),'contract_version':CONTRACT_VERSION,'checkpoint_id':_CHECKPOINT_ID,'read_only':True,'post_available':False,'content_free':True,'summary':summary,'blocked_cases':{k:v.get('errors',[]) for k,v in blocked.items()},'limitations':list(_LIMITATIONS),'source_unchanged':before==after,'source_file_count':count,'runtime_mutated':False,'production_source_modified':False,'fixture_deleted':False,'verifier_retired':False,'global_profile_pass_claimed':False,'provider_contacted':False,'model_contacted':False,'thread_started':False,'process_started':False,'execution_invoked':False,'approval_consumed':False,'authority_granted':False}
