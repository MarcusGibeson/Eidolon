from __future__ import annotations
import sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.dont_write_bytecode=True
checks=[]
def req(v,n):checks.append(n);assert v,n
from goal_representation import *
g1=create_goal(outcome='A',workspace_digest='b'*64);g2=create_goal(outcome='A',workspace_digest='b'*64);req(g1['goal_id']==g2['goal_id'],'deterministic');req(g1['workspace_digest']=='b'*64,'workspace');req(not g1['goal_is_authority'],'not_authority')
print(json.dumps({'suite':'v1303.3-5-goal-representation','ok':True,'passed':len(checks),'failed':0,'checks':checks},sort_keys=True))
