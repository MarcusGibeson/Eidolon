from __future__ import annotations
import sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.dont_write_bytecode=True
checks=[]
def req(v,n):checks.append(n);assert v,n
from goal_intake import *
rows=[intake_goal(source_kind=s,request_text='Same task',workspace_digest='b'*64) for s in SOURCES];req(len({r['goal']['goal_id'] for r in rows})==1,'same_contract');req(len({r['source_digest'] for r in rows})==1,'same_content_lineage');req(all(not r['action_executed'] for r in rows),'no_action')
import tempfile
from ordinary_chat_development_campaign import process_ordinary_chat_development_turn
with tempfile.TemporaryDirectory() as td:
 turn=process_ordinary_chat_development_turn('Build me a to-do webpage',action_projection={'intent':{'category':'action_request'}},session_id='v1304-ordinary',runtime_root=Path(td));req(turn.get('event')=='proposal_created','legacy_proposal_preserved');req((turn.get('goal_intake') or {}).get('status')=='goal_intake_ready','ordinary_goal_augmented');req('Approve development proposal' in turn.get('conversation_response',''),'legacy_authority_text')
print(json.dumps({'suite':'v1304.3-5-goal-intake','ok':True,'passed':len(checks),'failed':0,'checks':checks},sort_keys=True))
