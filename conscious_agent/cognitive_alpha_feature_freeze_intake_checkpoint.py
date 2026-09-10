from __future__ import annotations
"""Strictly read-only v1149.2 Cognitive Alpha Feature Freeze intake checkpoint."""
import hashlib,os
from pathlib import Path
from typing import Any
from cognitive_alpha_feature_freeze import FEATURE_DOMAINS, build_cognitive_alpha_feature_freeze
from cognitive_alpha_install_readiness import PATHS, build_cognitive_alpha_install_readiness
CONTRACT_VERSION='v1149.2'
_EXCLUDED_SOURCE_ROOTS={'data','.git','.venv','venv','__pycache__','.pytest_cache','.mypy_cache','reports'}
def _tree(root:Path)->str:
 d=hashlib.sha256()
 paths=[]
 for base,dirs,names in os.walk(root):
  dirs[:]=[name for name in dirs if name not in _EXCLUDED_SOURCE_ROOTS]
  paths.extend(Path(base)/name for name in names if Path(name).suffix not in {'.pyc','.pyo'})
 for p in sorted(paths):
  try:
   stat=p.stat();d.update(p.relative_to(root).as_posix().encode());d.update(b'\0');d.update(str(stat.st_size).encode());d.update(b'\0');d.update(str(stat.st_mtime_ns).encode())
  except OSError:pass
 return d.hexdigest()
def build_cognitive_alpha_feature_freeze_intake_checkpoint(*,source_root:str|Path|None=None)->dict[str,Any]:
 source=Path(source_root).resolve() if source_root else Path(__file__).resolve().parents[1];before=_tree(source)
 freeze=build_cognitive_alpha_feature_freeze(); readiness=build_cognitive_alpha_install_readiness(freeze=freeze)
 features=list(freeze.get('features') or []);paths=list(readiness.get('paths') or [])
 lineage=all(r.get('freeze_digest')==freeze.get('structural_digest') and r.get('freeze_revision')==freeze.get('freeze_revision') for r in paths)
 checks=[
 ('feature_scope_is_frozen',freeze.get('new_feature_intake_open') is False),('all_feature_domains_present',{r.get('domain') for r in features}==set(FEATURE_DOMAINS)),('feature_ids_unique',not freeze.get('duplicate_feature_ids')),('new_capabilities_disallowed',all(r.get('new_capability_allowed') is False for r in features)),('bounded_repairs_remain_allowed',all(r.get('repair_allowed') is True for r in features)),('compatibility_changes_require_review',all(r.get('compatibility_change_requires_review') is True for r in features)),('exact_five_readiness_paths',{r.get('path') for r in paths}==set(PATHS)),('readiness_ids_unique',not readiness.get('duplicate_readiness_ids')),('exact_freeze_lineage',lineage),('readiness_execution_ineligible',all(r.get('execution_eligible') is False for r in paths)),('operator_confirmation_required',all(r.get('operator_confirmation_required') is True for r in paths)),('deterministic_replay_required',all('deterministic_replay' in r.get('required_evidence',[]) for r in paths)),('runtime_separation_required',all('runtime_separation' in r.get('required_evidence',[]) for r in paths)),('records_content_free',freeze.get('content_free') and readiness.get('content_free')),('no_operational_authority',not any(freeze.get('authority_boundary',{}).values()) and not any(readiness.get('authority_boundary',{}).values())),('source_runtime_separation','data' in _EXCLUDED_SOURCE_ROOTS),('desktop_verification_pending',True),('consciousness_not_proven',True)]
 rows=[{'id':n,'status':'pass' if v else 'fail','passed':bool(v)} for n,v in checks];passed=sum(r['passed'] for r in rows);ok=passed==len(rows)
 return {'contract_version':CONTRACT_VERSION,'checkpoint_id':'cognitive-alpha-feature-freeze-intake:v1149.2','status':'ready_for_bundle_b' if ok else 'review_required','ok':ok,'passed':passed,'total':len(rows),'checks':rows,'feature_freeze':freeze,'install_readiness':readiness,'summary':{'feature_count':len(features),'readiness_path_count':len(paths),'new_feature_intake_open':freeze.get('new_feature_intake_open'),'execution_eligible_count':sum(bool(r.get('execution_eligible')) for r in paths)},'read_only':True,'post_available':False,'source_modified':before!=_tree(source),'runtime_mutated':False,'installation_performed':False,'rollback_performed':False,'promotion_performed':False,'certification_performed':False,'provider_contacted':False,'command_executed':False,'message_sent':False,'hidden_reasoning_exposed':False,'desktop_verification_pending':True,'consciousness_proven':False}
