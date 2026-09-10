from __future__ import annotations
import sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.dont_write_bytecode=True
checks=[]
def req(v,n):checks.append(n);assert v,n
from goal_representation import create_goal
from goal_decomposition import *
g=create_goal(outcome='x');d=decompose_goal(g,[{'code':'a','deliverable':'file','test':'unit','rollback':'restore','completion':'pass'}]);req(all(d['tasks'][0].get(k) for k in ('deliverable_digest','test_digest','rollback_digest','completion_digest')),'artifacts');req(d['goal_id']==g['goal_id'],'lineage')
print(json.dumps({'suite':'v1306.3-5-goal-decomposition','ok':True,'passed':len(checks),'failed':0,'checks':checks},sort_keys=True))
