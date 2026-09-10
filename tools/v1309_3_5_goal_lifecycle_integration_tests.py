from __future__ import annotations
import sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.dont_write_bytecode=True
checks=[]
def req(v,n):checks.append(n);assert v,n
from goal_representation import create_goal
from goal_lifecycle import *
g=create_goal(outcome='x');a=transition_goal(g,'start',event_id='same');b=transition_goal(a,'start',event_id='same');req(a['goal_digest']==b['goal_digest'],'idempotent');c=transition_goal(a,'recover_after_crash',event_id='crash');req(c['state']=='recovering','recover');d=transition_goal(c,'resume',event_id='resume');req(d['state']=='active','recovered')
print(json.dumps({'suite':'v1309.3-5-goal-lifecycle','ok':True,'passed':len(checks),'failed':0,'checks':checks},sort_keys=True))
