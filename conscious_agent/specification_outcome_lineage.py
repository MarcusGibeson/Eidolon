from __future__ import annotations
"""v1137.6 content-free specification outcome lineage and continuity."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib, os
from pathlib import Path
from typing import Any, Callable
from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
from specification_arbitration import SpecificationArbitrationStore
CONTRACT_VERSION='v1137.6'; SCHEMA_VERSION='1'
STATES={'active','continued','superseded','stale','retracted','retired'}
def _now(): return datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00','Z')
def _clean(v:Any,n=240): return ' '.join(str(v or '').split())[:n]
def _digest(*p:Any): return hashlib.sha256('\x1f'.join(_clean(x,3000) for x in p).encode()).hexdigest()
def _root(): return Path(os.environ.get('EIDOLON_DATA_DIR') or Path(__file__).resolve().parents[1]/'data').expanduser().resolve()/'cognition'
def _default(): return {'schema_version':SCHEMA_VERSION,'contract_version':CONTRACT_VERSION,'lineage':[],'processed_events':[],'revision':0,'updated_at':'','authority_boundary':{k:False for k in ('can_write_specification_text','can_modify_source','can_create_specification','can_create_test_plan','can_create_sandbox','can_run_tests','can_approve','can_authorize','can_execute','can_promote','can_certify')}}
class SpecificationOutcomeLineageStore:
 def __init__(self,runtime_root=None,*,clock:Callable[[],str]|None=None): self.runtime_root=Path(runtime_root).resolve() if runtime_root else _root(); self.path=self.runtime_root/'specification_outcome_lineage.json'; self.clock=clock or _now; self.arbitration=SpecificationArbitrationStore(self.runtime_root)
 def _load(self):
  s=load_json_file(self.path,_default(),expected_type=dict)
  for k,v in _default().items(): s.setdefault(k,deepcopy(v))
  return s
 def record(self,event_id:str,*,arbitration_id:str,predecessor_lineage_ids=None,continuity_context='restart',state='active',supersedes_ids=None,retraction_ids=None):
  outcome=next((x for x in self.arbitration.inspection_summary().get('recent_outcomes',[]) if x.get('arbitration_id')==arbitration_id),None)
  if not outcome: raise ValueError('development proposal arbitration outcome required')
  state=state if state in STATES else 'active'; predecessors=[_clean(x,180) for x in (predecessor_lineage_ids or []) if _clean(x,180)]; supersedes=[_clean(x,180) for x in (supersedes_ids or []) if _clean(x,180)]; retracts=[_clean(x,180) for x in (retraction_ids or []) if _clean(x,180)]
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   s=self._load(); prior=next((x for x in s['processed_events'] if x.get('event_id')==event_id),None)
   if prior:return {'ok':True,**deepcopy(prior['result']),'idempotent':True}
   lid='dev-proposal-lineage-'+_digest(arbitration_id,*predecessors,*supersedes,*retracts)[:20]; existing=next((x for x in s['lineage'] if x.get('lineage_id')==lid),None)
   if existing: result={'status':'specification_outcome_lineage_reused','lineage_id':lid}
   else:
    now=self.clock(); rec={'lineage_id':lid,'arbitration_id':arbitration_id,'candidate_id':outcome.get('candidate_id'),'eligibility_ids':outcome.get('eligibility_ids',[]),'deficiency_candidate_ids':outcome.get('deficiency_candidate_ids',[]),'specification_categories':outcome.get('specification_categories',[]),'component_ids':outcome.get('component_ids',[]),'project_digests':outcome.get('project_digests',[]),'scope_digests':outcome.get('scope_digests',[]),'evidence_ids':outcome.get('evidence_ids',[]),'outcome':outcome.get('outcome'),'predecessor_lineage_ids':predecessors,'supersedes_ids':supersedes,'retraction_ids':retracts,'continuity_context':_clean(continuity_context,80),'state':state,'created_at':now,'structural_digest':_digest(arbitration_id,outcome.get('outcome'),*predecessors,*supersedes,*retracts),'specification_text_digest':'','specification_id':'','test_plan_id':'','sandbox_change_id':'','approval_id':'','authorization_id':'','execution_id':'','promotion_id':'','certification_id':''}; s['lineage'].append(rec); result={'status':'specification_outcome_lineage_recorded','lineage_id':lid}
   now=self.clock(); s['processed_events'].append({'event_id':_clean(event_id,180),'occurred_at':now,'result':deepcopy(result),'content_free':True}); s['revision']+=1;s['updated_at']=now;write_json_atomic(self.path,s,expected_type=dict,sort_keys=True);return {'ok':True,**result,'idempotent':False}
 def inspection_summary(self):
  s=self._load(); return {'ok':True,'contract_version':CONTRACT_VERSION,'lineage_count':len(s['lineage']),'recognized_states':sorted(STATES),'recent_lineage':deepcopy(s['lineage'][-24:]),'authority_boundary':deepcopy(s['authority_boundary']),'specification_text_exposed':False,'raw_source_exposed':False,'evidence_text_exposed':False,'hidden_reasoning_exposed':False,'provider_contacted':False,'external_action_executed':False}
def build_specification_outcome_lineage_inspection(runtime_root=None): return SpecificationOutcomeLineageStore(runtime_root).inspection_summary()
