from __future__ import annotations
"""v1127.1 restart-safe thought-thread continuity and lifecycle review."""
from copy import deepcopy
from datetime import datetime, timezone
import os
from pathlib import Path
from typing import Any
from continuous_thought_threads import ContinuousThoughtThreadStore
CONTRACT_VERSION='v1127.1'
def _now(): return datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00','Z')
def _root(): return Path(os.environ.get('EIDOLON_DATA_DIR') or Path(__file__).resolve().parents[1]/'data').expanduser().resolve()/'cognition'
class ThoughtThreadContinuityReview:
 def __init__(self,runtime_root=None): self.runtime_root=Path(runtime_root).resolve() if runtime_root else _root();self.threads=ContinuousThoughtThreadStore(self.runtime_root)
 def review(self,*,now:str|None=None):
  snap=self.threads.snapshot();rows=[]
  for t in snap.get('threads',[]):
   state=t.get('state');history=t.get('history') or [];status='stable'
   if state=='paused': status='resume_available'
   elif state=='resumable': status='resume_pending'
   elif state=='branched': status='branch_continuity'
   elif state=='unresolved': status='unresolved_continuity'
   elif state=='concluded': status='concluded'
   rows.append({'thread_id':t.get('thread_id'),'state':state,'status':status,'history_count':len(history),'parent_thread_id':t.get('parent_thread_id'),'branch_count':len(t.get('branch_ids') or []),'resume_token_digest':t.get('resume_token_digest'),'continuity_horizon_days':t.get('continuity_horizon_days'),'updated_at':t.get('updated_at')})
  return {'ok':True,'contract_version':CONTRACT_VERSION,'reviewed_at':now or _now(),'thread_count':len(rows),'reviews':rows,'restart_continuity_supported':True,'day_scale_continuity_supported':True,'raw_content_exposed':False,'hidden_reasoning_exposed':False,'provider_contacted':False,'belief_updated':False,'goal_updated':False,'self_model_updated':False,'message_sent':False,'initiative_created':False,'external_action_executed':False}
def build_thought_thread_continuity_review(runtime_root=None): return ThoughtThreadContinuityReview(runtime_root).review()
