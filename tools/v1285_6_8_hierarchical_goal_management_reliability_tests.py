from __future__ import annotations
import hashlib,json,os,sys,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.dont_write_bytecode=True;os.environ['PYTHONDONTWRITEBYTECODE']='1';sys.path[:0]=[str(ROOT/'conscious_agent'),str(ROOT)]
from hierarchical_goal_management_foundations import *
from hierarchical_goal_management_reliability import *
C=[]
def req(v,l):
 if not v:raise AssertionError(l)
 C.append(l)
h=inspect_hierarchical_goal_health(source_root=ROOT);req(h['ok'] and all(h['checks'].values()),'health');hand=build_hierarchical_goal_handoff(source_root=ROOT);req(hand['ok'] and hand['next_bounded_unit']=='v1286 Dynamic Replanning','handoff');req(hand['v1286_started'] is False,'unstarted');i=hashlib.sha256(b'x').hexdigest();a=build_goal_hierarchy(objective_code='x',original_intent_digest=i,milestone_codes=['a','b']);b=build_goal_hierarchy(objective_code='x',original_intent_digest=i,milestone_codes=['a','b','c']);cmp=compare_goal_hierarchies(a,b);req(cmp['ok'] and cmp['intent_preserved'] and cmp['milestone_change']==1,'compare');req(not cmp['authority_changed'],'contained');code=f"import sys;sys.path[:0]=[{str(ROOT/'conscious_agent')!r},{str(ROOT)!r}];import hierarchical_goal_management_foundations,hierarchical_goal_management,hierarchical_goal_management_reliability;print('ok')";p=subprocess.run([sys.executable,'-c',code],capture_output=True,text=True,timeout=20);req(p.returncode==0 and 'ok' in p.stdout,'fresh_import');print(json.dumps({'ok':True,'suite':'v1285.6-8-hierarchical-goal-management-reliability','passed':len(C),'failed':0,'checks':C},sort_keys=True))
