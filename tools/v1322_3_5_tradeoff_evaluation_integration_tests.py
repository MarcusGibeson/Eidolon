from __future__ import annotations
import json,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.dont_write_bytecode=True
from ordinary_chat_development_campaign import process_ordinary_chat_development_turn
from goal_representation import create_goal
checks=[]
def req(v,n):checks.append(n);assert v,n
PU={'workspace_digest':'a'*64,'source_manifest_digest':'b'*64,'manifest_consistent':True};g=create_goal(outcome='choose bounded implementation')
with tempfile.TemporaryDirectory() as td:
 r=process_ordinary_chat_development_turn('show tradeoff evaluation',project_state={'project_understanding':PU,'planning_goal':g,'planning_decision_context':{'tradeoffs_matter':True}},runtime_root=td)
 req(r.get('active') and r.get('ok'),'ordinary_route');e=r['tradeoff_evaluation'];req(len(e['approach_scores'])>=2,'candidate_chain');req(e['criteria']==list(__import__('tradeoff_evaluation').CRITERIA),'criteria_visible');req(not e['action_executed'],'read_only')
print(json.dumps({'suite':'v1322.3-5-tradeoff-evaluation','ok':True,'passed':len(checks),'checks':checks},sort_keys=True))
