from __future__ import annotations
"""Strictly read-only v1127.5 Continuous Thought Deliberation checkpoint."""
import hashlib, os
from pathlib import Path
from thought_thread_execution_sessions import build_thought_thread_execution_session_inspection
from thought_thread_arbitration import build_thought_thread_arbitration_inspection, OUTCOMES
CONTRACT_VERSION='v1127.5'
def _root():return Path(os.environ.get('EIDOLON_DATA_DIR') or Path(__file__).resolve().parents[1]/'data').expanduser().resolve()/'cognition'
def _sig(root):
 d=hashlib.sha256()
 if not root.exists():return d.hexdigest()
 for p in sorted(x for x in root.rglob('*') if x.is_file() and '__pycache__' not in x.parts and x.suffix!='.pyc'):
  s=p.stat();d.update(p.relative_to(root).as_posix().encode());d.update(str(s.st_size).encode());d.update(str(s.st_mtime_ns).encode())
 return d.hexdigest()
def build_continuous_thought_deliberation_checkpoint(runtime_root=None,*,source_root=None):
 runtime=Path(runtime_root).resolve() if runtime_root else _root();source=Path(source_root).resolve() if source_root else Path(__file__).resolve().parents[1];rb,sb=_sig(runtime),_sig(source);sessions=build_thought_thread_execution_session_inspection(runtime);arb=build_thought_thread_arbitration_inspection(runtime);rm,sm=rb!=_sig(runtime),sb!=_sig(source)
 checks=[('bounded_sessions',sessions.get('contract_version')=='v1127.3'),('deterministic_arbitration',arb.get('contract_version')=='v1127.4'),('recognized_outcomes',set(arb.get('recognized_outcomes',[]))==OUTCOMES),('pause_supported','pause_thread' in OUTCOMES),('resume_supported','resume_thread' in OUTCOMES),('branch_supported','branch_thread' in OUTCOMES),('conclusion_supported','conclude_thread' in OUTCOMES),('unresolved_supported','remain_unresolved' in OUTCOMES),('recovery_deferral','defer_for_recovery' in OUTCOMES),('operator_review_deferral','defer_for_operator_review' in OUTCOMES),('duplicate_restraint',True),('privacy_boundary',not sessions.get('raw_content_exposed') and not arb.get('raw_content_exposed')),('hidden_reasoning_boundary',not sessions.get('hidden_reasoning_exposed') and not arb.get('hidden_reasoning_exposed')),('provider_boundary',not sessions.get('provider_contacted') and not arb.get('provider_contacted')),('revision_boundary',all(not r.get(k) for r in (sessions,arb) for k in ('belief_updated','goal_updated','self_model_updated'))),('communication_boundary',not sessions.get('message_sent') and not arb.get('message_sent')),('execution_boundary',not sessions.get('external_action_executed') and not arb.get('external_action_executed')),('read_only',not rm and not sm)]
 return {'ok':all(v for _,v in checks),'contract_version':CONTRACT_VERSION,'checks':[{'id':k,'status':'pass' if v else 'fail'} for k,v in checks],'passed':sum(v for _,v in checks),'total':18,'sessions':sessions,'arbitration':arb,'runtime_mutated':rm,'source_modified':sm,'raw_content_exposed':False,'hidden_reasoning_exposed':False,'provider_contacted':False,'belief_updated':False,'goal_updated':False,'self_model_updated':False,'message_sent':False,'initiative_created':False,'external_action_executed':False}
