from pathlib import Path
import sys,tempfile
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'conscious_agent')]
from conscious_agent.persistent_identity_model import PersistentIdentityModelStore
from conscious_agent.identity_evidence_arbitration import IdentityEvidenceArbitrator

def req(x,m='failed'):
 if not x:raise AssertionError(m)
def main():
 root=Path(tempfile.mkdtemp())/'cognition';store=PersistentIdentityModelStore(root);cid=store.register_claim('c',claim_kind='preference',claim_summary='Prefers concise structural receipts',evidence_refs=['r1'])['result']['claim_id'];arb=IdentityEvidenceArbitrator(root)
 r=arb.arbitrate('a1',claim_id=cid,supporting_refs=['r2']);req(r['result']['outcome']=='retain')
 d=arb.arbitrate('a1',claim_id=cid,supporting_refs=['r2']);req(d['status']=='duplicate_event_ignored')
 v=arb.arbitrate('a2',claim_id=cid,contradicting_refs=['x'],correction=True);req(v['result']['outcome']=='revise')
 z=arb.arbitrate('a3',claim_id=cid,retraction=True);req(z['result']['outcome']=='retract')
 row=store.snapshot()['claims'][0];req(row['active_influence'] is False and row['state']=='retracted');req(len(row['update_history'])==4)
 summary=arb.inspection_summary();req(summary['provider_contacted'] is False and summary['external_action_executed'] is False);req(not any(summary['authority_boundary'].values()))
 print('{"passed":8,"total":8,"suite":"v1110.1"}')
if __name__=='__main__':main()
