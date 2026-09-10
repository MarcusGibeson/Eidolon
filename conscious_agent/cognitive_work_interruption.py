from __future__ import annotations
"""Bounded interruption, resumption, and stale-work retirement."""
from copy import deepcopy
from cognitive_work_scheduling import CognitiveWorkScheduler, _clean, _digest
CONTRACT_VERSION="v1115.4"
class CognitiveWorkInterruptionManager:
 def __init__(self,runtime_root=None,*,clock=None): self.scheduler=CognitiveWorkScheduler(runtime_root,clock=clock)
 def interrupt(self,event_id:str,*,work_id:str,reason_code:str="higher_priority_admitted",resumable:bool=True,resume_token:str=""):
  state="resumable" if resumable else "paused"; result=self.scheduler.transition(event_id,work_id=work_id,state=state,progress_digest=_digest(resume_token) if resume_token else "",reason_code=reason_code)
  if result.get("result",{}).get("work_id"):
   with __import__('conscious_agent.metadata_mutation_coordination',fromlist=['metadata_mutation_lock']).metadata_mutation_lock(self.scheduler.path,timeout_seconds=5):
    s=self.scheduler._load(); row=next(x for x in s['work_items'] if x.get('work_id')==work_id); row['interrupt_count']=int(row.get('interrupt_count',0))+1; row['resume_token_digest']=_digest(resume_token) if resume_token else row.get('resume_token_digest',''); __import__('conscious_agent.json_storage',fromlist=['write_json_atomic']).write_json_atomic(self.scheduler.path,s,expected_type=dict,sort_keys=True)
  return result
 def resume(self,event_id:str,*,work_id:str,resume_token:str=""):
  s=self.scheduler.snapshot(); row=next((x for x in s['work_items'] if x.get('work_id')==work_id),None)
  if not row or row.get('state') not in {'resumable','paused'}: return {"ok":True,"status":"resume_rejected","result":{"reason":"work_not_resumable","work_id":work_id},"idempotent":False}
  expected=row.get('resume_token_digest') or ''; supplied=_digest(resume_token) if resume_token else ''
  if expected and expected!=supplied: return {"ok":True,"status":"resume_rejected","result":{"reason":"resume_token_mismatch","work_id":work_id},"idempotent":False}
  result=self.scheduler.transition(event_id,work_id=work_id,state='scheduled',reason_code='bounded_resume')
  if result.get('result',{}).get('work_id'):
   from metadata_mutation_coordination import metadata_mutation_lock
   from json_storage import write_json_atomic
   with metadata_mutation_lock(self.scheduler.path,timeout_seconds=5):
    s=self.scheduler._load(); row=next(x for x in s['work_items'] if x.get('work_id')==work_id); row['resume_count']=int(row.get('resume_count',0))+1; write_json_atomic(self.scheduler.path,s,expected_type=dict,sort_keys=True)
  return result
 def retire_stale(self,event_id:str,*,work_id:str,stale:bool,dependency_valid:bool=True):
  if not stale:return {"ok":True,"status":"retirement_not_required","result":{"work_id":work_id,"reason":"work_not_stale"},"idempotent":False}
  state='retired' if dependency_valid else 'stale'; reason='stale_work_retired' if dependency_valid else 'dependency_invalidated'
  return self.scheduler.transition(event_id,work_id=work_id,state=state,reason_code=reason)
 def inspection_summary(self):
  x=self.scheduler.inspection_summary(); x.update({"contract_version":CONTRACT_VERSION,"bounded_interruptions":True,"resume_requires_matching_token":True,"stale_work_loses_active_influence":True,"interruption_grants_authority":False,"automatic_external_action":False}); return x
def build_cognitive_work_interruption_inspection(runtime_root=None): return CognitiveWorkInterruptionManager(runtime_root).inspection_summary()
