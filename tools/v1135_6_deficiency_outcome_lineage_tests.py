from pathlib import Path
import tempfile
ROOT=Path(__file__).resolve().parents[1]
from conscious_agent.deficiency_signals import DeficiencySignalStore
from conscious_agent.deficiency_candidates import DeficiencyCandidateStore
from conscious_agent.deficiency_deliberation_sessions import DeficiencyDeliberationSessionStore
from conscious_agent.deficiency_arbitration import DeficiencyArbitrationStore
from conscious_agent.deficiency_outcome_lineage import DeficiencyOutcomeLineageStore
with tempfile.TemporaryDirectory() as td:
 r=Path(td); sig=DeficiencySignalStore(r).register('e1',origin_ids=['o1'],source_categories=['failed_checkpoint'],deficiency_category='reliability_deficiency',component_ids=['component:a'],project_digest='p',scope_digest='s',evidence_ids=['ev'],recurrence_count=2,reproducibility=.9,severity=.8,urgency=.4,confidence=.9,uncertainty=.1); sid=sig['result']['signal_id']; cand=DeficiencyCandidateStore(r).register('e2',signal_ids=[sid]); cid=cand['result']['candidate_id']; ses=DeficiencyDeliberationSessionStore(r).open('e3',candidate_id=cid); sess=ses['session_id']; arb=DeficiencyArbitrationStore(r).arbitrate('e4',session_id=sess,evidence_support=.9,impact_support=.8,feasibility_support=.8,verified_defect_evidence=True); out=DeficiencyOutcomeLineageStore(r).record('e5',arbitration_id=arb['arbitration_id']); assert out['ok']; snap=DeficiencyOutcomeLineageStore(r).inspection_summary(); assert snap['contract_version']=='v1135.6' and snap['lineage_count']==1; assert not any(snap['authority_boundary'].values()); print('v1135.6 deficiency outcome lineage: 4/4 passed')
