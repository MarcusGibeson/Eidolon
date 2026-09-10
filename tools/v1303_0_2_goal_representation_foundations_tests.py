from __future__ import annotations
import sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.dont_write_bytecode=True
checks=[]
def req(v,n):checks.append(n);assert v,n
from goal_representation import *
g=create_goal(outcome='Build feature',constraints=['offline'],acceptance_criteria=['tests pass'],non_goals=['publish'],evidence_requirements=['focused tests'],stop_conditions=['budget exhausted'],workspace_digest='a'*64);req(validate_goal(g)['ok'],'valid');req(g['constraint_digests'] and g['acceptance_criteria_digests'],'fields');req(not g['raw_goal_content_persisted'],'private');req('Build feature' not in json.dumps(g),'no_raw')
print(json.dumps({'suite':'v1303.0-2-goal-representation','ok':True,'passed':len(checks),'failed':0,'checks':checks},sort_keys=True))
