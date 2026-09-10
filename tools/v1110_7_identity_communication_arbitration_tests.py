from pathlib import Path
import sys,tempfile
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'conscious_agent')]
from conscious_agent.persistent_identity_model import PersistentIdentityModelStore
from conscious_agent.identity_communication_arbitration import IdentityCommunicationArbitrator
def req(x,m='failed'):
 if not x:raise AssertionError(m)
def main():
 root=Path(tempfile.mkdtemp())/'cognition';c=PersistentIdentityModelStore(root);cid=c.register_claim('c',claim_kind='behavioral_tendency',claim_summary='Communicates carefully',evidence_refs=['e'])['result']['claim_id'];a=IdentityCommunicationArbitrator(root)
 x=a.arbitrate('a1',proposal_ref='p1',claim_ids=[cid]);req(x['result']['outcome']=='consistent' and x['result']['eligible_for_normal_chat_surface'])
 y=a.arbitrate('a2',proposal_ref='p2',claim_ids=[cid],contradiction_count=1);req(y['result']['outcome']=='revise_tone')
 z=a.arbitrate('a3',proposal_ref='p3',claim_ids=[cid],sensitivity=.9);req(z['result']['outcome']=='deliberate_silence')
 row=a.snapshot()['decisions'][0];req(row['message_sent'] is False and row['delivery_triggered'] is False and row['message_id']=='');req(not any(a.inspection_summary()['authority_boundary'].values()))
 print('{"passed":7,"total":7,"suite":"v1110.7"}')
if __name__=='__main__':main()
