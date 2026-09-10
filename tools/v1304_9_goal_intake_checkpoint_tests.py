from __future__ import annotations
import sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.dont_write_bytecode=True
checks=[]
def req(v,n):checks.append(n);assert v,n
from goal_intake import *
r=intake_goal(source_kind='casual_conversation_command',request_text='It would be nice; build the bounded thing',workspace_digest='d'*64);req(CONTRACT_VERSION=='v1304.8','contract');req(r['goal']['goal_id'].startswith('goal_'),'goal');req(r['review_required'],'review');req(not r['project_mutation_authorized'],'authority')
print(json.dumps({'suite':'v1304.9-goal-intake-checkpoint','ok':True,'passed':len(checks),'failed':0,'checks':checks},sort_keys=True))
