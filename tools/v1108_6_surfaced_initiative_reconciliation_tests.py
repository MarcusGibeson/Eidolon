from pathlib import Path
import tempfile
ROOT=Path(__file__).resolve().parents[1]
def run():
 root=Path(tempfile.mkdtemp())/'cognition'
 from conscious_agent.initiative_arbitration import InitiativeArbitrator
 from conscious_agent.initiative_conversation_proposal import InitiativeConversationProposalStore
 from conscious_agent.initiative_communication_restraint import InitiativeCommunicationRestraint
 from conscious_agent.surfaced_initiative_reconciliation import SurfacedInitiativeReconciliationStore
 # seed arbitration receipt directly, preserving test isolation
 a=InitiativeArbitrator(root); st=a._load(); st['receipts']=[{'receipt_id':'sel-1','decision':'selected','selected_candidate_id':'cand-1','intention_id':'int-1','subject_digest':'abc'}]; from conscious_agent.json_storage import write_json_atomic; write_json_atomic(a.path,st,expected_type=dict,sort_keys=True)
 p=InitiativeConversationProposalStore(root); pr=p.form('p1',selection_receipt_id='sel-1',conversation_context_digest='ctx')['result']['proposal_id']
 r=InitiativeCommunicationRestraint(root); d=r.decide('d1',proposal_id=pr,user_present=True,user_receptive=True,conversation_active=True)['decision']['decision_id']
 s=SurfacedInitiativeReconciliationStore(root); x=s.record('s1',decision_id=d,outcome='shown',normal_chat_turn_id='turn-1',conversation_session_id='session-1',explicit_surface_event=True); dup=s.record('s1',decision_id=d,outcome='shown',normal_chat_turn_id='turn-1',explicit_surface_event=True); bad=s.record('s2',decision_id=d,outcome='shown',normal_chat_turn_id='',explicit_surface_event=False)
 checks=[x['status']=='shown',x['receipt']['message_sent'] is False,x['receipt']['normal_chat_turn_digest']!='',dup['idempotent'] is True,bad['status']=='not_shown',s.inspection_summary()['authority_boundary']['can_send'] is False]
 print('v1108.6',sum(checks),'/',len(checks)); return all(checks)
if __name__=='__main__': raise SystemExit(0 if run() else 1)
