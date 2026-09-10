from pathlib import Path
import json,tempfile
from conscious_agent.development_proposal_reliability_review import DevelopmentProposalReliabilityReviewStore

def main():
 with tempfile.TemporaryDirectory() as td:
  r=Path(td)/'cognition'; r.mkdir(parents=True); (r/'development_proposal_outcome_lineage.json').write_text(json.dumps({'lineage':[{'lineage_id':'l1','arbitration_id':'a1','candidate_id':'c1','component_ids':['comp'],'project_digests':['p'],'scope_digests':['s'],'outcome':'proposal_supported'}]}))
  store=DevelopmentProposalReliabilityReviewStore(r)
  assert store.review('r1',lineage_id='l1',false_positive_count=2)['finding']=='repeated_false_positive'
  assert store.review('r2',lineage_id='l1',missed_signal_count=2)['finding']=='possible_missed_proposal'
  assert store.review('r3',lineage_id='l1',scope_drift=True)['finding']=='scope_drift'
  out=store.inspection_summary(); assert out['review_count']==3 and not any(out['authority_boundary'].values())
 print('v1136.7 development proposal reliability review: 4/4 passed')
if __name__=='__main__': main()
