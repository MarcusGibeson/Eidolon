from pathlib import Path
import tempfile, json
from conscious_agent.active_inquiry_records import ActiveInquiryStore
from conscious_agent.inquiry_evidence_acquisition_proposals import InquiryEvidenceAcquisitionProposalStore
def req(x):
 if not x: raise AssertionError(x)
def main():
 with tempfile.TemporaryDirectory() as td:
  root=Path(td);(root/'curiosity_inquiry_promotions.json').write_text(json.dumps({'schema_version':'1','contract_version':'v1111.6','promotions':[{'inquiry_candidate_id':'c1','semantic_key':'s1','decision_id':'d1','question_id':'q1','project_digest':'p','state':'candidate'}],'processed_events':[],'revision':1,'updated_at':'','controls':{'max_candidates':256,'max_active':48},'state_separation':{},'authority_boundary':{}}));a=ActiveInquiryStore(root)
  c={'inquiry_candidate_id':'c1','question_id':'q1','decision_id':'d1','project_digest':'p'}
  r=a.register('e1',inquiry_candidate_id='c1',scope_digest='s',expected_information_value=.8,known_uncertainty=.7,sensitivity=.5,intrusion=.2,resource_budget=.5,allowed_source_classes=['existing_structural_records']);iid=r['result']['active_inquiry_id'];a.apply_arbitration(iid,arbitration_id='arb1',outcome='active_internal')
  s=InquiryEvidenceAcquisitionProposalStore(root);x=s.propose('p1',active_inquiry_id=iid,source_class='existing_structural_records',scope_digest='x',resource_cost=.2,sensitivity=.2);req(x['result']['state']=='pending_operator_review')
  req(s.propose('p1',active_inquiry_id=iid,source_class='existing_structural_records')['idempotent'])
  y=s.propose('p2',active_inquiry_id=iid,source_class='approved_browsing_path',scope_digest='y',resource_cost=.9,sensitivity=.8);req(y['result']['state']=='suspended')
  i=s.inspection_summary();req(i['contract_version']=='v1113.3');req(i['proposal_count']==2);req(not i['external_browsing_performed']);req(not i['provider_contacted'])
 print('v1113.3 focused tests: 8/8')
if __name__=='__main__':main()
