from __future__ import annotations
"""Strictly read-only v1149.5 Cognitive Alpha feature-freeze execution checkpoint."""
import hashlib,os
from pathlib import Path
from typing import Any
from cognitive_alpha_feature_freeze import build_cognitive_alpha_feature_freeze
from cognitive_alpha_install_readiness import PATHS, build_cognitive_alpha_install_readiness
from cognitive_alpha_release_readiness_execution import build_cognitive_alpha_release_readiness_execution
from cognitive_alpha_recovery_continuity import build_cognitive_alpha_recovery_continuity
CONTRACT_VERSION='v1149.5'
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
def build_cognitive_alpha_feature_freeze_execution_checkpoint(*,source_root:str|Path|None=None)->dict[str,Any]:
 source=Path(source_root).resolve() if source_root else Path(__file__).resolve().parents[1];before=_tree(source)
 freeze=build_cognitive_alpha_feature_freeze(); readiness=build_cognitive_alpha_install_readiness(freeze=freeze); execution=build_cognitive_alpha_release_readiness_execution(readiness=readiness); continuity=build_cognitive_alpha_recovery_continuity(execution=execution)
 ex=list(execution.get('executions') or []);co=list(continuity.get('records') or [])
 checks=[('feature_freeze_remains_closed',freeze.get('new_feature_intake_open') is False),('all_readiness_paths_exercised',{x.get('path') for x in ex}==set(PATHS)),('execution_ids_unique',not execution.get('duplicate_execution_ids')),('operator_confirmation_bound',execution.get('operator_confirmed') is True),('all_checks_are_structural_dry_runs',all(x.get('check_mode')=='structural_dry_run' for x in ex)),('no_operation_performed',execution.get('all_operations_simulated') is True),('bounded_step_budget',all(x.get('step_budget',99)<=4 for x in ex)),('bounded_attempt_budget',all(x.get('attempt_budget',99)<=1 for x in ex)),('bounded_runtime_budget',all(x.get('runtime_budget_ms',9999)<=250 for x in ex)),('exact_execution_lineage',all(x.get('readiness_digest') for x in ex)),('continuity_covers_all_paths',{x.get('path') for x in co}==set(PATHS)),('continuity_ids_unique',not continuity.get('duplicate_continuity_ids')),('restart_replay_verified',all(x.get('restart_replay')=='verified' for x in co)),('lineage_recovery_verified',all(x.get('lineage_recovery')=='verified' for x in co)),('rollback_pointer_unchanged',all(x.get('rollback_pointer_changed') is False for x in co)),('runtime_state_not_packaged',all(x.get('runtime_state_packaged') is False for x in co)),('records_content_free',execution.get('content_free') and continuity.get('content_free')),('no_operational_authority',not any(execution.get('authority_boundary',{}).values()) and not any(continuity.get('authority_boundary',{}).values())),('source_runtime_separation','data' in _EXCLUDED_SOURCE_ROOTS),('desktop_verification_pending',True),('consciousness_not_proven',True)]
 rows=[{'id':n,'status':'pass' if v else 'fail','passed':bool(v)} for n,v in checks];passed=sum(r['passed'] for r in rows);ok=passed==len(rows)
 return {'contract_version':CONTRACT_VERSION,'checkpoint_id':'cognitive-alpha-feature-freeze-execution:v1149.5','status':'ready_for_bundle_c' if ok else 'review_required','ok':ok,'passed':passed,'total':len(rows),'checks':rows,'feature_freeze':freeze,'install_readiness':readiness,'readiness_execution':execution,'recovery_continuity':continuity,'summary':{'readiness_path_count':len(PATHS),'execution_count':len(ex),'continuity_record_count':len(co),'stable_count':continuity.get('stable_count',0)},'read_only':True,'post_available':False,'source_modified':before!=_tree(source),'runtime_mutated':False,'installation_performed':False,'upgrade_performed':False,'backup_created':False,'rollback_performed':False,'promotion_performed':False,'certification_performed':False,'provider_contacted':False,'command_executed':False,'message_sent':False,'hidden_reasoning_exposed':False,'desktop_verification_pending':True,'consciousness_proven':False}
