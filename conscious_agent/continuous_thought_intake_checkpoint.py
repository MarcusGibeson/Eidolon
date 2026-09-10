from __future__ import annotations
"""Strictly read-only v1127.2 Continuous Thought Intake checkpoint."""
import hashlib, os
from pathlib import Path
from continuous_thought_threads import build_continuous_thought_thread_inspection, STATES
from thought_thread_continuity import build_thought_thread_continuity_review
CONTRACT_VERSION='v1127.2'
def _root(): return Path(os.environ.get('EIDOLON_DATA_DIR') or Path(__file__).resolve().parents[1]/'data').expanduser().resolve()/'cognition'
def _sig(root:Path):
 d=hashlib.sha256()
 if not root.exists(): return d.hexdigest()
 for p in sorted(x for x in root.rglob('*') if x.is_file() and '__pycache__' not in x.parts and x.suffix!='.pyc'):
  s=p.stat();d.update(p.relative_to(root).as_posix().encode());d.update(str(s.st_size).encode());d.update(str(s.st_mtime_ns).encode())
 return d.hexdigest()
def build_continuous_thought_intake_checkpoint(runtime_root=None,*,source_root=None):
 runtime=Path(runtime_root).resolve() if runtime_root else _root();source=Path(source_root).resolve() if source_root else Path(__file__).resolve().parents[1];rb=_sig(runtime);sb=_sig(source);threads=build_continuous_thought_thread_inspection(runtime);continuity=build_thought_thread_continuity_review(runtime)
 checks=[
 ('thread_contract',threads.get('contract_version')=='v1127.0'),('continuity_contract',continuity.get('contract_version')=='v1127.1'),('durable_lineage',all(x.get('root_reflection_outcome_id') and x.get('structural_digest') for x in threads.get('recent_threads',[]))),('pause_supported','paused' in STATES),('resume_supported','resumable' in STATES),('branch_supported','branched' in STATES),('conclusion_supported','concluded' in STATES),('unresolved_supported','unresolved' in STATES),('restart_continuity',continuity.get('restart_continuity_supported') is True),('day_scale_continuity',continuity.get('day_scale_continuity_supported') is True),('resume_tokens_content_free',all(x.get('resume_token_digest') for x in threads.get('recent_threads',[]))),('parent_branch_lineage',all(isinstance(x.get('branch_ids'),list) for x in threads.get('recent_threads',[]))),('privacy_boundary',not threads.get('raw_content_exposed') and not threads.get('conclusions_exposed') and not threads.get('hidden_reasoning_exposed')),('provider_boundary',not threads.get('provider_contacted') and not continuity.get('provider_contacted')),('revision_boundary',not threads.get('belief_updated') and not threads.get('goal_updated') and not threads.get('self_model_updated')),('communication_boundary',not threads.get('message_sent') and not threads.get('initiative_created')),('execution_boundary',not threads.get('external_action_executed')),('read_only',rb==_sig(runtime) and sb==_sig(source))]
 return {'ok':all(v for _,v in checks),'contract_version':CONTRACT_VERSION,'checks':[{'id':k,'status':'pass' if v else 'fail'} for k,v in checks],'threads':threads,'continuity':continuity,'runtime_mutated':rb!=_sig(runtime),'source_modified':sb!=_sig(source),'raw_content_exposed':False,'conclusions_exposed':False,'hidden_reasoning_exposed':False,'provider_contacted':False,'belief_updated':False,'goal_updated':False,'self_model_updated':False,'message_sent':False,'initiative_created':False,'external_action_executed':False}
