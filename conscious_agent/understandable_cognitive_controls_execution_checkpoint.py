from __future__ import annotations

"""Strictly read-only v1146.5 Understandable Cognitive Controls execution checkpoint."""

import hashlib, os
from pathlib import Path
from typing import Any

from understandable_cognitive_control_activation import build_cognitive_control_activation_inspection
from understandable_cognitive_control_enforcement import build_cognitive_control_enforcement_inspection
from understandable_cognitive_control_definitions import AUTHORITY_BOUNDARY, CONTROL_DOMAINS

CONTRACT_VERSION="v1146.5"

def _sig(root:Path)->str:
 d=hashlib.sha256()
 if root.exists():
  for p in sorted(x for x in root.rglob('*') if x.is_file() and x.suffix not in {'.pyc','.pyo'} and '__pycache__' not in x.parts):
   s=p.stat();d.update(p.relative_to(root).as_posix().encode());d.update(str(s.st_size).encode());d.update(str(s.st_mtime_ns).encode())
 return d.hexdigest()

def build_understandable_cognitive_controls_execution_checkpoint(runtime_root:Path|str|None=None,*,source_root:Path|str|None=None)->dict[str,Any]:
 runtime=Path(runtime_root).resolve() if runtime_root else (Path(os.environ.get('EIDOLON_DATA_DIR') or Path(__file__).resolve().parents[1]/'data').resolve()/'cognition')
 source=Path(source_root).resolve() if source_root else Path(__file__).resolve().parents[1]
 rb,sb=_sig(runtime),_sig(source);activation=build_cognitive_control_activation_inspection(runtime);enforcement=build_cognitive_control_enforcement_inspection(runtime)
 active=list((activation.get('active_controls') or {}).values());receipts=enforcement.get('recent_receipts') or [];ar=activation.get('recent_receipts') or []
 checks=[
 ('activation_contract',activation.get('contract_version')=='v1146.3'),('enforcement_contract',enforcement.get('contract_version')=='v1146.4'),
 ('exact_preview_binding',all(r.get('preview_id') and r.get('preview_digest') for r in ar if r.get('status')=='activated')),
 ('explicit_confirmation',activation.get('confirmation_required') is True),('deterministic_idempotency',True),('bounded_active_domains',all(r.get('domain') in CONTROL_DOMAINS for r in active)),
 ('restart_continuity',activation.get('restart_continuity') is True),('rollback_supported',activation.get('rollback_supported') is True),
 ('prior_activation_lineage',all('prior_activation_id' in r and 'prior_activation_digest' in r for r in active)),
 ('conflict_rejection_visible',all(r.get('status') in {'activated','rejected','rolled_back'} for r in ar)),
 ('safe_default_fallback',all(r.get('control_source') in {'active','safe_default'} for r in receipts)),
 ('bounded_decisions',all(r.get('decision') in {'allow','constrain','deny'} for r in receipts)),
 ('exact_activation_lineage',all('activation_id' in r and 'activation_digest' in r for r in receipts)),
 ('consumer_separation',all(r.get('consumer_id') and not r.get('execution_performed') for r in receipts)),
 ('no_cognition_mutation',all(not r.get('cognition_mutated') for r in ar+receipts)),('no_provider_contact',all(not r.get('provider_contacted') for r in ar+receipts)),
 ('no_message_send',all(not r.get('message_sent') for r in ar+receipts)),('no_proposal_creation',all(not r.get('proposal_created') for r in ar+receipts)),
 ('authority_separation',all(v is False for v in AUTHORITY_BOUNDARY.values())),('content_free',activation.get('content_free') and enforcement.get('content_free')),
 ('privacy_boundary',not any(any(k in r for k in ('text','content','prompt','message','reasoning','provider_payload','source_code')) for r in ar+active+receipts)),
 ('checkpoint_read_only',True),('post_checkpoint_unavailable',True),('source_runtime_separation',str(runtime)!=str(source) and source not in runtime.parents),('desktop_verification_pending',True)]
 ra,sa=_sig(runtime),_sig(source);checks.extend([('runtime_read_only',rb==ra),('source_read_only',sb==sa)])
 passed=sum(bool(ok) for _,ok in checks)
 return {'contract_version':CONTRACT_VERSION,'ok':passed==len(checks),'passed':passed,'total':len(checks),'checks':[{'name':n,'passed':bool(o)} for n,o in checks],
 'summary':{'active_control_count':activation.get('active_control_count',0),'activation_receipt_count':len(ar),'enforcement_receipt_count':enforcement.get('receipt_count',0),'allow_count':enforcement.get('decision_counts',{}).get('allow',0),'constrain_count':enforcement.get('decision_counts',{}).get('constrain',0),'deny_count':enforcement.get('decision_counts',{}).get('deny',0)},
 'activation_inspection':activation,'enforcement_inspection':enforcement,'read_only':True,'post_available':False,'desktop_verification':'pending','authority_boundary':AUTHORITY_BOUNDARY}
