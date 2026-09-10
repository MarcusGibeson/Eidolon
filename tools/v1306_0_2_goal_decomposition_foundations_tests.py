from __future__ import annotations
import sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.dont_write_bytecode=True
checks=[]
def req(v,n):checks.append(n);assert v,n
from goal_representation import create_goal
from goal_decomposition import *
g=create_goal(outcome='x');d=decompose_goal(g,[{'code':'inspect'},{'code':'edit','depends_on':['inspect']},{'code':'test','depends_on':['edit']}]);req(d['task_count']==3,'count');req(d['acyclic'],'acyclic');req(d['tasks'][2]['depends_on']==('edit',),'deps')
print(json.dumps({'suite':'v1306.0-2-goal-decomposition','ok':True,'passed':len(checks),'failed':0,'checks':checks},sort_keys=True))
