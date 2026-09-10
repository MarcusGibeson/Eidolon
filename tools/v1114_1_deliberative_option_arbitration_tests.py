from __future__ import annotations
import tempfile
from pathlib import Path
from conscious_agent.deliberative_option_records import DeliberativeOptionStore
from conscious_agent.deliberative_option_arbitration import DeliberativeOptionArbitrator

def main():
 checks=[]
 def check(name,ok): checks.append((name,bool(ok))); print(('PASS' if ok else 'FAIL'),name)
 with tempfile.TemporaryDirectory() as td:
  root=Path(td); clock=lambda:'2026-07-28T12:00:00.000Z'; store=DeliberativeOptionStore(root,clock=clock); arb=DeliberativeOptionArbitrator(root,clock=clock)
  ids=[]
  for i,(benefit,risk,cost,rev) in enumerate(((.9,.2,.2,.9),(.6,.4,.4,.6))):
   r=store.register(f'r{i}',origin_type='objective',origin_id='obj-1',intended_outcome_digest=str(i)*64,benefit_score=benefit,risk_score=risk,uncertainty=.2,resource_cost=cost,reversibility=rev); ids.append(r['result']['option_id'])
  result=arb.compare('c1',option_ids=ids,objective_alignment={ids[0]:.9,ids[1]:.6},evidence_quality={ids[0]:.9,ids[1]:.6})
  check('comparison_completed',result['status']=='comparison_completed')
  outcomes=result['result']['outcomes']; check('preferred_selected',outcomes[ids[0]]=='preferred')
  check('alternative_preserved',outcomes[ids[1]] in {'viable_alternative','dominated'})
  check('latest_not_automatic_winner',outcomes[ids[0]]=='preferred')
  check('duplicate_comparison_idempotent',arb.compare('c1',option_ids=ids)['idempotent'])
  # separate missing-evidence case
  s2=DeliberativeOptionStore(root,clock=clock); r=s2.register('r3',origin_type='active_inquiry',origin_id='inq-1',intended_outcome_digest='x'*64); oid=r['result']['option_id']; miss=arb.compare('c2',option_ids=[oid],missing_evidence=True)
  check('missing_evidence_unknown',miss['result']['outcomes'][oid]=='requires_more_evidence')
  summary=arb.inspection_summary(); check('no_authority_granted',not any(summary['authority_boundary'].values()))
  check('no_causation_claim',all(not x['causation_claimed'] for x in summary['recent_comparisons']))
 print(f'{sum(x for _,x in checks)}/{len(checks)} passed'); return 0 if all(x for _,x in checks) else 1
if __name__=='__main__': raise SystemExit(main())
