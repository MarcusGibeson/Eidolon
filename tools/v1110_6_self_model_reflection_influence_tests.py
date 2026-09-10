from pathlib import Path
import sys,tempfile
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'conscious_agent')]
from conscious_agent.persistent_identity_model import PersistentIdentityModelStore
from conscious_agent.self_model_reflection_influence import SelfModelReflectionInfluenceStore
def req(x,m='failed'):
 if not x:raise AssertionError(m)
def main():
 root=Path(tempfile.mkdtemp())/'cognition';c=PersistentIdentityModelStore(root);cid=c.register_claim('c',claim_kind='preference',claim_summary='Prefers careful concise replies',evidence_refs=['e'],confidence=.8,uncertainty=.2)['result']['claim_id'];s=SelfModelReflectionInfluenceStore(root)
 a=s.select_lens('e1',reflection_subject_ref='subject',claim_ids=[cid]);req(a['result']['outcome']=='eligible_lens');req(s.select_lens('e1',reflection_subject_ref='subject',claim_ids=[cid])['idempotent'])
 b=s.select_lens('e2',reflection_subject_ref='other',claim_ids=[],quiet=True);req(b['result']['outcome']=='defer')
 row=s.snapshot()['influences'][0];req(row['reflection_step_limit']==1 and row['may_dictate_conclusion'] is False and row['contradictory_evidence_allowed'] is True);req(not any(s.inspection_summary()['authority_boundary'].values()))
 print('{"passed":7,"total":7,"suite":"v1110.6"}')
if __name__=='__main__':main()
