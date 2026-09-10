from __future__ import annotations
import json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'conscious_agent'))
from action_history_review import build_action_history_review, action_history_review_prompt, MAX_HISTORY_RECORDS, MAX_REVIEW_BYTES
checks=[]
def req(v): checks.append(bool(v)); assert v
H='a'*64
base={'proposal_id':'action_proposal_1','capability_id':'diagnostics','state':'awaiting_approval','proposal_digest':H,'updated_at':10,'content_free':True,'raw_request':'SECRET','arguments':{'path':'SECRET'}}
r=build_action_history_review([base])
req(r['review_status']=='history' and r['record_count']==1)
req(r['history'][0]['status_reference']=='status action action_proposal_1')
req('SECRET' not in json.dumps(r) and not r['raw_content_included'] and not r['argument_values_included'])
req(not r['ledger_discovered'] and not r['ledger_path_accepted'] and not r['authority_granted'] and not r['execution_invoked'])
q=build_action_history_review([base],status_reference='status action action_proposal_1')
req(q['exact_status_reference'] and q['selected_status']['state']=='awaiting_approval')
req(q['follow_through']['next_governed_step']=='await_operator_approval_decision')
req(not q['follow_through']['automatic_retry'] and not q['follow_through']['automatic_approval'] and not q['follow_through']['automatic_authorization'])
req('Do not claim retry' in action_history_review_prompt(q))
req(build_action_history_review([base],status_reference='go ahead')['review_status']=='invalid_reference')
req(build_action_history_review([base],status_reference='status action missing')['review_status']=='invalid_reference')
req(build_action_history_review([dict(base,content_free=False)])['record_count']==0)
req(build_action_history_review([dict(base,proposal_digest='bad')])['record_count']==0)
req(build_action_history_review([dict(base,state='invented')])['record_count']==0)
# Newest exact proposal wins without exposing digest in history list.
dupe=build_action_history_review([base,dict(base,state='approved',updated_at=20,approval_decision_digest='b'*64)],status_reference='show status for action action_proposal_1')
req(dupe['record_count']==1 and dupe['selected_status']['state']=='approved')
req(dupe['follow_through']['next_governed_step']=='request_separate_execution_authorization')
# Terminal failures never imply retry.
failed=build_action_history_review([dict(base,state='execution_failed',terminal_result_digest='c'*64)],status_reference='status action action_proposal_1')
req(failed['selected_status']['terminal'] and failed['follow_through']['next_governed_step']=='review_failure_before_new_governed_operation')
req(not failed['follow_through']['operator_action_available'] and not failed['follow_through']['automatic_retry'])
# Expired records may suggest a new governed proposal, not revival.
expired=build_action_history_review([dict(base,state='expired')],status_reference='status action action_proposal_1')
req(expired['follow_through']['next_governed_step']=='create_new_proposal_if_still_needed')
req(expired['follow_through']['operator_action_available'] and not expired['follow_through']['automatic_authorization'])
# Bounded retention and size.
many=[dict(base,proposal_id=f'action_proposal_{i}',updated_at=i) for i in range(MAX_HISTORY_RECORDS+9)]
bounded=build_action_history_review(many)
req(bounded['record_count']==MAX_HISTORY_RECORDS)
req(len(json.dumps(bounded,sort_keys=True,separators=(',',':')).encode())<=MAX_REVIEW_BYTES)
# Source contract contains no path/open/execute API.
source=(ROOT/'conscious_agent'/'action_history_review.py').read_text(encoding='utf-8')
req('Path(' not in source and 'execute_admitted_action' not in source and 'open(' not in source)
req('automatic_retry": False' in source and 'ledger_discovered": False' in source)
print(json.dumps({'ok':True,'suite':'v1179.0-v1179.2-action-review-follow-through-foundations','passed':sum(checks),'total':len(checks)},sort_keys=True))
