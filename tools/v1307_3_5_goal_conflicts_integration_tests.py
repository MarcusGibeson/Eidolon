from __future__ import annotations
import sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.dont_write_bytecode=True
checks=[]
def req(v,n):checks.append(n);assert v,n
from goal_conflicts import *
r=detect_goal_conflicts(repository_rules=['must not delete'],runtime_constraints=['deny:network'],plan_actions=['delete file','network request']);req(r['conflict_count']==2,'multi');req({x['source'] for x in r['conflicts']}=={'repository','runtime'},'sources')
print(json.dumps({'suite':'v1307.3-5-goal-conflicts','ok':True,'passed':len(checks),'failed':0,'checks':checks},sort_keys=True))
