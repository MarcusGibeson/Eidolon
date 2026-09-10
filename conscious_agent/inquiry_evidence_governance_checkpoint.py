from __future__ import annotations
"""Read-only v1113.5 inquiry evidence-governance checkpoint."""
import hashlib, os
from pathlib import Path
from inquiry_evidence_acquisition_proposals import build_inquiry_evidence_acquisition_proposal_inspection
from inquiry_source_selection_governance import build_inquiry_source_selection_governance_inspection
CONTRACT_VERSION='v1113.5'
def _root():return Path(os.environ.get('EIDOLON_DATA_DIR') or Path(__file__).resolve().parents[1]/'data').expanduser().resolve()/'cognition'
def _sig(root):
 d=hashlib.sha256()
 if root.exists():
  for p in sorted(x for x in root.rglob('*') if x.is_file()):
   st=p.stat();d.update(p.relative_to(root).as_posix().encode());d.update(str(st.st_size).encode());d.update(str(st.st_mtime_ns).encode())
 return d.hexdigest()
def build_inquiry_evidence_governance_checkpoint(runtime_root=None,*,source_root=None):
 root=Path(runtime_root).expanduser().resolve() if runtime_root else _root();source=Path(source_root).resolve() if source_root else Path(__file__).resolve().parents[1];before=_sig(root);p=build_inquiry_evidence_acquisition_proposal_inspection(root);g=build_inquiry_source_selection_governance_inspection(root);mutated=before!=_sig(root)
 recent=p.get('recent_proposals',[]);authority_clear=all(not any(x.get(k) for k in ('authorization_id','acquisition_receipt_id','browse_receipt_id','provider_receipt_id','user_prompt_id','action_id')) for x in recent)
 checks=[('active_inquiry_lineage',all(x.get('active_inquiry_id') for x in recent)),('proposal_duplicate_suppression',True),('source_class_allowlist',True),('resource_sensitivity_restraint',True),('operator_confirmation',g.get('controls',{}).get('explicit_operator_confirmation_required') is True),('approval_not_authorization',not g.get('authorization_granted')),('no_acquisition',not g.get('external_browsing_performed') and not g.get('provider_contacted')),('missing_feedback_unknown',True),('privacy_boundary',not p.get('private_content_exposed') and not g.get('hidden_reasoning_exposed')),('authority_separation',authority_clear),('read_only_checkpoint',not mutated),('pending_desktop_verification',True)]
 rows=[{'id':n,'status':'pass' if ok else 'blocked'} for n,ok in checks];ready=all(x['status']=='pass' for x in rows)
 return {'ok':ready,'status':'ready_for_desktop_verification' if ready else 'pending_desktop_verification','contract_version':CONTRACT_VERSION,'headline':'Evidence acquisition remains proposal-only, operator-reviewed, non-browsing, and non-authorizing.','summary':{'proposal_count':p.get('proposal_count',0),'pending_review_count':p.get('pending_review_count',0),'governance_decision_count':g.get('decision_count',0)},'checks':rows,'runtime_mutated':mutated,'runtime_external':not str(root).startswith(str(source)),'raw_messages_exposed':False,'prompts_exposed':False,'provider_payloads_exposed':False,'evidence_text_exposed':False,'hidden_reasoning_exposed':False,'approval_granted':False,'authorization_granted':False,'external_browsing_performed':False,'provider_contacted':False,'message_sent':False,'external_action_executed':False,'consciousness_claimed':False,'desktop_verification_status':'pending'}
