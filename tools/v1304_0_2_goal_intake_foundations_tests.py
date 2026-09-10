from __future__ import annotations
import sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.dont_write_bytecode=True
checks=[]
def req(v,n):checks.append(n);assert v,n
from goal_intake import *
req(len(SOURCES)==4,'sources');
for s in SOURCES:
 r=intake_goal(source_kind=s,request_text='Do bounded work',workspace_digest='a'*64);req(r['goal']['outcome_digest'],'goal_'+s);req(r['review_required'],'review_'+s)
print(json.dumps({'suite':'v1304.0-2-goal-intake','ok':True,'passed':len(checks),'failed':0,'checks':checks},sort_keys=True))
