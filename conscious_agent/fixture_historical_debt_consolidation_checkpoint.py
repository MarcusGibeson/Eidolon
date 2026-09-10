from __future__ import annotations
"""Read-only v1193.8 fixture and historical-debt consolidation checkpoint."""
import hashlib, os
from pathlib import Path
from typing import Any
from fixture_historical_debt_consolidation import create_fixture_record, consolidate_fixture_records, public_consolidation_summary
from checkpoint_registry import inspect_checkpoint_registry
from package_integrity import package_privacy_summary_for_root
CONTRACT_VERSION="v1193.8";_CHECKPOINT_ID="fixture-historical-debt-consolidation:v1193.8"
_LIMITATIONS=("Consolidation is source-declared and read-only.","No fixture is deleted and no verifier is retired.","Deferred partial overlap remains historical debt.","Global quick/full profile execution remains outside this checkpoint.","Desktop Codex and native-provider review remain deferred until v1200.")
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
def _rows():
 return [
  create_fixture_record(fixture_id="current-v1193",owner="platform",cleanup_owner="platform",fixture_group="v1193-current",suite_path="tools/v1193_6_8_fixture_historical_debt_consolidation_tests.py",source_version="v1193.8",overlap_class="unique",disposition="retain_independent",expected_checks=80),
  create_fixture_record(fixture_id="historical-canonical",owner="release",cleanup_owner="release",fixture_group="historical-checkpoints",suite_path="tools/v1189_9_persistent_supervised_developer_alpha_hardening_checkpoint_tests.py",source_version="v1189.9",overlap_class="checkpoint_overlap",canonical_fixture_id="historical-canonical",disposition="retain_canonical",historical_debt_id="debt-historical-overlap",debt_severity="medium",expected_checks=72),
  create_fixture_record(fixture_id="historical-alias",owner="release",cleanup_owner="release",fixture_group="historical-checkpoints",suite_path="tools/v1189_6_8_persistent_supervised_developer_alpha_hardening_tests.py",source_version="v1189.8",overlap_class="exact_duplicate",canonical_fixture_id="historical-canonical",disposition="retain_alias",historical_debt_id="debt-historical-overlap",debt_severity="medium",expected_checks=72),
  create_fixture_record(fixture_id="partial-overlap",owner="platform",cleanup_owner="platform",fixture_group="legacy-fixtures",suite_path="tools/v1174_9_reflective_plan_review_checkpoint_tests.py",source_version="v1174.9",overlap_class="partial_overlap",canonical_fixture_id="historical-canonical",disposition="defer_consolidation",historical_debt_id="debt-partial-overlap",debt_severity="high",expected_checks=90),]
def build_fixture_historical_debt_consolidation_checkpoint(*,source_root:str|Path|None=None,runtime_root:str|Path|None=None)->dict[str,Any]:
 source=Path(source_root or Path(__file__).resolve().parents[1]).resolve();del runtime_root
 before,count=_tree(source);checks=[];req=lambda v:checks.append(bool(v))
 report=consolidate_fixture_records(_rows());summary=public_consolidation_summary(report)
 for v in (report['status']=='consolidated',summary['record_count']==4,summary['alias_count']==1,summary['deferred_count']==1,summary['historical_debt_count']==3,summary['historical_truth_preserved'],summary['fixture_deleted'] is False,summary['verifier_retired'] is False):req(v)
 blocked={};good=_rows()
 def case(name,mut):
  rows=[dict(r) for r in good];mut(rows);blocked[name]=consolidate_fixture_records(rows)
 case('tamper',lambda r:r[0].__setitem__('expected_checks',999));case('private-field',lambda r:r[0].__setitem__('prompt','x'));case('authority',lambda r:r[0].__setitem__('authority_state','granted'));case('delete',lambda r:r[0].__setitem__('fixture_deleted',True));case('retire',lambda r:r[0].__setitem__('verifier_retired',True));case('truth-loss',lambda r:r[0].__setitem__('historical_truth_preserved',False));case('unknown-canonical',lambda r:r[2].__setitem__('canonical_fixture_id','missing'));case('duplicate-id',lambda r:r[1].__setitem__('fixture_id',r[0]['fixture_id']));case('duplicate-path',lambda r:r[1].__setitem__('suite_path',r[0]['suite_path']));case('bad-owner',lambda r:r[0].__setitem__('cleanup_owner','nobody'))
 for value in blocked.values():req(value.get('status')=='blocked');req(bool(value.get('errors')));req(value.get('execution_invoked') is False);req(value.get('authority_granted') is False)
 registry=inspect_checkpoint_registry(source_root=source);req(any(r.get('checkpoint_id')=='fixture-historical-debt-consolidation-checkpoint' for r in registry.get('checkpoints',[])))
 privacy=package_privacy_summary_for_root(source);req(privacy.get('ok') is True)
 after,after_count=_tree(source);req(before==after);req(count==after_count)
 return {'ok':all(checks),'passed':sum(checks),'total':len(checks),'contract_version':CONTRACT_VERSION,'checkpoint_id':_CHECKPOINT_ID,'read_only':True,'post_available':False,'content_free':True,'summary':summary,'blocked_cases':{k:v.get('errors',[]) for k,v in blocked.items()},'limitations':list(_LIMITATIONS),'source_unchanged':before==after,'source_file_count':count,'runtime_mutated':False,'production_source_modified':False,'fixture_deleted':False,'verifier_retired':False,'global_profile_pass_claimed':False,'provider_contacted':False,'model_contacted':False,'thread_started':False,'process_started':False,'execution_invoked':False,'approval_consumed':False,'authority_granted':False}
