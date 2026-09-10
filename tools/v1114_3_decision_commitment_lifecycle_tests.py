from __future__ import annotations
import tempfile
from pathlib import Path
from conscious_agent.deliberative_option_records import DeliberativeOptionStore
from conscious_agent.deliberative_option_arbitration import DeliberativeOptionArbitrator
from conscious_agent.decision_commitment_lifecycle import DecisionCommitmentStore
def main():
 checks=[]
 def c(n,v):checks.append((n,bool(v)));print(('PASS' if v else 'FAIL'),n)
 with tempfile.TemporaryDirectory() as td:
  root=Path(td); clock=lambda:'2026-07-28T12:00:00.000Z'; opts=DeliberativeOptionStore(root,clock=clock); arb=DeliberativeOptionArbitrator(root,clock=clock); store=DecisionCommitmentStore(root,clock=clock)
  r=opts.register('r1',origin_type='objective',origin_id='o1',intended_outcome_digest='a'*64,benefit_score=.9,risk_score=.1,uncertainty=.1,resource_cost=.1,reversibility=.9); oid=r['result']['option_id']; cmp=arb.compare('c1',option_ids=[oid],objective_alignment={oid:1},evidence_quality={oid:1}); cid=cmp['result']['comparison_id']
  x=store.commit('d1',option_id=oid,comparison_id=cid); c('preferred_option_committed',x['status']=='commitment_created'); c('duplicate_event_idempotent',store.commit('d1',option_id=oid,comparison_id=cid)['idempotent']); c('semantic_duplicate_suppressed',store.commit('d2',option_id=oid,comparison_id=cid)['status']=='duplicate_commitment_ignored')
  bad=store.commit('d3',option_id='missing',comparison_id='missing'); c('exact_lineage_required',bad['status']=='commitment_rejected'); s=store.inspection_summary(); c('durable_active_commitment',s['commitment_count']==1 and s['active_commitment_count']==1); c('no_intention_formed',not s['recent_commitments'][0]['intention_id']); c('no_authority',not any(s['authority_boundary'].values())); c('content_free_inspection',not s['private_content_exposed'] and not s['hidden_reasoning_exposed'])
 print(f'{sum(v for _,v in checks)}/{len(checks)} passed');return 0 if all(v for _,v in checks) else 1
if __name__=='__main__':raise SystemExit(main())
