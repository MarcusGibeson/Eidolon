from __future__ import annotations
import sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.dont_write_bytecode=True
checks=[]
def req(v,n):checks.append(n);assert v,n
from goal_conflicts import *
r=detect_goal_conflicts(operator_rules=['deny:publish'],plan_actions=['local test']);req(r['status']=='goal_conflict_clear','clear');req(not r['requires_operator_resolution'],'no_resolution');req(not r['action_executed'],'no_action')
print(json.dumps({'suite':'v1307.6-8-goal-conflicts','ok':True,'passed':len(checks),'failed':0,'checks':checks},sort_keys=True))
