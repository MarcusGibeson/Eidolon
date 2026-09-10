from __future__ import annotations

"""v2506.2-v2506.5 bounded memory consolidation/revision candidate planning."""

from copy import deepcopy
from datetime import datetime,timezone
import hashlib,json
from pathlib import Path
from typing import Any,Callable,Mapping

from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
from unified_memory_roles_v2506 import MEMORY_ROLES, verify_unified_memory_role_projection

CONTRACT_VERSION="v2506.5";SCHEMA_VERSION="1"
CANDIDATE_TYPES=frozenset({"EPISODIC_PATTERN_REVIEW","SEMANTIC_STABILITY_REVIEW","RELATIONSHIP_STABILITY_REVIEW","PROCEDURAL_LESSON_REVIEW","AUTOBIOGRAPHICAL_CONTINUITY_REVIEW","MEMORY_CONFLICT_REVISION_REVIEW","DUPLICATE_CONSOLIDATION_REVIEW"})

def _now():return datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00','Z')
def _digest(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()
def _default():return {'schema_version':SCHEMA_VERSION,'contract_version':CONTRACT_VERSION,'candidates':[],'processed_events':[],'revision':0,'updated_at':'','controls':{'max_candidates':512},'authority_boundary':{'can_write_memory':False,'can_delete_memory':False,'can_retract_memory':False,'can_apply_candidate':False,'can_train_model':False,'can_contact_provider':False,'operator_review_required':True}}

def derive_memory_consolidation_candidates(role_projection:Mapping[str,Any])->dict[str,Any]:
    if not verify_unified_memory_role_projection(role_projection):raise ValueError('valid memory role projection required')
    counts=role_projection.get('role_counts') if isinstance(role_projection.get('role_counts'),Mapping) else {}
    rows=[]
    def add(kind,role,reason,confidence=.6):
        rows.append({'candidate_type':kind,'role':role,'reason_code':reason,'confidence':round(float(confidence),3),'review_required':True,'memory_mutation_performed':False})
    if int(role_projection.get('conflict_groups_detected') or 0)>0:add('MEMORY_CONFLICT_REVISION_REVIEW','semantic','conflicting_fact_group_present',.8)
    if int(role_projection.get('duplicate_references_omitted') or 0)>0:add('DUPLICATE_CONSOLIDATION_REVIEW','semantic','duplicate_reference_evidence_present',.72)
    if int(counts.get('episodic') or 0)>=2:add('EPISODIC_PATTERN_REVIEW','episodic','multiple_grounded_episodes_present',.62)
    if int(counts.get('semantic') or 0)>=1:add('SEMANTIC_STABILITY_REVIEW','semantic','grounded_semantic_reference_present',.66)
    if int(counts.get('relational') or 0)>=1:add('RELATIONSHIP_STABILITY_REVIEW','relational','relationship_continuity_reference_present',.66)
    if int(counts.get('procedural') or 0)>=1:add('PROCEDURAL_LESSON_REVIEW','procedural','procedural_or_lesson_reference_present',.64)
    if int(counts.get('autobiographical') or 0)>=1:add('AUTOBIOGRAPHICAL_CONTINUITY_REVIEW','autobiographical','eidolon_owned_continuity_reference_present',.62)
    payload={'contract_version':CONTRACT_VERSION,'source_projection_digest':role_projection['projection_digest'],'candidate_count':len(rows),'candidates':rows,'provenance_preserved':True,'historical_truth_preserved':True,'automatic_forgetting_permitted':False,'candidate_applied':False,'memory_mutated':False,'provider_contacted':False,'authority':'none'}
    payload['candidate_set_digest']=_digest(payload);return payload

class MemoryConsolidationCandidateStore:
    def __init__(self,runtime_root:str|Path,*,clock:Callable[[],str]|None=None):self.root=Path(runtime_root).expanduser().resolve();self.path=self.root/'memory_consolidation_candidates_v2506.json';self.clock=clock or _now
    def _load(self):
        s=load_json_file(self.path,_default(),expected_type=dict)
        if s.get('schema_version')!=SCHEMA_VERSION:s=_default()
        for k,v in _default().items():s.setdefault(k,deepcopy(v))
        return s
    def record(self,event_id:str,candidate_set:Mapping[str,Any]):
        event_id=str(event_id or '').strip()[:180]
        if not event_id or not isinstance(candidate_set,Mapping) or len(str(candidate_set.get('candidate_set_digest') or ''))!=64:raise ValueError('event_id and candidate set required')
        with metadata_mutation_lock(self.path,timeout_seconds=5):
            s=self._load();prior=next((x for x in s['processed_events'] if x.get('event_id')==event_id),None)
            if prior:return {'ok':True,'status':'candidate_set_replayed','idempotent':True,'record_id':prior['record_id'],'candidate_applied':False}
            now=self.clock();rid='memory-consolidation-'+_digest({'event':event_id,'set':candidate_set['candidate_set_digest']})[:24]
            row={'record_id':rid,'source_projection_digest':str(candidate_set.get('source_projection_digest') or ''),'candidate_set_digest':str(candidate_set['candidate_set_digest']),'candidate_types':[str(x.get('candidate_type') or '') for x in candidate_set.get('candidates',[]) if isinstance(x,Mapping)][:16],'candidate_count':int(candidate_set.get('candidate_count') or 0),'status':'awaiting_operator_or_governed_memory_review','created_at':now,'candidate_applied':False,'memory_mutated':False,'historical_truth_preserved':True}
            s['candidates']=(s['candidates']+[row])[-int(s['controls']['max_candidates']):];s['processed_events']=(s['processed_events']+[{'event_id':event_id,'event_digest':_digest(event_id),'record_id':rid,'occurred_at':now,'content_free':True}])[-1024:];s['revision']+=1;s['updated_at']=now;write_json_atomic(self.path,s,expected_type=dict,sort_keys=True)
            return {'ok':True,'status':'memory_consolidation_candidates_recorded','record_id':rid,'candidate_count':row['candidate_count'],'candidate_applied':False,'memory_mutated':False,'idempotent':False}
    def inspection_summary(self):
        s=self._load();return {'ok':True,'contract_version':CONTRACT_VERSION,'revision':s['revision'],'candidate_set_count':len(s['candidates']),'recent_candidate_sets':deepcopy(s['candidates'][-32:]),'authority_boundary':deepcopy(s['authority_boundary']),'memory_mutated':False,'candidate_applied':False,'provider_contacted':False}

__all__=['CONTRACT_VERSION','CANDIDATE_TYPES','derive_memory_consolidation_candidates','MemoryConsolidationCandidateStore']
