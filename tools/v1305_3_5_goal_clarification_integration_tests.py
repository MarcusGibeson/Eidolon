from __future__ import annotations
import sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.dont_write_bytecode=True
checks=[]
def req(v,n):checks.append(n);assert v,n
from goal_representation import create_goal
from goal_clarification import *
g=create_goal(outcome='x');r=clarify_goal(g,known_requirements={'request_text':'rename local helper','workspace':'w','acceptance':'tests'},reversible_choices=['helper name']);req(r['status']=='goal_clear_enough','clear');req(r['question_count']==0,'minimal');req(r['reversible_choice_digests'],'choice')
print(json.dumps({'suite':'v1305.3-5-goal-clarification','ok':True,'passed':len(checks),'failed':0,'checks':checks},sort_keys=True))
