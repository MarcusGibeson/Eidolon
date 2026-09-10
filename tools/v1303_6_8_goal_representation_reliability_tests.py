from __future__ import annotations
import sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.dont_write_bytecode=True
checks=[]
def req(v,n):checks.append(n);assert v,n
from goal_representation import *
g=create_goal(outcome='A',workspace_digest='c'*64);bad=dict(g);bad['state']='active';req(not validate_goal(bad)['ok'],'tamper');
try:create_goal(outcome='')
except ValueError:req(True,'empty_rejected')
else:req(False,'empty_rejected')
print(json.dumps({'suite':'v1303.6-8-goal-representation','ok':True,'passed':len(checks),'failed':0,'checks':checks},sort_keys=True))
