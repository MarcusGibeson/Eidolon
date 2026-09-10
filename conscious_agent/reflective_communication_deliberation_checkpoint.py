from __future__ import annotations
"""Strictly read-only v1129.5 Reflective Communication Deliberation checkpoint."""
import hashlib, os
from pathlib import Path
from reflective_communication_deliberation_sessions import build_reflective_communication_deliberation_session_inspection
from reflective_communication_arbitration import build_reflective_communication_arbitration_inspection, OUTCOMES
CONTRACT_VERSION='v1129.5'
def _root(): return Path(os.environ.get('EIDOLON_DATA_DIR') or Path(__file__).resolve().parents[1]/'data').expanduser().resolve()/'cognition'
def _sig(root):
 d=hashlib.sha256()
 if not root.exists(): return d.hexdigest()
 for p in sorted(x for x in root.rglob('*') if x.is_file() and '__pycache__' not in x.parts and x.suffix!='.pyc'):
  st=p.stat();d.update(p.relative_to(root).as_posix().encode());d.update(str(st.st_size).encode());d.update(str(st.st_mtime_ns).encode())
 return d.hexdigest()
def build_reflective_communication_deliberation_checkpoint(runtime_root=None,*,source_root=None):
 runtime=Path(runtime_root).resolve() if runtime_root else _root();source=Path(source_root).resolve() if source_root else Path(__file__).resolve().parents[1];rb,sb=_sig(runtime),_sig(source);sessions=build_reflective_communication_deliberation_session_inspection(runtime);arb=build_reflective_communication_arbitration_inspection(runtime);rm,sm=rb!=_sig(runtime),sb!=_sig(source)
 checks=[('bounded_sessions',sessions.get('contract_version')=='v1129.3'),('deterministic_arbitration',arb.get('contract_version')=='v1129.4'),('recognized_outcomes',set(arb.get('recognized_outcomes',[]))==OUTCOMES),('deliberate_silence','deliberate_silence' in OUTCOMES),('communication_eligibility','communicate_when_eligible' in OUTCOMES),('delayed_follow_up','delayed_follow_up' in OUTCOMES),('curiosity_eligibility','curiosity_question_eligible' in OUTCOMES),('clarification_eligibility','clarification_eligible' in OUTCOMES),('interruption_deferral','defer_for_interruption' in OUTCOMES),('timing_deferral','defer_for_timing' in OUTCOMES),('recovery_deferral','defer_for_recovery' in OUTCOMES),('focus_deferral','defer_for_focus' in OUTCOMES),('operator_review_deferral','defer_for_operator_review' in OUTCOMES),('prerequisite_deferral','await_prerequisite' in OUTCOMES),('content_not_exposed',not sessions.get('raw_content_exposed') and not arb.get('raw_content_exposed')),('hidden_reasoning_not_exposed',not sessions.get('hidden_reasoning_exposed') and not arb.get('hidden_reasoning_exposed')),('no_provider_or_message',not sessions.get('provider_contacted') and not arb.get('provider_contacted') and not sessions.get('message_sent') and not arb.get('message_sent')),('no_notification_or_initiative',not sessions.get('notification_created') and not arb.get('notification_created') and not sessions.get('initiative_created') and not arb.get('initiative_created')),('source_runtime_read_only',not rm and not sm),('pending_desktop_verification',True)]
 rows=[{'id':i,'status':'pass' if ok else 'fail'} for i,ok in checks]
 return {'ok':all(ok for _,ok in checks),'contract_version':CONTRACT_VERSION,'checkpoint_name':'Reflective Communication Deliberation','checks':rows,'passed':sum(ok for _,ok in checks),'total':len(checks),'sessions':sessions,'arbitration':arb,'runtime_mutated':rm,'source_modified':sm,'raw_content_exposed':False,'message_text_exposed':False,'hidden_reasoning_exposed':False,'provider_contacted':False,'message_sent':False,'notification_created':False,'initiative_created':False,'approval_created':False,'authorization_created':False,'external_action_executed':False,'promotion_performed':False,'certification_performed':False,'desktop_verification':'pending'}
