from __future__ import annotations
import tempfile
from pathlib import Path
from conscious_agent.deliberative_option_records import DeliberativeOptionStore
from conscious_agent.deliberative_option_arbitration import DeliberativeOptionArbitrator
from conscious_agent.decision_commitment_lifecycle import DecisionCommitmentStore
from conscious_agent.decision_commitment_reconsideration import DecisionCommitmentReconsideration
def main():
 checks=[]
 def c(n,v):checks.append((n,bool(v)));print(('PASS' if v else 'FAIL'),n)
 with tempfile.TemporaryDirectory() as td:
  root=Path(td); clock=lambda:'2026-07-28T12:00:00.000Z'; o=DeliberativeOptionStore(root,clock=clock); a=DeliberativeOptionArbitrator(root,clock=clock); s=DecisionCommitmentStore(root,clock=clock); r=DecisionCommitmentReconsideration(root,clock=clock)
  x=o.register('r1',origin_type='objective',origin_id='o1',intended_outcome_digest='b'*64,benefit_score=.9,risk_score=.1,uncertainty=.1,resource_cost=.1,reversibility=.9); oid=x['result']['option_id']; cmp=a.compare('c1',option_ids=[oid],objective_alignment={oid:1},evidence_quality={oid:1}); cid=cmp['result']['comparison_id']; did=s.commit('d1',option_id=oid,comparison_id=cid)['result']['commitment_id']
  c('material_conflict_suspends',r.reconsider('x1',commitment_id=did,conflict_score=.9)['result']['outcome']=='suspended'); c('supported_resumes',r.reconsider('x2',commitment_id=did,evidence_support=.9)['result']['outcome']=='active'); c('stale_unsupported_retires',r.reconsider('x3',commitment_id=did,evidence_support=.2,stale=True)['result']['outcome']=='retired'); c('explicit_expiry',r.reconsider('x4',commitment_id=did,expired=True)['result']['outcome']=='expired'); c('duplicate_reconsideration_idempotent',r.reconsider('x4',commitment_id=did,expired=True)['idempotent']); q=r.inspection_summary(); c('deterministic',q['deterministic']); c('missing_feedback_not_positive',not q['missing_feedback_is_positive']); c('authority_unchanged',not q['authority_changed'])
 print(f'{sum(v for _,v in checks)}/{len(checks)} passed');return 0 if all(v for _,v in checks) else 1
if __name__=='__main__':raise SystemExit(main())
