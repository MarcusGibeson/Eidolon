from __future__ import annotations
import sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.dont_write_bytecode=True
checks=[]
def req(v,n):checks.append(n);assert v,n
from goal_representation import create_goal
from goal_lifecycle import *
g=create_goal(outcome='x');
try:transition_goal(g,'complete',event_id='bad')
except ValueError:req(True,'invalid')
else:req(False,'invalid');a=transition_goal(g,'abandon',event_id='a');req(a['state']=='abandoned','abandon')
print(json.dumps({'suite':'v1309.6-8-goal-lifecycle','ok':True,'passed':len(checks),'failed':0,'checks':checks},sort_keys=True))
