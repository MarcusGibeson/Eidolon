from pathlib import Path
import tempfile
from conscious_agent.commitment_outcome_evidence import CommitmentOutcomeEvidenceStore
from conscious_agent.decision_commitment_lifecycle import DecisionCommitmentStore
from conscious_agent.deliberative_option_records import DeliberativeOptionStore

def c(name,ok):
 print(('PASS' if ok else 'FAIL'),name)
 if not ok: raise SystemExit(1)
with tempfile.TemporaryDirectory() as td:
 r=Path(td); opts=DeliberativeOptionStore(r); opt=opts.register('a',origin_type='objective',origin_id='o',intended_outcome_digest='outcome-x',benefit_score=.9,risk_score=.2,uncertainty=.1,reversibility=.8,resource_cost=.2)['result']['option_id']; opts.apply_comparison(opt,comparison_id='cmp',outcome='preferred'); commit=DecisionCommitmentStore(r).commit('c',option_id=opt,comparison_id='cmp')['result']['commitment_id']; s=CommitmentOutcomeEvidenceStore(r)
 c('supported_trigger',s.record('d',commitment_id=commit,outcome_class='supported',reliability=.9,relevance=.8)['result']['trigger']=='reaffirm_review'); c('contradiction_trigger',s.record('e',commitment_id=commit,outcome_class='contradicted',reliability=.8,relevance=.8)['result']['trigger']=='suspend_review'); c('stalled_trigger',s.record('f',commitment_id=commit,outcome_class='stalled',reliability=.7,relevance=.7)['result']['trigger']=='reconsider'); c('unknown_no_trigger',s.record('g',commitment_id=commit,outcome_class='unknown',reliability=.9,relevance=.9)['result']['trigger']=='none'); c('duplicate_event',s.record('g',commitment_id=commit,outcome_class='unknown')['idempotent']); c('retraction_no_influence',s.record('h',commitment_id=commit,outcome_class='supported',reliability=.9,relevance=.8,retracted=True)['result']['trigger']=='none'); c('missing_feedback_unknown',not s.inspection_summary()['missing_feedback_is_positive']); c('no_transition_authority',not any(s.inspection_summary()['authority_boundary'].values()))
