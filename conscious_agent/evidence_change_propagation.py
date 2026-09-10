from __future__ import annotations
"""Deterministic propagation of evidence changes to affected inquiry and belief health."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib, os
from pathlib import Path
try:
    from json_storage import load_json_file, write_json_atomic
    from metadata_mutation_coordination import metadata_mutation_lock
    from inquiry_evidence_assimilation import InquiryEvidenceLedger
    from cross_inquiry_evidence_lineage import CrossInquiryEvidenceLineage
    from inquiry_evidence_quality import InquiryEvidenceQuality
    from belief_revision import BeliefRevisionStore
except ImportError:
    from json_storage import load_json_file, write_json_atomic
    from metadata_mutation_coordination import metadata_mutation_lock
    from inquiry_evidence_assimilation import InquiryEvidenceLedger
    from cross_inquiry_evidence_lineage import CrossInquiryEvidenceLineage
    from inquiry_evidence_quality import InquiryEvidenceQuality
    from belief_revision import BeliefRevisionStore
CONTRACT_VERSION='v1106.4';SCHEMA_VERSION='1'
def _now():return datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00','Z')
def _clean(v,l=300):return ' '.join(str(v or '').split())[:l]
def _digest(*p):return hashlib.sha256('\x1f'.join(_clean(x,2000) for x in p).encode()).hexdigest()
def _root():return Path(os.environ.get('EIDOLON_DATA_DIR') or Path(__file__).resolve().parents[1]/'data').expanduser().resolve()/'cognition'
def _default():return {'schema_version':SCHEMA_VERSION,'contract_version':CONTRACT_VERSION,'receipts':[],'processed_events':[],'revision':0,'updated_at':'','authority_boundary':{'can_authorize_action':False,'can_execute_action':False,'can_browse_externally':False,'can_manage_models':False}}
class EvidenceChangePropagation:
    def __init__(self,runtime_root=None,*,ledger=None,lineage=None,quality=None,beliefs=None):
        self.runtime_root=Path(runtime_root).expanduser().resolve() if runtime_root else _root();self.path=self.runtime_root/'evidence_change_propagation.json';self.ledger=ledger or InquiryEvidenceLedger(self.runtime_root);self.lineage=lineage or CrossInquiryEvidenceLineage(self.runtime_root,ledger=self.ledger);self.quality=quality or InquiryEvidenceQuality(self.runtime_root,ledger=self.ledger);self.beliefs=beliefs or BeliefRevisionStore(self.runtime_root)
    def _load(self):
        s=load_json_file(self.path,_default(),expected_type=dict)
        for k,v in _default().items():s.setdefault(k,deepcopy(v))
        return s
    def propagate(self,event_id,*,evidence_id:str,change_type:str='updated'):
        event_id=_clean(event_id,160);evidence_id=_clean(evidence_id,120);change_type=_clean(change_type,80)
        if not event_id or not evidence_id:raise ValueError('event_id and evidence_id are required')
        with metadata_mutation_lock(self.path,timeout_seconds=5.0):
            s=self._load();prior=next((r for r in s['processed_events'] if r.get('event_id')==event_id),None)
            if prior:return {'ok':True,'status':'duplicate_propagation_ignored','result':deepcopy(prior['result']),'idempotent':True}
            evidence=next((r for r in self.ledger.snapshot().get('evidence') or [] if r.get('evidence_id')==evidence_id),None)
            if not evidence:raise KeyError('evidence not found')
            affected={str(evidence.get('inquiry_id') or '')}
            links=self.lineage.snapshot().get('links') or []
            for link in links:
                if link.get('evidence_id')==evidence_id and link.get('active') is True: affected.add(str(link.get('target_inquiry_id') or ''))
            affected.discard('');assessments=[]
            for inquiry_id in sorted(affected):
                try:r=self.quality.assess(f'{event_id}:quality:{inquiry_id}',inquiry_id=inquiry_id);assessments.append(r.get('result') or {})
                except Exception as exc:assessments.append({'inquiry_id':inquiry_id,'status':'assessment_unavailable','error_type':type(exc).__name__})
            belief_updates=[];digest=_digest(evidence_id)
            for belief in self.beliefs.snapshot().get('beliefs') or []:
                matches=[row for row in belief.get('evidence') or [] if row.get('reference_digest')==digest or row.get('evidence_id')==evidence_id]
                for row in matches:
                    desired=bool(evidence.get('active'))
                    if bool(row.get('active'))!=desired:
                        if not desired:
                            out=self.beliefs.retract_evidence(f'{event_id}:belief:{belief["belief_id"]}:{row["evidence_id"]}',belief_id=belief['belief_id'],evidence_id=row['evidence_id'],correction_ref=f'propagated:{evidence_id}:{change_type}')
                            belief_updates.append(out.get('result') or {})
            now=_now();receipt={'receipt_id':'propagation-'+_digest(event_id,evidence_id)[:28],'evidence_id':evidence_id,'change_type':change_type,'source_active':bool(evidence.get('active')),'affected_inquiry_ids':sorted(affected),'inquiry_assessments':assessments,'belief_updates':belief_updates,'provider_contacted':False,'external_browsing_performed':False,'action_authorized':False,'action_executed':False,'occurred_at':now};s['receipts']=(s['receipts']+[receipt])[-256:];result={'status':'evidence_change_propagated','receipt_id':receipt['receipt_id'],'affected_inquiry_count':len(affected),'belief_update_count':len(belief_updates),'action_authorized':False,'action_executed':False};s['processed_events']=(s['processed_events']+[{'event_id':event_id,'result':deepcopy(result),'occurred_at':now}])[-512:];s['revision']+=1;s['updated_at']=now;write_json_atomic(self.path,s,expected_type=dict,sort_keys=True);return {'ok':True,'status':result['status'],'result':result,'receipt':receipt,'idempotent':False}
    def inspection_summary(self):
        s=self._load();return {'ok':True,'contract_version':CONTRACT_VERSION,'propagation_count':len(s['receipts']),'recent_receipts':deepcopy(s['receipts'][-8:]),'provider_contacted':False,'external_browsing_performed':False,'hidden_reasoning_exposed':False,'authority_boundary':deepcopy(s['authority_boundary'])}
def build_evidence_change_propagation_inspection(runtime_root=None):return EvidenceChangePropagation(runtime_root).inspection_summary()
