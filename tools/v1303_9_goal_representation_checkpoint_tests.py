from __future__ import annotations
import sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.dont_write_bytecode=True
checks=[]
def req(v,n):checks.append(n);assert v,n
from goal_representation import *
g=create_goal(outcome='Goal',workspace_digest='d'*64);req(CONTRACT_VERSION=='v1303.8','contract');req(validate_goal(g)['ok'],'valid');req(all(not g.get(k) for k in g if k.endswith('_authorized')),'authority')
print(json.dumps({'suite':'v1303.9-goal-representation-checkpoint','ok':True,'passed':len(checks),'failed':0,'checks':checks},sort_keys=True))
