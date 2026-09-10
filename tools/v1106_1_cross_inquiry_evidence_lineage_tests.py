from __future__ import annotations
import argparse,json,tempfile,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from conscious_agent.persistent_motivation import MotivationStore
from conscious_agent.self_directed_inquiry import InquiryWorkspace
from conscious_agent.inquiry_evidence_assimilation import InquiryEvidenceLedger
from conscious_agent.cross_inquiry_evidence_lineage import CrossInquiryEvidenceLineage

def req(v,d='failed'):
    if not v:raise AssertionError(d)
def fix():
    r=Path(tempfile.mkdtemp())/'runtime'/'cognition';m=MotivationStore(r);mid=m.record_motivation('m',kind='curiosity',summary='evidence',cognitive_state='desire',urgency=.8,confidence=.8,origin_type='fixture',origin_ref='v1106.1')['result']['motivation_id'];w=InquiryWorkspace(r,motivation_store=m);a=w.create_inquiry('a',motivation_id=mid,question='A?')['result']['inquiry_id'];b=w.create_inquiry('b',motivation_id=mid,question='B?')['result']['inquiry_id'];l=InquiryEvidenceLedger(r,workspace=w);eid=l.assimilate('e',inquiry_id=a,summary='shared fact',source_label='operator',reliability=.9,supports='supports')['result']['evidence_id'];return r,w,l,a,b,eid
def tests():
 out=[]
 def run(n,f):
  try:f();out.append({'name':n,'status':'pass'})
  except Exception as e:out.append({'name':n,'status':'fail','detail':repr(e)})
 def create():
  r,w,l,a,b,e=fix();x=CrossInquiryEvidenceLineage(r,workspace=w,ledger=l).link('x',evidence_id=e,target_inquiry_id=b,relevance=.8);req(x['result']['created'])
 def duplicate():
  r,w,l,a,b,e=fix();s=CrossInquiryEvidenceLineage(r,workspace=w,ledger=l);x=s.link('x',evidence_id=e,target_inquiry_id=b);y=s.link('y',evidence_id=e,target_inquiry_id=b);req(y['result']['created'] is False)
 def retry():
  r,w,l,a,b,e=fix();s=CrossInquiryEvidenceLineage(r,workspace=w,ledger=l);s.link('x',evidence_id=e,target_inquiry_id=b);req(s.link('x',evidence_id=e,target_inquiry_id=b)['idempotent'])
 def source_identity():
  r,w,l,a,b,e=fix();s=CrossInquiryEvidenceLineage(r,workspace=w,ledger=l);s.link('x',evidence_id=e,target_inquiry_id=b);q=s.inspection_summary()['recent_links'][0];req(q['source_identity']['source_label']=='operator' and q['provenance_digest'])
 def retraction_propagates():
  r,w,l,a,b,e=fix();s=CrossInquiryEvidenceLineage(r,workspace=w,ledger=l);s.link('x',evidence_id=e,target_inquiry_id=b);l.retract_evidence('r',evidence_id=e,reason_code='withdrawn');req(s.inspection_summary()['active_link_count']==0)
 def link_retract():
  r,w,l,a,b,e=fix();s=CrossInquiryEvidenceLineage(r,workspace=w,ledger=l);lid=s.link('x',evidence_id=e,target_inquiry_id=b)['result']['link_id'];s.retract('r',link_id=lid,reason_code='not relevant');req(s.inspection_summary()['historical_link_count']==1)
 def contradiction():
  r,w,l,a,b,e=fix();s=CrossInquiryEvidenceLineage(r,workspace=w,ledger=l);s.link('x',evidence_id=e,target_inquiry_id=b,stance='contradicts');req(s.inspection_summary()['recent_links'][0]['stance']=='contradicts')
 def missing():
  r,w,l,a,b,e=fix();
  try:CrossInquiryEvidenceLineage(r,workspace=w,ledger=l).link('x',evidence_id='missing',target_inquiry_id=b);raise AssertionError('not blocked')
  except KeyError:pass
 def persistence():
  r,w,l,a,b,e=fix();CrossInquiryEvidenceLineage(r,workspace=w,ledger=l).link('x',evidence_id=e,target_inquiry_id=b);req(CrossInquiryEvidenceLineage(r,workspace=w,ledger=l).inspection_summary()['active_link_count']==1)
 def boundaries():
  r,w,l,a,b,e=fix();q=CrossInquiryEvidenceLineage(r,workspace=w,ledger=l).inspection_summary();req(q['provider_contacted'] is False and q['authority_boundary']['can_execute_action'] is False)
 def no_payload():
  r,w,l,a,b,e=fix();s=CrossInquiryEvidenceLineage(r,workspace=w,ledger=l);s.link('x',evidence_id=e,target_inquiry_id=b);req('summary' not in s.snapshot()['links'][0])
 for n,f in [('create',create),('duplicate',duplicate),('retry',retry),('source_identity',source_identity),('retraction_propagates',retraction_propagates),('link_retract',link_retract),('contradiction',contradiction),('missing',missing),('persistence',persistence),('boundaries',boundaries),('no_payload',no_payload)]:run(n,f)
 return out
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--json',action='store_true');p.parse_args();rows=tests();x={'passed':sum(r['status']=='pass' for r in rows),'total':len(rows),'tests':rows};print(json.dumps(x,indent=2));raise SystemExit(0 if x['passed']==x['total'] else 1)
