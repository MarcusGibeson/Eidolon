from __future__ import annotations
"""Bounded evidence quality, corroboration, contradiction, and inquiry uncertainty updates."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib, os
from pathlib import Path
from typing import Any, Callable
try:
    from json_storage import load_json_file, write_json_atomic
    from metadata_mutation_coordination import metadata_mutation_lock
    from inquiry_evidence_assimilation import InquiryEvidenceLedger
    from self_directed_inquiry import InquiryWorkspace
except ImportError:
    from json_storage import load_json_file, write_json_atomic
    from metadata_mutation_coordination import metadata_mutation_lock
    from inquiry_evidence_assimilation import InquiryEvidenceLedger
    from self_directed_inquiry import InquiryWorkspace
CONTRACT_VERSION='v1105.6'; SCHEMA_VERSION='1'
def _now(): return datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00','Z')
def _clean(v,limit=700): return ' '.join(str(v or '').split())[:limit]
def _digest(*parts): return hashlib.sha256('\x1f'.join(_clean(p,2000) for p in parts).encode()).hexdigest()
def _root(): return Path(os.environ.get('EIDOLON_DATA_DIR') or Path(__file__).resolve().parents[1]/'data').expanduser().resolve()/'cognition'
def _default(): return {'schema_version':SCHEMA_VERSION,'contract_version':CONTRACT_VERSION,'assessments':[],'processed_events':[],'revision':0,'updated_at':'','authority_boundary':{'can_browse_externally':False,'can_authorize_action':False,'can_execute_action':False,'operator_authority_unchanged':True}}
class InquiryEvidenceQuality:
    def __init__(self,runtime_root=None,*,ledger=None,workspace=None,clock:Callable[[],str]|None=None):
        self.runtime_root=Path(runtime_root).expanduser().resolve() if runtime_root else _root(); self.path=self.runtime_root/'inquiry_evidence_quality.json'; self.workspace=workspace or InquiryWorkspace(self.runtime_root); self.ledger=ledger or InquiryEvidenceLedger(self.runtime_root,workspace=self.workspace); self.clock=clock or _now
    def _load(self):
        s=load_json_file(self.path,_default(),expected_type=dict)
        for k,v in _default().items(): s.setdefault(k,deepcopy(v))
        return s
    def snapshot(self): return deepcopy(self._load())
    def assess(self,event_id,*,inquiry_id:str):
        event_id=_clean(event_id,160); inquiry_id=_clean(inquiry_id,120)
        if not event_id or not inquiry_id: raise ValueError('event_id and inquiry_id are required')
        inquiry=next((r for r in self.workspace.snapshot()['inquiries'] if r.get('inquiry_id')==inquiry_id),None)
        if not inquiry: raise KeyError('inquiry not found')
        with metadata_mutation_lock(self.path,timeout_seconds=5.0):
            s=self._load(); prior=next((r for r in s['processed_events'] if r.get('event_id')==event_id),None)
            if prior:return {'ok':True,'status':'duplicate_event_ignored','result':deepcopy(prior['result']),'idempotent':True}
            rows=[r for r in self.ledger.snapshot()['evidence'] if r.get('inquiry_id')==inquiry_id and r.get('active')]
            supports=[r for r in rows if _clean(r.get('supports'),180).lower() not in {'','contradicts','against','refutes'}]
            contradicts=[r for r in rows if _clean(r.get('supports'),180).lower() in {'contradicts','against','refutes'}]
            source_groups={_clean(r.get('source_label'),180).casefold() for r in rows}
            support_weight=sum(float(r.get('reliability') or 0) for r in supports)
            contradiction_weight=sum(float(r.get('reliability') or 0) for r in contradicts)
            corroboration=min(1.0,len(source_groups)/3.0)
            quality=round(min(1.0,(support_weight+contradiction_weight)/max(1,len(rows))*0.7+corroboration*0.3),4) if rows else 0.0
            conflict=bool(supports and contradicts)
            prior_uncertainty=float(inquiry.get('uncertainty') or .5)
            certainty_gain=min(.45,quality*.35) if rows else 0.0
            conflict_penalty=min(.35,contradiction_weight*.15) if conflict else 0.0
            uncertainty=round(max(0,min(1,prior_uncertainty-certainty_gain+conflict_penalty)),4)
            now=self.clock(); result={'status':'evidence_quality_assessed','inquiry_id':inquiry_id,'active_evidence_count':len(rows),'independent_source_count':len(source_groups),'support_count':len(supports),'contradiction_count':len(contradicts),'contradiction_present':conflict,'quality_score':quality,'prior_uncertainty':prior_uncertainty,'updated_uncertainty':uncertainty,'provider_contacted':False,'external_browsing_performed':False,'action_authorized':False}
            s['assessments'].append(dict(result,assessment_id='assessment-'+_digest(event_id)[:20],occurred_at=now,evidence_reference_digests=[_digest(r.get('evidence_id')) for r in rows]));s['revision']+=1;s['updated_at']=now;s['processed_events']=(s['processed_events']+[{'event_id':event_id,'event_digest':_digest(event_id),'result':deepcopy(result),'occurred_at':now}])[-512:];write_json_atomic(self.path,s,expected_type=dict,sort_keys=True)
            self.workspace.add_progress(event_id+'-uncertainty',inquiry_id=inquiry_id,conclusion='Evidence quality was assessed with contradiction and corroboration kept explicit.',supporting_refs=[r.get('evidence_id','') for r in rows],uncertainty_after=uncertainty,next_question=inquiry.get('question',''))
            return {'ok':True,'status':result['status'],'result':result,'idempotent':False}
    def inspection_summary(self):
        s=self._load();return {'ok':True,'contract_version':CONTRACT_VERSION,'assessment_count':len(s['assessments']),'recent_assessments':deepcopy(s['assessments'][-8:]),'provider_contacted':False,'external_browsing_performed':False,'action_authority_changed':False,'authority_boundary':deepcopy(s['authority_boundary'])}
def build_inquiry_evidence_quality_inspection(runtime_root=None): return InquiryEvidenceQuality(runtime_root).inspection_summary()
