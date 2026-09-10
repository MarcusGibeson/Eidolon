from pathlib import Path
import json,tempfile
from conscious_agent.development_proposal_outcome_lineage import DevelopmentProposalOutcomeLineageStore

def main():
 with tempfile.TemporaryDirectory() as td:
  r=Path(td)/'cognition'; r.mkdir(parents=True); (r/'development_proposal_arbitration.json').write_text(json.dumps({'outcomes':[{'arbitration_id':'a1','candidate_id':'c1','eligibility_ids':['e1'],'deficiency_candidate_ids':['d1'],'proposal_categories':['reliability_repair'],'component_ids':['comp'],'project_digests':['p'],'scope_digests':['s'],'evidence_ids':['ev'],'outcome':'proposal_supported'}]}))
  store=DevelopmentProposalOutcomeLineageStore(r); first=store.record('l1',arbitration_id='a1'); second=store.record('l1',arbitration_id='a1'); out=store.inspection_summary(); row=out['recent_lineage'][0]
  assert first['ok'] and second['idempotent']
  assert out['lineage_count']==1 and row['arbitration_id']=='a1'
  assert not row['proposal_id'] and not row['specification_id'] and not row['sandbox_change_id']
  assert not any(out['authority_boundary'].values())
 print('v1136.6 development proposal outcome lineage: 4/4 passed')
if __name__=='__main__': main()
