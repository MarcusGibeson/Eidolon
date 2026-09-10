from __future__ import annotations
"""Strictly read-only v1130.5 Genuine Inquiry Deliberation checkpoint."""
import hashlib, os
from pathlib import Path
from genuine_inquiry_deliberation_sessions import build_genuine_inquiry_deliberation_session_inspection
from genuine_inquiry_arbitration import build_genuine_inquiry_arbitration_inspection, OUTCOMES
CONTRACT_VERSION='v1130.5'
def _root(): return Path(os.environ.get('EIDOLON_DATA_DIR') or Path(__file__).resolve().parents[1]/'data').expanduser().resolve()/'cognition'
def _sig(root:Path):
 d=hashlib.sha256()
 if not root.exists(): return d.hexdigest()
 for p in sorted(x for x in root.rglob('*') if x.is_file() and '__pycache__' not in x.parts and x.suffix!='.pyc'):
  s=p.stat(); d.update(p.relative_to(root).as_posix().encode()); d.update(str(s.st_size).encode()); d.update(str(s.st_mtime_ns).encode())
 return d.hexdigest()
def build_genuine_inquiry_deliberation_checkpoint(runtime_root=None,*,source_root=None):
 runtime=Path(runtime_root).resolve() if runtime_root else _root(); source=Path(source_root).resolve() if source_root else Path(__file__).resolve().parents[1]; rb=_sig(runtime); sb=_sig(source); sessions=build_genuine_inquiry_deliberation_session_inspection(runtime); arbitration=build_genuine_inquiry_arbitration_inspection(runtime)
 checks=[('session_contract',sessions.get('contract_version')=='v1130.3'),('arbitration_contract',arbitration.get('contract_version')=='v1130.4'),('bounded_sessions',all(1<=x.get('deliberation_budget',0)<=6 for x in sessions.get('recent_sessions',[]))),('recognized_outcomes',len(OUTCOMES)==11),('recovery_deferral','defer_for_recovery' in OUTCOMES),('focus_deferral','defer_for_focus' in OUTCOMES),('budget_deferral','defer_for_cognitive_budget' in OUTCOMES),('operator_review_deferral','defer_for_operator_review' in OUTCOMES),('prerequisite_deferral','await_prerequisite' in OUTCOMES),('deliberate_no_inquiry','deliberate_no_inquiry' in OUTCOMES),('false_pressure_suppression','suppress_false_pressure' in OUTCOMES),('content_free_lineage',all(x.get('candidate_id') and x.get('signal_ids') is not None for x in sessions.get('recent_sessions',[]))),('privacy_boundary',not sessions.get('raw_content_exposed') and not sessions.get('question_text_exposed') and not sessions.get('hidden_reasoning_exposed')),('no_browser_or_provider',not sessions.get('browser_contacted') and not arbitration.get('browser_contacted') and not sessions.get('provider_contacted') and not arbitration.get('provider_contacted')),('no_message_or_notification',not sessions.get('message_sent') and not arbitration.get('message_sent') and not sessions.get('notification_created') and not arbitration.get('notification_created')),('authority_separation',not any(sessions.get('authority_boundary',{}).values()) and not any(arbitration.get('authority_boundary',{}).values())),('read_only',rb==_sig(runtime) and sb==_sig(source)),('desktop_pending',True)]
 return {'ok':all(v for _,v in checks),'contract_version':CONTRACT_VERSION,'checks':[{'id':k,'status':'pass' if v else 'fail'} for k,v in checks],'sessions':sessions,'arbitration':arbitration,'runtime_mutated':rb!=_sig(runtime),'source_modified':sb!=_sig(source),'raw_content_exposed':False,'question_text_exposed':False,'hidden_reasoning_exposed':False,'browser_contacted':False,'provider_contacted':False,'message_sent':False,'notification_created':False,'initiative_created':False,'approval_created':False,'authorization_created':False,'external_action_executed':False,'promotion_performed':False,'certification_performed':False,'desktop_verification':'pending'}
