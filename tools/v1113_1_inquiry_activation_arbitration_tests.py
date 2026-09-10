from pathlib import Path
import json,tempfile
from conscious_agent.active_inquiry_records import ActiveInquiryStore
from conscious_agent.inquiry_activation_arbitration import InquiryActivationArbitrator

def req(v):
 if not v: raise AssertionError()
def seed(root,cid='c1'):
 (root/'curiosity_inquiry_promotions.json').write_text(json.dumps({'schema_version':'1','contract_version':'v1111.6','promotions':[{'inquiry_candidate_id':cid,'semantic_key':'s1','decision_id':'d1','question_id':'q1','project_digest':'p1','state':'candidate'}],'processed_events':[],'revision':1,'updated_at':'','controls':{'max_candidates':256,'max_active':48},'state_separation':{},'authority_boundary':{}}))
with tempfile.TemporaryDirectory() as td:
 root=Path(td);seed(root);store=ActiveInquiryStore(root,clock=lambda:'2026-07-27T12:00:00.000Z');iid=store.register('e1',inquiry_candidate_id='c1')['result']['active_inquiry_id'];arb=InquiryActivationArbitrator(root,clock=lambda:'2026-07-27T12:01:00.000Z')
 r=arb.decide('a1',active_inquiry_id=iid,relevance=.9,answerability=.9,novelty=.8,importance=.9);req(r['result']['outcome']=='active_internal');req(store.snapshot()['records'][0]['state']=='active_internal');req(not r['result']['causation_claimed']);req(not r['result']['browse_receipt_id'])
 req(arb.decide('a1',active_inquiry_id=iid)['idempotent']);req(arb.decide('a2',active_inquiry_id='missing')['status']=='arbitration_rejected');ins=arb.inspection_summary();req(ins['contract_version']=='v1113.1');req(ins['decision_count']==1);req(not ins['authority_boundary']['can_browse'])
print('8/8')
