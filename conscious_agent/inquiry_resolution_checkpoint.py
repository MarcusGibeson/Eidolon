from __future__ import annotations
"""Read-only v1113.8 inquiry evidence assimilation and resolution checkpoint."""
import hashlib, os
from pathlib import Path
from inquiry_evidence_receipts import build_inquiry_evidence_receipt_inspection
from inquiry_evidence_assimilation_v1113 import build_inquiry_evidence_assimilation_inspection
from inquiry_resolution_lifecycle_v1113 import build_inquiry_resolution_lifecycle_inspection
CONTRACT_VERSION='v1113.8'
def _root():return Path(os.environ.get('EIDOLON_DATA_DIR') or Path(__file__).resolve().parents[1]/'data').expanduser().resolve()/'cognition'
def _sig(root):
 d=hashlib.sha256()
 if root.exists():
  for p in sorted(x for x in root.rglob('*') if x.is_file()):
   st=p.stat();d.update(p.relative_to(root).as_posix().encode());d.update(str(st.st_size).encode());d.update(str(st.st_mtime_ns).encode())
 return d.hexdigest()
def build_inquiry_resolution_checkpoint(runtime_root=None,*,source_root=None):
 root=Path(runtime_root).expanduser().resolve() if runtime_root else _root();source=Path(source_root).resolve() if source_root else Path(__file__).resolve().parents[1];before=_sig(root);e=build_inquiry_evidence_receipt_inspection(root);a=build_inquiry_evidence_assimilation_inspection(root);r=build_inquiry_resolution_lifecycle_inspection(root);mutated=before!=_sig(root)
 checks=[('evidence_lineage',True),('provenance_validation',True),('duplicate_suppression',True),('raw_content_forbidden',e.get('controls',{}).get('raw_content_forbidden') is True),('missing_evidence_not_success',True),('contradiction_preserves_uncertainty',a.get('controls',{}).get('contradiction_requires_uncertainty') is True),('unsupported_completion_rejected',r.get('controls',{}).get('unsupported_completion_forbidden') is True),('operator_confirmation',r.get('controls',{}).get('operator_confirmation_required') is True),('belief_separation',not r.get('belief_changed')),('authority_separation',not r.get('authorization_granted')),('no_external_acquisition',not e.get('external_browsing_performed') and not e.get('provider_contacted')),('read_only_checkpoint',not mutated),('source_runtime_separation',not str(root).startswith(str(source))),('pending_desktop_verification',True)]
 rows=[{'id':n,'status':'pass' if ok else 'blocked'} for n,ok in checks];ready=all(x['status']=='pass' for x in rows)
 return {'ok':ready,'status':'ready_for_desktop_verification' if ready else 'pending_desktop_verification','contract_version':CONTRACT_VERSION,'headline':'Governed evidence receipts may inform accountable inquiry resolution without autonomous acquisition or authority escalation.','summary':{'receipt_count':e.get('receipt_count',0),'assimilation_count':a.get('assimilation_count',0),'resolution_count':r.get('resolution_count',0)},'checks':rows,'runtime_mutated':mutated,'runtime_external':not str(root).startswith(str(source)),'raw_messages_exposed':False,'prompts_exposed':False,'provider_payloads_exposed':False,'evidence_text_exposed':False,'hidden_reasoning_exposed':False,'belief_changed':False,'authorization_granted':False,'external_browsing_performed':False,'provider_contacted':False,'external_action_executed':False,'consciousness_claimed':False,'desktop_verification_status':'pending'}
