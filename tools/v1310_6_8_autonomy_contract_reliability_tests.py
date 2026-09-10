from __future__ import annotations
import sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.dont_write_bytecode=True
checks=[]
def req(v,n):checks.append(n);assert v,n
from authority_profiles import create_authority_profile
from standing_session_grants import *
from goal_representation import create_goal
from session_budgets import *
from autonomy_contract import *
p=create_authority_profile(name='bounded_autonomous',workspace_digest='c'*64);x=prepare_standing_session(p,now_unix=100);g=activate_standing_session(x['grant'],x['exact_authorization_phrase'],now_unix=101)['grant'];goal=create_goal(outcome='x',workspace_digest='c'*64);b=create_budget({k:0 for k in FIELDS});req(not evaluate_routine_step(grant=g,goal=goal,budget=b,action_class='command',workspace_digest='c'*64,cost={'commands':1},now_unix=102)['permitted'],'budget');req(not evaluate_routine_step(grant=g,goal=goal,budget=b,action_class='read',workspace_digest='d'*64,now_unix=102)['permitted'],'workspace');req(not evaluate_routine_step(grant=g,goal=goal,budget=b,action_class='read',workspace_digest='c'*64,now_unix=999999)['permitted'],'expiry')
print(json.dumps({'suite':'v1310.6-8-autonomy-contract','ok':True,'passed':len(checks),'failed':0,'checks':checks},sort_keys=True))
