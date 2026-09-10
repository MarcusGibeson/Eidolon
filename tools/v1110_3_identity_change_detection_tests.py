from pathlib import Path
import sys,tempfile
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'conscious_agent')]
from conscious_agent.persistent_identity_model import PersistentIdentityModelStore
from conscious_agent.identity_change_detection import IdentityChangeDetector
def req(x,m='failed'):
 if not x:raise AssertionError(m)
def main():
 root=Path(tempfile.mkdtemp())/'cognition';claims=PersistentIdentityModelStore(root);cid=claims.register_claim('c',claim_kind='behavioral_tendency',claim_summary='Uses concise structural receipts',evidence_refs=['e1'])['result']['claim_id'];d=IdentityChangeDetector(root)
 a=d.detect('d1',claim_id=cid,observation_refs=['o1']);req(a['result']['outcome']=='no_material_change')
 b=d.detect('d2',claim_id=cid,contradicting_refs=['x1'],material_change=True,recurrence_count=1,observed_days=1);req(b['result']['outcome']=='contradiction_detected')
 c=d.detect('d3',claim_id=cid,contradicting_refs=['x2','x3'],material_change=True,recurrence_count=3,observed_days=14);req(c['result']['outcome']=='durable_change_candidate' and c['result']['eligible_for_revision'])
 req(d.detect('d3',claim_id=cid)['status']=='duplicate_detection_event_ignored');req(d.detect('d4',claim_id=cid,observation_refs=['o'],material_change=True)['result']['outcome']=='transient_variation')
 s=d.inspection_summary();req(s['detection_count']==4);req(not any(s['authority_boundary'].values()));req(s['provider_contacted'] is False and s['private_content_exposed'] is False)
 print('{"passed":8,"total":8,"suite":"v1110.3"}')
if __name__=='__main__':main()
