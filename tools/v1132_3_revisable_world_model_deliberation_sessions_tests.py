from pathlib import Path
import tempfile
from conscious_agent.revisable_world_model_signals import RevisableWorldModelSignalStore
from conscious_agent.revisable_world_model_candidates import RevisableWorldModelCandidateStore
from conscious_agent.revisable_world_model_deliberation_sessions import RevisableWorldModelDeliberationSessionStore

def seed(root, suffix='a', relation='supports', review=False):
 s=RevisableWorldModelSignalStore(root); r=s.register('sig-'+suffix,origin_ids=['origin-'+suffix],subject_category='person',subject_id='p-'+suffix,relation_category=relation,object_category='project',object_id='proj-'+suffix,evidence_ids=['e-'+suffix],operator_review_required=review); sid=r['result']['signal_id']
 c=RevisableWorldModelCandidateStore(root); q=c.register('cand-'+suffix,signal_ids=[sid],scope_digest='scope-'+suffix); return q['result']['candidate_id']
def main():
 with tempfile.TemporaryDirectory() as td:
  r=Path(td); cid=seed(r); out=RevisableWorldModelDeliberationSessionStore(r).open('open-a',candidate_id=cid,deliberation_budget=99); assert out['state']=='open'; row=RevisableWorldModelDeliberationSessionStore(r).snapshot()['sessions'][0]; assert row['deliberation_budget']==6 and row['candidate_id']==cid
 with tempfile.TemporaryDirectory() as td:
  r=Path(td); cid=seed(r,'b',review=True); out=RevisableWorldModelDeliberationSessionStore(r).open('open-b',candidate_id=cid); assert out['state']=='paused'
 with tempfile.TemporaryDirectory() as td:
  r=Path(td); cid=seed(r,'c',relation='contradicts'); out=RevisableWorldModelDeliberationSessionStore(r).open('open-c',candidate_id=cid,contradiction_review_ready=False); assert out['state']=='paused'
 print('v1132.3 revisable world-model deliberation sessions: 3/3 passed')
if __name__=='__main__': main()
