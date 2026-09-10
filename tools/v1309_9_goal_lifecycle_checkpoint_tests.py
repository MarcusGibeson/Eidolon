from __future__ import annotations
import sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.dont_write_bytecode=True
checks=[]
def req(v,n):checks.append(n);assert v,n
from goal_representation import create_goal
from goal_lifecycle import *
g=transition_goal(create_goal(outcome='x'),'start',event_id='1');req(CONTRACT_VERSION=='v1309.8','contract');req(g['state']=='active','active');req(not g['release_authorized'],'authority')
print(json.dumps({'suite':'v1309.9-goal-lifecycle-checkpoint','ok':True,'passed':len(checks),'failed':0,'checks':checks},sort_keys=True))
