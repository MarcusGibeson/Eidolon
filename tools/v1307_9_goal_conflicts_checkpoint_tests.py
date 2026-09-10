from __future__ import annotations
import sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.dont_write_bytecode=True
checks=[]
def req(v,n):checks.append(n);assert v,n
from goal_conflicts import *
r=detect_goal_conflicts(operator_rules=['deny:release'],plan_actions=['release']);req(CONTRACT_VERSION=='v1307.8','contract');req(r['requires_operator_resolution'],'conflict');req(not r['release_authorized'],'authority')
print(json.dumps({'suite':'v1307.9-goal-conflicts-checkpoint','ok':True,'passed':len(checks),'failed':0,'checks':checks},sort_keys=True))
