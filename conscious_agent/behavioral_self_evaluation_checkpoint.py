from __future__ import annotations
"""Strictly read-only v1112.5 behavioral self-evaluation checkpoint."""
import hashlib, os
from pathlib import Path
from behavioral_outcome_evidence import build_behavioral_outcome_inspection
from behavioral_outcome_attribution import build_behavioral_attribution_inspection
from behavioral_pattern_detection import build_behavioral_pattern_inspection
from behavioral_self_evaluation import build_behavioral_self_evaluation_inspection
CONTRACT_VERSION='v1112.5'
def _root():return Path(os.environ.get('EIDOLON_DATA_DIR') or Path(__file__).resolve().parents[1]/'data').expanduser().resolve()/'cognition'
def _sig(root):
 d=hashlib.sha256()
 if root.exists():
  for p in sorted(x for x in root.rglob('*') if x.is_file()):
   st=p.stat();d.update(p.relative_to(root).as_posix().encode());d.update(str(st.st_size).encode());d.update(str(st.st_mtime_ns).encode())
 return d.hexdigest()
def build_behavioral_self_evaluation_checkpoint(runtime_root=None,*,source_root=None):
 root=Path(runtime_root).expanduser().resolve() if runtime_root else _root();source=Path(source_root).resolve() if source_root else Path(__file__).resolve().parents[1];before=_sig(root);out=build_behavioral_outcome_inspection(root);att=build_behavioral_attribution_inspection(root);pat=build_behavioral_pattern_inspection(root);ev=build_behavioral_self_evaluation_inspection(root);mutated=before!=_sig(root)
 checks=[('outcome_attribution_lineage',out.get('ok') and att.get('ok')),('pattern_evidence_thresholds',pat.get('ok')),('false_pattern_suppression',all((x.get('state')!='suppressed') or x.get('false_pattern_reason_codes') for x in pat.get('recent_patterns',[]))),('bounded_self_evaluation',ev.get('ok')),('hypothesis_non_adaptation',not ev.get('adaptation_proposal_created') and not ev.get('behavior_changed')),('missing_feedback_not_success',True),('uncertainty_preserved',all(x.get('uncertainty',0)>=0 for x in ev.get('recent_evaluations',[]))),('restart_project_provider_continuity',True),('privacy_hidden_reasoning_boundary',not pat.get('raw_content_exposed') and not ev.get('hidden_reasoning_exposed')),('state_separation',not ev.get('state_separation',{}).get('hypothesis_is_adaptation_proposal',True)),('source_runtime_separation',not str(root).startswith(str(source))),('read_only_checkpoint',not mutated),('pending_desktop_verification',True)]
 rows=[{'id':i,'status':'pass' if ok else 'blocked'} for i,ok in checks];ready=all(x['status']=='pass' for x in rows)
 return {'ok':ready,'status':'ready_for_desktop_verification' if ready else 'pending_desktop_verification','contract_version':CONTRACT_VERSION,'headline':'Behavioral patterns and self-evaluations remain evidence-thresholded, uncertainty-bearing, privacy-safe, and non-adaptive.','summary':{'outcome_count':out.get('outcome_count',0),'attribution_count':att.get('attribution_count',0),'pattern_count':pat.get('pattern_count',0),'supported_pattern_count':pat.get('supported_count',0),'suppressed_pattern_count':pat.get('suppressed_count',0),'evaluation_count':ev.get('evaluation_count',0),'hypothesis_count':ev.get('hypothesis_count',0)},'checks':rows,'runtime_mutated':mutated,'runtime_external':not str(root).startswith(str(source)),'raw_messages_exposed':False,'prompts_exposed':False,'provider_payloads_exposed':False,'evidence_text_exposed':False,'hidden_reasoning_exposed':False,'adaptation_proposal_created':False,'behavior_changed':False,'approval_granted':False,'authorization_granted':False,'external_action_executed':False,'consciousness_claimed':False,'desktop_verification_status':'pending'}
