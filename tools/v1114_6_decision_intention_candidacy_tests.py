from pathlib import Path
import tempfile
from conscious_agent.decision_intention_candidacy import DecisionIntentionCandidacyStore
from conscious_agent.decision_commitment_lifecycle import DecisionCommitmentStore
from conscious_agent.deliberative_option_records import DeliberativeOptionStore

def c(name,ok):
 print(('PASS' if ok else 'FAIL'),name)
 if not ok: raise SystemExit(1)
with tempfile.TemporaryDirectory() as td:
 r=Path(td); opts=DeliberativeOptionStore(r); opt=opts.register('e1',origin_type='objective',origin_id='o1',intended_outcome_digest='outcome-x',benefit_score=.9,risk_score=.2,uncertainty=.1,reversibility=.9,resource_cost=.2)['result']['option_id']; opts.apply_comparison(opt,comparison_id='cmp1',outcome='preferred')
 commit=DecisionCommitmentStore(r).commit('e3',option_id=opt,comparison_id='cmp1')['result']['commitment_id']; s=DecisionIntentionCandidacyStore(r)
 a=s.register('e4',commitment_id=commit,evidence_support=.8,conflict_score=.1,risk_score=.2); c('eligible_candidate',a['result']['outcome']=='eligible'); c('no_intention_formed',not s.inspection_summary()['intention_formed']); c('duplicate_event',s.register('e4',commitment_id=commit)['idempotent']); c('semantic_duplicate',s.register('e5',commitment_id=commit,evidence_support=.8,conflict_score=.1,risk_score=.2)['status']=='duplicate_candidate_ignored'); c('low_support_deferred',s.register('e6',commitment_id=commit,evidence_support=.2)['result']['outcome']=='deferred'); c('conflict_suspended',s.register('e7',commitment_id=commit,evidence_support=.9,conflict_score=.8)['result']['outcome']=='suspended'); c('unknown_rejected',s.register('e8',commitment_id='missing')['result']['outcome']=='rejected'); c('authority_boundary',not any(s.inspection_summary()['authority_boundary'].values()))
