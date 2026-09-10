from __future__ import annotations
"""Strictly read-only v1149.8 Cognitive Alpha feature-freeze reliability checkpoint."""
import hashlib,os
from pathlib import Path
from cognitive_alpha_feature_freeze_execution_checkpoint import build_cognitive_alpha_feature_freeze_execution_checkpoint
from cognitive_alpha_release_continuity import build_cognitive_alpha_release_continuity_inspection
from cognitive_alpha_release_reliability import build_cognitive_alpha_release_reliability
CONTRACT_VERSION="v1149.8"
_EXCLUDED_SOURCE_ROOTS={"data",".git",".venv","venv","__pycache__",".pytest_cache",".mypy_cache","reports"}
def _root(): return Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1]/"data").expanduser().resolve()/"cognition"
def _sig(root,*,source_tree=False):
 d=hashlib.sha256()
 if root.exists():
  if source_tree:
   paths=[]
   for base,dirs,names in os.walk(root):
    dirs[:]=[name for name in dirs if name not in _EXCLUDED_SOURCE_ROOTS]
    paths.extend(Path(base)/name for name in names if Path(name).suffix not in {".pyc",".pyo"})
  else:
   paths=[x for x in root.rglob("*") if x.is_file() and x.suffix not in {".pyc",".pyo"} and "__pycache__" not in x.parts]
  for p in sorted(paths):
   stat=p.stat();d.update(p.relative_to(root).as_posix().encode());d.update(str(stat.st_size).encode());d.update(str(stat.st_mtime_ns).encode())
 return d.hexdigest()
def build_cognitive_alpha_feature_freeze_reliability_checkpoint(runtime_root=None,*,source_root=None):
 runtime=Path(runtime_root).resolve() if runtime_root else _root();source=Path(source_root).resolve() if source_root else Path(__file__).resolve().parents[1];rb=_sig(runtime);sb=_sig(source,source_tree=True)
 execution=build_cognitive_alpha_feature_freeze_execution_checkpoint(source_root=source);continuity=build_cognitive_alpha_release_continuity_inspection(runtime);reliability=build_cognitive_alpha_release_reliability(runtime);cr=continuity.get("recent_records",[])
 checks=[("execution_checkpoint_lineage",execution.get("contract_version")=="v1149.5"),("continuity_contract",continuity.get("contract_version")=="v1149.6"),("reliability_contract",reliability.get("contract_version")=="v1149.7"),("feature_freeze_closed",execution.get("feature_freeze",{}).get("new_feature_intake_open") is False),("exact_prior_lineage",all(not x.get("prior_revision") or x.get("prior_structural_digest") for x in cr)),("visible_behavior_bounded",all(x.get("visible_state") in {"steady","changed","attention"} for x in cr)),("all_release_paths_present",reliability.get("readiness_path_count")==5),("recovery_truth_visible",reliability.get("stable_recovery_count",0)>=0),("drift_reviewed",reliability.get("drift_count",0)>=0),("rollback_pointer_preserved",reliability.get("rollback_pointer_change_count",0)==0),("runtime_state_excluded",reliability.get("runtime_packaging_violation_count",0)==0),("reliability_bounded",0<=reliability.get("reliability_score",-1)<=100 and 0<=reliability.get("uncertainty",-1)<=100),("classification_bounded",reliability.get("classification") in {"reliable","review_required"}),("content_free",not continuity.get("raw_content_exposed") and not reliability.get("raw_content_exposed")),("hidden_reasoning_private",not continuity.get("hidden_reasoning_exposed") and not reliability.get("hidden_reasoning_exposed")),("provider_separation",not reliability.get("provider_contacted")),("no_operation_performed",not reliability.get("operation_performed")),("source_runtime_separation","data" in _EXCLUDED_SOURCE_ROOTS),("read_only",continuity.get("read_only") and reliability.get("read_only")),("post_unavailable",True),("desktop_verification_pending",True),("consciousness_not_proven",True)]
 rows=[{"id":k,"status":"pass" if v else "fail","passed":bool(v)} for k,v in checks];passed=sum(x["passed"] for x in rows);ok=passed==len(rows)
 return {"ok":ok,"status":"ready_for_governance_checkpoint" if ok else "review_required","contract_version":CONTRACT_VERSION,"checkpoint_id":"cognitive-alpha-feature-freeze-reliability:v1149.8","passed":passed,"total":len(rows),"checks":rows,"execution":execution,"continuity":continuity,"reliability":reliability,"summary":{"continuity_record_count":len(cr),"readiness_path_count":reliability["readiness_path_count"],"stable_recovery_count":reliability["stable_recovery_count"],"reliability_score":reliability["reliability_score"],"classification":reliability["classification"]},"read_only":True,"post_available":False,"runtime_mutated":rb!=_sig(runtime),"source_modified":sb!=_sig(source,source_tree=True),"raw_content_exposed":False,"hidden_reasoning_exposed":False,"installation_performed":False,"upgrade_performed":False,"backup_created":False,"rollback_performed":False,"packaging_performed":False,"approval_created":False,"authorization_created":False,"promotion_performed":False,"certification_performed":False,"desktop_verification_pending":True,"consciousness_proven":False}
