from pathlib import Path
import json,tempfile
from conscious_agent.active_inquiry_records import ActiveInquiryStore

def req(v):
 if not v: raise AssertionError()
with tempfile.TemporaryDirectory() as td:
 root=Path(td); root.mkdir(exist_ok=True)
 (root/'curiosity_inquiry_promotions.json').write_text(json.dumps({'schema_version':'1','contract_version':'v1111.6','promotions':[{'inquiry_candidate_id':'c1','semantic_key':'s1','decision_id':'d1','question_id':'q1','project_digest':'p1','state':'candidate'}],'processed_events':[],'revision':1,'updated_at':'','controls':{'max_candidates':256,'max_active':48},'state_separation':{},'authority_boundary':{}}))
 store=ActiveInquiryStore(root,clock=lambda:'2026-07-27T12:00:00.000Z')
 r=store.register('e1',inquiry_candidate_id='c1',scope_digest='abc',resource_budget=.9,allowed_source_classes=['existing_structural_records'])
 req(r['status']=='inquiry_registered'); iid=r['result']['active_inquiry_id']; snap=store.snapshot(); row=snap['records'][0]
 req(row['state']=='pending_activation');req(row['resource_budget']==.7);req(row['inquiry_candidate_id']=='c1');req(not row['browse_receipt_id'] and not row['authorization_id'])
 req(store.register('e1',inquiry_candidate_id='c1')['idempotent']);req(store.register('e2',inquiry_candidate_id='missing')['status']=='registration_rejected')
 ins=store.inspection_summary();req(ins['contract_version']=='v1113.0');req(ins['record_count']==1);req(not ins['external_browsing_performed']);req(not ins['authority_boundary']['can_activate_research'])
print('8/8')
