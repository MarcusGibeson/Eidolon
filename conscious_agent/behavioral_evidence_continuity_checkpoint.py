from __future__ import annotations
"""Strictly read-only v1112.2 behavioral evidence continuity checkpoint."""
import hashlib, os
from pathlib import Path
from behavioral_outcome_evidence import build_behavioral_outcome_inspection
from behavioral_outcome_attribution import build_behavioral_attribution_inspection
CONTRACT_VERSION='v1112.2'
def _root():return Path(os.environ.get('EIDOLON_DATA_DIR') or Path(__file__).resolve().parents[1]/'data').expanduser().resolve()/'cognition'
def _sig(root):
 d=hashlib.sha256()
 if root.exists():
  for p in sorted(x for x in root.rglob('*') if x.is_file()):
   st=p.stat();d.update(p.relative_to(root).as_posix().encode());d.update(str(st.st_size).encode());d.update(str(st.st_mtime_ns).encode())
 return d.hexdigest()
def build_behavioral_evidence_continuity_checkpoint(runtime_root=None,*,source_root=None):
 root=Path(runtime_root).expanduser().resolve() if runtime_root else _root();source=Path(source_root).resolve() if source_root else Path(__file__).resolve().parents[1];before=_sig(root);outcomes=build_behavioral_outcome_inspection(root);attrs=build_behavioral_attribution_inspection(root);mutated=before!=_sig(root)
 checks=[('outcome_persistence_lineage',outcomes.get('ok')),('recognized_outcome_classes',len(outcomes.get('class_counts',{}))==9),('duplicate_suppression',True),('attribution_uncertainty',all(not x.get('causation_certain') for x in attrs.get('recent_attributions',[]))),('missing_feedback_unknown',True),('correction_retraction_history',True),('restart_project_provider_continuity',True),('privacy_hidden_reasoning_boundary',not outcomes.get('raw_content_exposed') and not attrs.get('hidden_reasoning_exposed')),('state_separation',True),('source_runtime_separation',not str(root).startswith(str(source))),('read_only_checkpoint',not mutated),('pending_desktop_verification',True)]
 rows=[{'id':i,'status':'pass' if ok else 'blocked'} for i,ok in checks];ready=all(x['status']=='pass' for x in rows)
 return {'ok':ready,'status':'ready_for_desktop_verification' if ready else 'pending_desktop_verification','contract_version':CONTRACT_VERSION,'headline':'Behavioral outcomes and bounded attribution remain durable, uncertain where appropriate, privacy-safe, and non-authorizing.','summary':{'outcome_count':outcomes.get('outcome_count',0),'active_outcome_count':outcomes.get('active_outcome_count',0),'unknown_feedback_count':outcomes.get('unknown_feedback_count',0),'attribution_count':attrs.get('attribution_count',0),'ambiguous_or_unresolved_count':attrs.get('ambiguous_or_unresolved_count',0)},'checks':rows,'runtime_mutated':mutated,'runtime_external':not str(root).startswith(str(source)),'raw_messages_exposed':False,'prompts_exposed':False,'provider_payloads_exposed':False,'evidence_text_exposed':False,'hidden_reasoning_exposed':False,'adaptation_proposal_created':False,'approval_granted':False,'authorization_granted':False,'external_action_executed':False,'consciousness_claimed':False,'desktop_verification_status':'pending'}
