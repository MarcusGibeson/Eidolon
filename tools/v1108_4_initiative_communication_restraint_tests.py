from pathlib import Path
import json,tempfile

def run():
 root=Path(tempfile.mkdtemp())/'cognition'; root.mkdir(parents=True)
 (root/'initiative_conversation_proposals.json').write_text(json.dumps({'schema_version':'1','contract_version':'v1108.3','proposals':[{'proposal_id':'p1','active':True,'eligible':True,'sensitivity':.2,'confidence':.8}],'processed_events':[],'revision':1,'updated_at':'','controls':{},'state_separation':{},'authority_boundary':{}}))
 from conscious_agent.initiative_communication_restraint import InitiativeCommunicationRestraint
 s=InitiativeCommunicationRestraint(root); a=s.decide('e1',proposal_id='p1'); b=s.decide('e2',proposal_id='p1',user_present=True,user_receptive=True,conversation_active=True); c=s.decide('e2',proposal_id='p1'); snap=s.inspection_summary()
 tests=[a['status']=='defer',b['status']=='eligible_to_surface',c['idempotent'],snap['message_sent'] is False,snap['notification_sent'] is False,all(v is False for v in snap['authority_boundary'].values())]
 print({'suite':'v1108.4','passed':sum(tests),'total':len(tests)}); return all(tests)
if __name__=='__main__': raise SystemExit(0 if run() else 1)
