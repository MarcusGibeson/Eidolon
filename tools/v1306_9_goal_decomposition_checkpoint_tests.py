from __future__ import annotations
import sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.dont_write_bytecode=True
checks=[]
def req(v,n):checks.append(n);assert v,n
from goal_representation import create_goal
from goal_decomposition import *
g=create_goal(outcome='x');d=decompose_goal(g,[{'code':'a'}]);req(CONTRACT_VERSION=='v1306.8','contract');req(not d['decomposition_grants_authority'],'no_authority');req(not d['project_mutation_authorized'],'mutation')
print(json.dumps({'suite':'v1306.9-goal-decomposition-checkpoint','ok':True,'passed':len(checks),'failed':0,'checks':checks},sort_keys=True))
