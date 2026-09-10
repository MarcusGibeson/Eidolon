from pathlib import Path
import tempfile,json
from conscious_agent.evidence_change_signals import EvidenceChangeSignalStore
from conscious_agent.belief_reconsideration_candidates import BeliefReconsiderationCandidateStore
passed=0
def req(v):
 global passed; assert v; passed+=1
with tempfile.TemporaryDirectory() as td:
 root=Path(td); sig=EvidenceChangeSignalStore(root,clock=lambda:'2026-08-02T00:00:00Z'); sid=sig.register('s1',belief_id='belief-1',evidence_id='ev-1',change_type='contradiction_detected',contradiction_severity=.9)['result']['signal_id']; c=BeliefReconsiderationCandidateStore(root,signals=sig,clock=lambda:'2026-08-02T00:00:01Z'); kw=dict(belief_id='belief-1',signal_ids=[sid],existing_confidence=.8,existing_uncertainty=.2,contradiction_severity=.9,temporal_relevance=.7,operator_review_required=True,structural_digest='d')
 a=c.register('c1',**kw); req(a['status']=='belief_reconsideration_candidate_registered'); req(c.register('c1',**kw)['idempotent']); req(c.register('c2',**kw)['status']=='duplicate_candidate_ignored'); snap=c.snapshot(); req(len(snap['candidates'])==1); req(snap['candidates'][0]['revision_outcome_id']==''); req(snap['candidates'][0]['operator_review_required'] is True); req(not any(snap['authority_boundary'].values())); req(c.inspection_summary()['candidate_count']==1); req(not c.inspection_summary()['hidden_reasoning_exposed']);
 try:c.register('bad',belief_id='belief-2',signal_ids=[sid]); ok=False
 except ValueError:ok=True
 req(ok)
print(json.dumps({'passed':passed,'total':10,'suite':'v1118.1'}))
