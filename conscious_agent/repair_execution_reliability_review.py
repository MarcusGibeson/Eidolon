from __future__ import annotations
"""v1141.7 structural result lineage, contamination, and repeated-failure review."""
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
import hashlib, os
from pathlib import Path
from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
from sandbox_repair_execution import SandboxRepairExecutionStore
from repair_execution_continuity import RepairExecutionContinuityStore
CONTRACT_VERSION='v1141.7'; SCHEMA_VERSION='1'
def _now(): return datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00','Z')
def _clean(v,n=240): return ' '.join(str(v or '').split())[:n]
def _digest(*parts): return hashlib.sha256('\x1f'.join(_clean(p,4000) for p in parts).encode()).hexdigest()
def _root(): return Path(os.environ.get('EIDOLON_DATA_DIR') or Path(__file__).resolve().parents[1]/'data').expanduser().resolve()/'cognition'
def _default(): return {'schema_version':SCHEMA_VERSION,'contract_version':CONTRACT_VERSION,'reviews':[],'processed_events':[],'revision':0,'updated_at':''}
class RepairExecutionReliabilityReviewStore:
 def __init__(self,runtime_root=None): self.runtime_root=Path(runtime_root).resolve() if runtime_root else _root(); self.path=self.runtime_root/'repair_execution_reliability_reviews.json'; self.executions=SandboxRepairExecutionStore(self.runtime_root); self.continuity=RepairExecutionContinuityStore(self.runtime_root)
 def _load(self):
  s=load_json_file(self.path,_default(),expected_type=dict)
  for k,v in _default().items(): s.setdefault(k,deepcopy(v))
  return s
 def review(self,event_id:str,*,workspace_contamination_digests:list[str]|None=None):
  now=_now(); contamination=sorted(set(_clean(x,128) for x in (workspace_contamination_digests or []) if _clean(x,128)))
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   s=self._load(); prior=next((x for x in s['processed_events'] if x.get('event_id')==_clean(event_id,180)),None)
   if prior: return {'ok':True,**deepcopy(prior['result']),'idempotent':True}
   exs=self.executions.snapshot().get('executions',[]); counts=Counter(x.get('status','unknown') for x in exs); failed=[x for x in exs if x.get('status') in {'failed','timed_out'}]
   lineage=[{'execution_id':x.get('execution_id',''),'candidate_change_id':x.get('candidate_change_id',''),'materialization_id':x.get('materialization_id',''),'status':x.get('status',''),'structural_digest':x.get('structural_digest',''),'result_count':len(x.get('result_records',[]))} for x in exs]
   repeated=len(failed)>=2; finding='contamination_detected' if contamination else 'repeated_failure' if repeated else 'supported' if counts.get('completed') else 'insufficient_evidence'
   rid=f'repair-reliability-{_digest(event_id,finding,*[x["structural_digest"] for x in lineage])[:24]}'; row={'review_id':rid,'finding':finding,'execution_count':len(exs),'completed_count':counts.get('completed',0),'failure_count':len(failed),'cancelled_count':counts.get('cancelled',0),'repeated_failure':repeated,'contamination_detected':bool(contamination),'contamination_digest_count':len(contamination),'contamination_digests':contamination,'result_lineage':lineage,'operator_candidate_evidence_ready':bool(lineage) and not contamination,'installation_eligible':False,'approval_created':False,'authorization_created':False,'promotion_created':False,'certification_created':False,'source_modified':False,'installation_modified':False,'created_at':now}; row['structural_digest']=_digest(rid,finding,*[x['structural_digest'] for x in lineage],*contamination)
   s['reviews'].append(row); result={'status':'reviewed','review_id':rid,'finding':finding}; s['processed_events'].append({'event_id':_clean(event_id,180),'result':deepcopy(result),'occurred_at':now}); s['revision']+=1; s['updated_at']=now; write_json_atomic(self.path,s,expected_type=dict,sort_keys=True); return {'ok':True,**result,'idempotent':False}
 def inspection_summary(self):
  s=self._load(); return {'ok':True,'contract_version':CONTRACT_VERSION,'review_count':len(s['reviews']),'recent_reviews':deepcopy(s['reviews'][-24:]),'operator_candidate_evidence_only':True,'installation_eligible':False,'raw_source_exposed':False,'patch_text_exposed':False,'commands_exposed':False,'logs_exposed':False,'hidden_reasoning_exposed':False,'source_modified':False,'installation_modified':False,'approval_created':False,'authorization_created':False,'promotion_created':False,'certification_created':False}
def build_repair_execution_reliability_review_inspection(runtime_root=None): return RepairExecutionReliabilityReviewStore(runtime_root).inspection_summary()
