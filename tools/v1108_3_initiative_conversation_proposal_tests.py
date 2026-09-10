from pathlib import Path
import json,tempfile
ROOT=Path(__file__).resolve().parents[1]
def run():
 root=Path(tempfile.mkdtemp())/'cognition'; root.mkdir(parents=True)
 (root/'initiative_arbitration.json').write_text(json.dumps({'schema_version':'1','contract_version':'v1108.1','receipts':[{'receipt_id':'r1','decision':'selected','selected_candidate_id':'c1','intention_id':'i1','subject_digest':'d1'}],'processed_events':[],'revision':1,'updated_at':'','controls':{},'authority_boundary':{}}))
 from conscious_agent.initiative_conversation_proposal import InitiativeConversationProposalStore
 s=InitiativeConversationProposalStore(root); a=s.form('e1',selection_receipt_id='r1',conversation_context_digest='ctx'); b=s.form('e1',selection_receipt_id='r1'); snap=s.inspection_summary()
 tests=[a['status']=='conversation_proposal_formed',b['idempotent'],snap['proposal_count']==1,snap['message_sent'] is False,all(v is False for v in snap['authority_boundary'].values()),snap['recent_proposals'][0]['subject_digest']=='d1']
 print({'suite':'v1108.3','passed':sum(tests),'total':len(tests)}); return all(tests)
if __name__=='__main__': raise SystemExit(0 if run() else 1)
