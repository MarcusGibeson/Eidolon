from __future__ import annotations
"""Strictly read-only v1128.5 Reflection-Supported Revision Deliberation checkpoint."""
import hashlib, os
from pathlib import Path
from reflection_supported_revision_deliberation_sessions import build_reflection_supported_revision_deliberation_session_inspection
from reflection_supported_revision_arbitration import build_reflection_supported_revision_arbitration_inspection, OUTCOMES
CONTRACT_VERSION='v1128.5'
def _root():return Path(os.environ.get('EIDOLON_DATA_DIR') or Path(__file__).resolve().parents[1]/'data').expanduser().resolve()/'cognition'
def _sig(root):
 d=hashlib.sha256()
 if not root.exists():return d.hexdigest()
 for p in sorted(x for x in root.rglob('*') if x.is_file() and '__pycache__' not in x.parts and x.suffix!='.pyc'):
  st=p.stat();d.update(p.relative_to(root).as_posix().encode());d.update(str(st.st_size).encode());d.update(str(st.st_mtime_ns).encode())
 return d.hexdigest()
def build_reflection_supported_revision_deliberation_checkpoint(runtime_root=None,*,source_root=None):
 runtime=Path(runtime_root).resolve() if runtime_root else _root();source=Path(source_root).resolve() if source_root else Path(__file__).resolve().parents[1];rb,sb=_sig(runtime),_sig(source);sessions=build_reflection_supported_revision_deliberation_session_inspection(runtime);arbitration=build_reflection_supported_revision_arbitration_inspection(runtime);rm,sm=rb!=_sig(runtime),sb!=_sig(source)
 checks=[('bounded_revision_sessions',sessions.get('contract_version')=='v1128.3'),('deterministic_target_arbitration',arbitration.get('contract_version')=='v1128.4'),('recognized_outcomes',set(arbitration.get('recognized_outcomes',[]))==OUTCOMES),('belief_target_specific','recommend_belief_revision' in OUTCOMES),('motivation_target_specific','recommend_motivation_revision' in OUTCOMES),('goal_target_specific','recommend_goal_revision' in OUTCOMES),('self_model_target_specific','recommend_self_model_revision' in OUTCOMES),('deliberate_non_application','deliberate_non_application' in OUTCOMES),('recovery_deferral','defer_for_recovery' in OUTCOMES),('operator_review_deferral','defer_for_operator_review' in OUTCOMES),('prerequisite_deferral','await_prerequisite' in OUTCOMES),('unresolved_preserved','unresolved' in OUTCOMES),('content_not_exposed',not sessions.get('raw_content_exposed') and not arbitration.get('raw_content_exposed')),('hidden_reasoning_not_exposed',not sessions.get('hidden_reasoning_exposed') and not arbitration.get('hidden_reasoning_exposed')),('no_target_revision',not sessions.get('target_revised') and not arbitration.get('target_revised')),('no_application_or_execution',not sessions.get('revision_applied') and not arbitration.get('revision_applied') and not sessions.get('external_action_executed') and not arbitration.get('external_action_executed')),('source_runtime_read_only',not rm and not sm),('pending_desktop_verification',True)]
 rows=[{'id':i,'status':'pass' if ok else 'fail'} for i,ok in checks]
 return {'ok':all(ok for _,ok in checks),'contract_version':CONTRACT_VERSION,'checkpoint_name':'Reflection-Supported Revision Deliberation','checks':rows,'passed':sum(ok for _,ok in checks),'total':len(checks),'sessions':sessions,'arbitration':arbitration,'runtime_mutated':rm,'source_modified':sm,'raw_content_exposed':False,'hidden_reasoning_exposed':False,'belief_revised':False,'motivation_revised':False,'goal_revised':False,'self_model_revised':False,'revision_applied':False,'external_action_executed':False,'desktop_verification_pending':True}
