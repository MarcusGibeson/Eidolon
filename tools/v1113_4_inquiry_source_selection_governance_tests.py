from pathlib import Path
import tempfile, json
from conscious_agent.active_inquiry_records import ActiveInquiryStore
from conscious_agent.inquiry_evidence_acquisition_proposals import InquiryEvidenceAcquisitionProposalStore
from conscious_agent.inquiry_source_selection_governance import InquirySourceSelectionGovernanceStore
def req(x):
 if not x: raise AssertionError(x)
def main():
 with tempfile.TemporaryDirectory() as td:
  root=Path(td);(root/'curiosity_inquiry_promotions.json').write_text(json.dumps({'schema_version':'1','contract_version':'v1111.6','promotions':[{'inquiry_candidate_id':'c1','semantic_key':'s1','state':'candidate'}],'processed_events':[],'revision':1,'updated_at':'','controls':{'max_candidates':256,'max_active':48},'state_separation':{},'authority_boundary':{}}));a=ActiveInquiryStore(root);r=a.register('e1',inquiry_candidate_id='c1',scope_digest='s',expected_information_value=.8,known_uncertainty=.7,sensitivity=.6,intrusion=.1,resource_budget=.6);iid=r['result']['active_inquiry_id'];a.apply_arbitration(iid,arbitration_id='a',outcome='active_internal')
  p=InquiryEvidenceAcquisitionProposalStore(root);pid=p.propose('p',active_inquiry_id=iid,source_class='existing_structural_records',resource_cost=.2,sensitivity=.2)['result']['proposal_id'];g=InquirySourceSelectionGovernanceStore(root)
  try:g.decide('d0',proposal_id=pid,new_state='approved_for_authorization_review')
  except PermissionError:pass
  else:raise AssertionError('confirmation required')
  x=g.decide('d1',proposal_id=pid,new_state='approved_for_authorization_review',operator_confirmation=True);req(x['result']['state']=='approved_for_authorization_review');req(g.decide('d1',proposal_id=pid,new_state='approved_for_authorization_review',operator_confirmation=True)['idempotent'])
  i=g.inspection_summary();req(i['contract_version']=='v1113.4');req(not i['authorization_granted']);req(not i['external_browsing_performed']);req(i['decision_count']==1)
 print('v1113.4 focused tests: 8/8')
if __name__=='__main__':main()
