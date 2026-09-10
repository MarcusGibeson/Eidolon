from __future__ import annotations
import sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.dont_write_bytecode=True
checks=[]
def req(v,n):checks.append(n);assert v,n
from goal_representation import create_goal
from goal_decomposition import *
g=create_goal(outcome='x');
for specs in ([{'code':'a','depends_on':['b']}],[{'code':'a','depends_on':['b']},{'code':'b','depends_on':['a']}],[{'code':'a'},{'code':'a'}]):
 try:decompose_goal(g,specs)
 except ValueError:req(True,'blocked')
 else:req(False,'blocked')
print(json.dumps({'suite':'v1306.6-8-goal-decomposition','ok':True,'passed':len(checks),'failed':0,'checks':checks},sort_keys=True))
