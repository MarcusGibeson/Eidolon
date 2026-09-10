from __future__ import annotations
import json, sys, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'conscious_agent'))
from action_history_review import build_action_history_review
from action_follow_up_continuity import *
checks=[]
def req(v): checks.append(bool(v)); assert v
H='a'*64
base={'proposal_id':'action_proposal_1','capability_id':'diagnostics','state':'execution_failed','proposal_digest':H,'terminal_result_digest':'b'*64,'updated_at':10,'content_free':True}
review=build_action_history_review([base],status_reference='status action action_proposal_1')
with tempfile.TemporaryDirectory() as td:
 p=Path(td)/'followups.json'
 a=register_action_follow_up(p,review,now=100); req(a['ok'] and a['persisted'] and a['state']=='pending')
 raw=p.read_text(); req('SECRET' not in raw and 'raw_request' not in raw and 'argument' not in raw)
 req(not a['authority_granted'] and not a['execution_invoked'])
 d=register_action_follow_up(p,review,now=101); req(d['state']=='duplicate_pending' and not d['persisted'])
 r=resume_action_follow_up(p,proposal_id='action_proposal_1',review_digest=review['review_digest'],proposal_digest=H,now=102)
 req(r['ok'] and r['resumable'] and r['next_governed_step']=='review_failure_before_new_governed_operation')
 req(not r['authority_granted'] and not r['execution_invoked'])
 req(not resume_action_follow_up(p,proposal_id='action_proposal_1',review_digest='c'*64,proposal_digest=H,now=102)['resumable'])
 req(not resume_action_follow_up(p,proposal_id='action_proposal_1',review_digest=review['review_digest'],proposal_digest='d'*64,now=102)['resumable'])
 c=transition_action_follow_up(p,proposal_id='action_proposal_1',transition='closed',now=103); req(c['ok'] and c['state']=='closed')
 c2=transition_action_follow_up(p,proposal_id='action_proposal_1',transition='closed',now=104); req(not c2['ok'] and c2['duplicate_terminal_transition'])
 req(not resume_action_follow_up(p,proposal_id='action_proposal_1',review_digest=review['review_digest'],proposal_digest=H,now=105)['resumable'])
 ins=inspect_action_follow_up_continuity(p,now=105); req(ins['record_count']==1 and ins['state_counts']['closed']==1)
 req(not ins['raw_content_exposed'] and not ins['ledger_discovered'] and not ins['authority_granted'] and not ins['execution_invoked'])
 # restart persistence
 rr=resume_action_follow_up(p,proposal_id='action_proposal_1',review_digest=review['review_digest'],proposal_digest=H,now=106); req(rr['state']=='closed')
 # expiry
 review2=build_action_history_review([dict(base,proposal_id='action_proposal_2',proposal_digest='e'*64)],status_reference='status action action_proposal_2')
 register_action_follow_up(p,review2,now=0)
 ex=resume_action_follow_up(p,proposal_id='action_proposal_2',review_digest=review2['review_digest'],proposal_digest='e'*64,now=7*86400+1); req(ex['state']=='expired' and not ex['resumable'])
 req(not register_action_follow_up(p,build_action_history_review([base]),now=1)['ok'])
 req(not transition_action_follow_up(p,proposal_id='missing',transition='cancelled')['ok'])
 req(not transition_action_follow_up(p,proposal_id='action_proposal_1',transition='retry')['ok'])
 source=(ROOT/'conscious_agent'/'action_follow_up_continuity.py').read_text()
 req('execute_admitted_action' not in source and 'automatic_retry' not in source)
 req('ledger_discovered' in source and "authority_granted':False" in source)
print(json.dumps({'ok':True,'suite':'v1179.3-v1179.5-governed-action-follow-up-continuity','passed':sum(checks),'total':len(checks)},sort_keys=True))
