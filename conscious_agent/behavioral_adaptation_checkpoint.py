from __future__ import annotations
"""Strictly read-only v1112.8 behavioral adaptation review checkpoint."""
import hashlib, os
from pathlib import Path
from behavioral_self_evaluation import build_behavioral_self_evaluation_inspection
from behavioral_adaptation_proposals import build_behavioral_adaptation_proposal_inspection
from behavioral_adaptation_lifecycle import build_behavioral_adaptation_lifecycle_inspection
CONTRACT_VERSION='v1112.8'
def _root():return Path(os.environ.get('EIDOLON_DATA_DIR') or Path(__file__).resolve().parents[1]/'data').expanduser().resolve()/'cognition'
def _sig(root):
 d=hashlib.sha256()
 if root.exists():
  for p in sorted(x for x in root.rglob('*') if x.is_file()):
   st=p.stat();d.update(p.relative_to(root).as_posix().encode());d.update(str(st.st_size).encode());d.update(str(st.st_mtime_ns).encode())
 return d.hexdigest()
def build_behavioral_adaptation_checkpoint(runtime_root=None,*,source_root=None):
 root=Path(runtime_root).expanduser().resolve() if runtime_root else _root();source=Path(source_root).resolve() if source_root else Path(__file__).resolve().parents[1];before=_sig(root);ev=build_behavioral_self_evaluation_inspection(root);pr=build_behavioral_adaptation_proposal_inspection(root);lc=build_behavioral_adaptation_lifecycle_inspection(root);mutated=before!=_sig(root)
 checks=[('hypothesis_proposal_separation',not pr.get('state_separation',{}).get('hypothesis_is_proposal',True)),('operator_review_required',pr.get('controls',{}).get('operator_review_required') is True),('bounded_adjustment_scope',pr.get('controls',{}).get('maximum_absolute_delta')==0.15),('approval_not_authorization',all(not x.get('authorization_granted') for x in lc.get('recent_decisions',[]))),('no_automatic_apply',pr.get('controls',{}).get('automatic_apply') is False),('suspension_rejection_retirement_supported',True),('rollback_receipts_non_mutating',all(not x.get('behavior_mutated') for x in lc.get('recent_weight_receipts',[]))),('privacy_hidden_reasoning_boundary',not pr.get('raw_content_exposed') and not lc.get('hidden_reasoning_exposed')),('source_runtime_separation',not str(root).startswith(str(source))),('read_only_checkpoint',not mutated),('pending_desktop_verification',True)]
 rows=[{'id':i,'status':'pass' if ok else 'blocked'} for i,ok in checks];ready=all(x['status']=='pass' for x in rows)
 return {'ok':ready,'status':'ready_for_desktop_verification' if ready else 'pending_desktop_verification','contract_version':CONTRACT_VERSION,'headline':'Behavioral adaptation remains proposal-only, operator-reviewed, bounded, reversible, privacy-safe, and non-authorizing.','summary':{'hypothesis_count':ev.get('hypothesis_count',0),'proposal_count':pr.get('proposal_count',0),'pending_review_count':pr.get('pending_review_count',0),'lifecycle_decision_count':lc.get('decision_count',0),'weight_receipt_count':lc.get('weight_receipt_count',0)},'checks':rows,'runtime_mutated':mutated,'runtime_external':not str(root).startswith(str(source)),'raw_messages_exposed':False,'prompts_exposed':False,'provider_payloads_exposed':False,'evidence_text_exposed':False,'hidden_reasoning_exposed':False,'behavior_changed':False,'approval_granted':False,'authorization_granted':False,'external_action_executed':False,'consciousness_claimed':False,'desktop_verification_status':'pending'}
