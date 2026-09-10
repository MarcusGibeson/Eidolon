from __future__ import annotations
import argparse,json,tempfile,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from conscious_agent.evidence_change_propagation import EvidenceChangePropagation
from conscious_agent.persistent_motivation import MotivationStore
from conscious_agent.self_directed_inquiry import InquiryWorkspace
from conscious_agent.inquiry_evidence_assimilation import InquiryEvidenceLedger
from conscious_agent.cross_inquiry_evidence_lineage import CrossInquiryEvidenceLineage

def req(v,d='failed'):
 if not v:raise AssertionError(d)
def fix():
 b=Path(tempfile.mkdtemp());r=b/'runtime'/'cognition';m=MotivationStore(r);mid=m.record_motivation('m',kind='curiosity',summary='evidence',cognitive_state='desire',urgency=.8,confidence=.8,origin_type='fixture',origin_ref='v1106.4')['result']['motivation_id'];w=InquiryWorkspace(r,motivation_store=m);a=w.create_inquiry('a',motivation_id=mid,question='A?',uncertainty=.9)['result']['inquiry_id'];c=w.create_inquiry('c',motivation_id=mid,question='C?',uncertainty=.9)['result']['inquiry_id'];l=InquiryEvidenceLedger(r,workspace=w);e=l.assimilate('e',inquiry_id=a,summary='operator fact',source_label='operator',reliability=.9,supports='supports')['result']['evidence_id'];CrossInquiryEvidenceLineage(r,workspace=w,ledger=l).link('x',evidence_id=e,target_inquiry_id=c);return b,r,l,e,a,c
def tests():
 out=[]
 def run(n,f):
  try:f();out.append({'name':n,'status':'pass'})
  except Exception as e:out.append({'name':n,'status':'fail','detail':repr(e)})
 def source_and_target():
  b,r,l,e,a,c=fix();x=EvidenceChangePropagation(r,ledger=l).propagate('p',evidence_id=e);req(x['result']['affected_inquiry_count']==2)
 def assessments():
  b,r,l,e,a,c=fix();x=EvidenceChangePropagation(r,ledger=l).propagate('p',evidence_id=e);req(len(x['receipt']['inquiry_assessments'])==2)
 def duplicate():
  b,r,l,e,a,c=fix();p=EvidenceChangePropagation(r,ledger=l);p.propagate('p',evidence_id=e);req(p.propagate('p',evidence_id=e)['idempotent'])
 def retraction():
  b,r,l,e,a,c=fix();l.retract_evidence('r',evidence_id=e,reason_code='corrected');x=EvidenceChangePropagation(r,ledger=l).propagate('p',evidence_id=e,change_type='retracted');req(x['receipt']['source_active'] is False)
 def restart():
  b,r,l,e,a,c=fix();EvidenceChangePropagation(r,ledger=l).propagate('p',evidence_id=e);req(EvidenceChangePropagation(r,ledger=l).inspection_summary()['propagation_count']==1)
 def no_summary():
  b,r,l,e,a,c=fix();x=EvidenceChangePropagation(r,ledger=l).propagate('p',evidence_id=e);req('operator fact' not in json.dumps(x['receipt']))
 def bounded():
  b,r,l,e,a,c=fix();p=EvidenceChangePropagation(r,ledger=l);[p.propagate(f'p{i}',evidence_id=e) for i in range(3)];req(p.inspection_summary()['propagation_count']==3)
 def provider():
  b,r,l,e,a,c=fix();q=EvidenceChangePropagation(r,ledger=l).inspection_summary();req(q['provider_contacted'] is False)
 def browse():
  b,r,l,e,a,c=fix();q=EvidenceChangePropagation(r,ledger=l).inspection_summary();req(q['external_browsing_performed'] is False)
 def authority():
  b,r,l,e,a,c=fix();q=EvidenceChangePropagation(r,ledger=l).inspection_summary();req(q['authority_boundary']['can_authorize_action'] is False)
 def missing():
  b,r,l,e,a,c=fix();
  try:EvidenceChangePropagation(r,ledger=l).propagate('p',evidence_id='missing')
  except KeyError:return
  raise AssertionError('missing accepted')
 for n,f in [('source_and_target',source_and_target),('assessments',assessments),('duplicate',duplicate),('retraction',retraction),('restart',restart),('no_summary',no_summary),('bounded',bounded),('provider',provider),('browse',browse),('authority',authority),('missing',missing)]:run(n,f)
 return out
if __name__=='__main__':
 argparse.ArgumentParser().add_argument('--json',action='store_true');rows=tests();x={'passed':sum(r['status']=='pass' for r in rows),'total':len(rows),'tests':rows};print(json.dumps(x,indent=2));raise SystemExit(0 if x['passed']==x['total'] else 1)
