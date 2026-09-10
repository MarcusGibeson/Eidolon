from pathlib import Path
import sys,tempfile
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'conscious_agent')]
from conscious_agent.persistent_identity_model import PersistentIdentityModelStore
from conscious_agent.identity_change_detection import IdentityChangeDetector
from conscious_agent.self_model_revision import SelfModelRevisionStore
def req(x,m='failed'):
 if not x:raise AssertionError(m)
def main():
 root=Path(tempfile.mkdtemp())/'cognition';claims=PersistentIdentityModelStore(root);cid=claims.register_claim('c',claim_kind='preference',claim_summary='Prefers concise answers',evidence_refs=['e'])['result']['claim_id'];det=IdentityChangeDetector(root);did=det.detect('d',claim_id=cid,contradicting_refs=['x'],material_change=True,recurrence_count=3,observed_days=20)['result']['detection_id'];r=SelfModelRevisionStore(root)
 a=r.revise('r1',detection_id=did,outcome='revise',confidence_delta=-.9,uncertainty_delta=.9);req(a['result']['outcome']=='revise')
 row=claims.snapshot()['claims'][0];req(row['state']=='uncertain' and row['confidence']>=0.3 and row['uncertainty']<=0.75)
 req(r.revise('r1',detection_id=did,outcome='retract')['status']=='duplicate_revision_event_ignored')
 b=r.revise('r2',detection_id=did,outcome='suspend');req(b['result']['claim_state']=='suspended')
 req(claims.snapshot()['claims'][0]['active_influence'] is False)
 s=r.inspection_summary();req(s['revision_count']==2);req(not any(s['authority_boundary'].values()));req(s['provider_contacted'] is False and s['private_content_exposed'] is False)
 print('{"passed":8,"total":8,"suite":"v1110.4"}')
if __name__=='__main__':main()
