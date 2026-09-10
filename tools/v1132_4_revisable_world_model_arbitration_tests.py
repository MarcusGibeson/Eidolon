from pathlib import Path
import tempfile
from conscious_agent.revisable_world_model_signals import RevisableWorldModelSignalStore
from conscious_agent.revisable_world_model_candidates import RevisableWorldModelCandidateStore
from conscious_agent.revisable_world_model_deliberation_sessions import RevisableWorldModelDeliberationSessionStore
from conscious_agent.revisable_world_model_arbitration import RevisableWorldModelArbitrationStore

def session(root, suffix, relation='supports', correction=False):
 s=RevisableWorldModelSignalStore(root); x=s.register('s-'+suffix,origin_ids=['o-'+suffix],subject_category='belief',subject_id='b-'+suffix,relation_category=relation,object_category='event',object_id='e-'+suffix,evidence_ids=['ev-'+suffix],correction=correction); sid=x['result']['signal_id']; c=RevisableWorldModelCandidateStore(root); cid=c.register('c-'+suffix,signal_ids=[sid],scope_digest='scope')['result']['candidate_id']; return RevisableWorldModelDeliberationSessionStore(root).open('d-'+suffix,candidate_id=cid)['session_id']
def main():
 with tempfile.TemporaryDirectory() as td:
  r=Path(td); sid=session(r,'a'); out=RevisableWorldModelArbitrationStore(r).arbitrate('a',session_id=sid,evidence_sufficiency=.9,coherence=.9,confidence_match=.9); assert out['outcome']=='relationship_acceptance_recommended'
 with tempfile.TemporaryDirectory() as td:
  r=Path(td); sid=session(r,'b','may_cause'); out=RevisableWorldModelArbitrationStore(r).arbitrate('b',session_id=sid,evidence_sufficiency=.9,coherence=.9,confidence_match=.9,causal_support=.2); assert out['outcome']=='suppress_unsupported_causation'
 with tempfile.TemporaryDirectory() as td:
  r=Path(td); sid=session(r,'c','corrects',True); out=RevisableWorldModelArbitrationStore(r).arbitrate('c',session_id=sid,evidence_sufficiency=.9,coherence=.9,confidence_match=.9); assert out['outcome']=='correction_acceptance_recommended'
 print('v1132.4 revisable world-model arbitration: 3/3 passed')
if __name__=='__main__': main()
