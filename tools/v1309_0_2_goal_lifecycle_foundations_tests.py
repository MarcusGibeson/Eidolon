from __future__ import annotations
import sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.dont_write_bytecode=True
checks=[]
def req(v,n):checks.append(n);assert v,n
from goal_representation import create_goal
from goal_lifecycle import *
g=create_goal(outcome='x');g=transition_goal(g,'start',event_id='1');req(g['state']=='active','start');g=transition_goal(g,'pause',event_id='2');req(g['state']=='paused','pause');g=transition_goal(g,'resume',event_id='3');req(g['state']=='active','resume')
print(json.dumps({'suite':'v1309.0-2-goal-lifecycle','ok':True,'passed':len(checks),'failed':0,'checks':checks},sort_keys=True))
