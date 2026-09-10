from pathlib import Path
from tempfile import TemporaryDirectory
from conscious_agent.revisable_world_model_signals import RevisableWorldModelSignalStore
from conscious_agent.revisable_world_model_candidates import RevisableWorldModelCandidateStore
from conscious_agent.revisable_world_model_deliberation_sessions import RevisableWorldModelDeliberationSessionStore
from conscious_agent.revisable_world_model_arbitration import RevisableWorldModelArbitrationStore
from conscious_agent.revisable_world_model_outcome_lineage import RevisableWorldModelOutcomeLineageStore
with TemporaryDirectory() as td:
 r=Path(td); sig=RevisableWorldModelSignalStore(r).register('s',origin_ids=['o1'],subject_id='p1',subject_category='project',object_id='e1',object_category='event',relation_category='supports',evidence_ids=['ev1'],structural_digest='a'*64); sid=sig['result']['signal_id']; c=RevisableWorldModelCandidateStore(r).register('c',signal_ids=[sid],scope_digest='b'*64); cid=c['result']['candidate_id']; ses=RevisableWorldModelDeliberationSessionStore(r).open('d',candidate_id=cid); aid=RevisableWorldModelArbitrationStore(r).arbitrate('a',session_id=ses['session_id'],evidence_sufficiency=.9,coherence=.9,confidence_match=.9)['arbitration_id']; out=RevisableWorldModelOutcomeLineageStore(r).record('o',arbitration_id=aid); assert out['ok']; snap=RevisableWorldModelOutcomeLineageStore(r).inspection_summary(); assert snap['outcome_count']==1 and not snap['authority_boundary']['can_apply_revision']
print('v1132.6 5/5')
