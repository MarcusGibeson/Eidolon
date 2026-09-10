from __future__ import annotations
import tempfile
from pathlib import Path
from conscious_agent.deliberative_option_records import DeliberativeOptionStore

def main():
 checks=[]
 def check(name,ok): checks.append((name,bool(ok))); print(('PASS' if ok else 'FAIL'),name)
 with tempfile.TemporaryDirectory() as td:
  root=Path(td); store=DeliberativeOptionStore(root,clock=lambda:'2026-07-28T12:00:00.000Z')
  r=store.register('e1',origin_type='objective',origin_id='objective-1',intended_outcome_digest='a'*64,benefit_score=.8,risk_score=.2,uncertainty=.3,resource_cost=.4,reversibility=.9)
  check('registers_structural_option',r['status']=='option_registered')
  oid=r['result']['option_id']; snap=store.snapshot(); row=snap['records'][0]
  check('preserves_origin_lineage',row['origin_type']=='objective' and row['origin_id']=='objective-1')
  check('stores_digests_not_content',row['intended_outcome_digest']=='a'*64 and 'text' not in row)
  check('bounded_scores',all(0<=row[k]<=1 for k in ('benefit_score','risk_score','uncertainty','resource_cost','reversibility')))
  check('duplicate_event_idempotent',store.register('e1',origin_type='objective',origin_id='objective-1',intended_outcome_digest='a'*64)['idempotent'])
  check('semantic_duplicate_suppressed',store.register('e2',origin_type='objective',origin_id='objective-1',intended_outcome_digest='a'*64)['status']=='duplicate_option_ignored')
  summary=store.inspection_summary()
  check('authority_boundary_clear',not any(summary['authority_boundary'].values()))
  check('state_separation_explicit',all(v is False for v in summary['state_separation'].values()))
 print(f'{sum(x for _,x in checks)}/{len(checks)} passed'); return 0 if all(x for _,x in checks) else 1
if __name__=='__main__': raise SystemExit(main())
