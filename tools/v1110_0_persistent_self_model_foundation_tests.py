from pathlib import Path
import hashlib, os, sys, tempfile
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'conscious_agent')]
from conscious_agent.persistent_identity_model import PersistentIdentityModelStore

def req(x,m='failed'):
 if not x: raise AssertionError(m)
def main():
 root=Path(tempfile.mkdtemp())/'cognition';s=PersistentIdentityModelStore(root)
 a=s.register_claim('e1',claim_kind='identity_trait',claim_summary='Preserves operator-governed boundaries',evidence_refs=['receipt-1'],confidence=.7)
 b=s.register_claim('e1',claim_kind='identity_trait',claim_summary='Preserves operator-governed boundaries',evidence_refs=['receipt-1'])
 c=s.register_claim('e2',claim_kind='identity_trait',claim_summary='Preserves operator-governed boundaries',evidence_refs=['receipt-2'])
 req(a['result']['status']=='claim_registered');req(b['status']=='duplicate_event_ignored');req(c['result']['status']=='duplicate_claim_ignored')
 snap=PersistentIdentityModelStore(root).snapshot();req(len(snap['claims'])==1);row=snap['claims'][0];req(row['provider_bound'] is False and row['authority_granted'] is False);req(not row['proposal_id'] and not row['authorization_id'] and not row['action_id'])
 try:s.register_claim('bad',claim_kind='preference',claim_summary='Retroactive claim',evidence_refs=['turn'],origin='generated_dialogue')
 except ValueError:pass
 else:raise AssertionError('post-hoc dialogue accepted')
 summary=s.inspection_summary();req(summary['private_content_exposed'] is False);req(not any(summary['authority_boundary'].values()))
 print('{"passed":8,"total":8,"suite":"v1110.0"}')
if __name__=='__main__':main()
