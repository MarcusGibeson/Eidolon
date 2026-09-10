from __future__ import annotations
import json,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.dont_write_bytecode=True
from candidate_approaches import *
from goal_representation import create_goal
from ordinary_chat_development_campaign import process_ordinary_chat_development_turn
checks=[]
def req(v,n): checks.append(n); assert v,n
PU={'workspace_digest':'c'*64,'source_manifest_digest':'d'*64,'manifest_consistent':True}
g=create_goal(outcome='extend behavior safely')
with tempfile.TemporaryDirectory() as td:
    state={'project_understanding':PU,'planning_goal':g,'planning_decision_context':{'tradeoffs_matter':True,'compatibility_sensitive':True}}
    r=process_ordinary_chat_development_turn('show candidate approaches',project_state=state,runtime_root=td)
    req(r.get('active') and r.get('ok'),'ordinary_chat_route')
    p=r['candidate_approaches']; req(p['approach_count']>=2,'ordinary_multiple')
    loaded=load_candidate_approaches(p['approach_set_id'],runtime_root=td); req(loaded.get('approach_set_id')==p['approach_set_id'],'durable_record')
    fresh=assess_candidate_approach_freshness(p['approach_set_id'],PU,runtime_root=td); req(fresh['current'],'fresh_current')
    stale=assess_candidate_approach_freshness(p['approach_set_id'],{**PU,'source_manifest_digest':'e'*64},runtime_root=td); req(stale['status']=='stale','manifest_stale')
print(json.dumps({'suite':'v1321.3-5-candidate-approaches','ok':True,'passed':len(checks),'checks':checks},sort_keys=True))
