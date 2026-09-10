from __future__ import annotations
import hashlib,json,os,sys,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.dont_write_bytecode=True;os.environ['PYTHONDONTWRITEBYTECODE']='1';sys.path[:0]=[str(ROOT/'conscious_agent'),str(ROOT)]
from hierarchical_goal_management_foundations import build_goal_hierarchy
from dynamic_replanning_foundations import *
from dynamic_replanning_reliability import *
C=[]
def req(v,l):
 if not v:raise AssertionError(l)
 C.append(l)
hl=inspect_dynamic_replanning_health(source_root=ROOT);req(hl['ok'] and all(hl['checks'].values()),'health');hand=build_dynamic_replanning_handoff(source_root=ROOT);req(hand['ok'] and hand['next_bounded_unit']=='v1287 Unified Conversation and Action','handoff');req(hand['v1287_started'] is False,'unstarted');i=hashlib.sha256(b'i').hexdigest();h=build_goal_hierarchy(objective_code='x',original_intent_digest=i,milestone_codes=['a','b']);e=build_replanning_event(event_kind='interruption',event_code='x');a=build_replan_candidate(hierarchy=h,completed_milestone_codes=['a'],event=e);b=build_replan_candidate(hierarchy=h,completed_milestone_codes=['a'],event=e);cmp=compare_replan_candidates(a,b);req(cmp['ok'] and cmp['deterministic_same_input'] and cmp['original_intent_same'] and cmp['completed_work_same'],'deterministic');req(not cmp['authority_changed'],'contained');bad=dict(a);bad['completed_milestone_codes']=[];req(not validate_replan_candidate(bad)['ok'],'tamper');code=f"import sys;sys.path[:0]=[{str(ROOT/'conscious_agent')!r},{str(ROOT)!r}];import dynamic_replanning_foundations,dynamic_replanning,dynamic_replanning_reliability;print('ok')";p=subprocess.run([sys.executable,'-c',code],capture_output=True,text=True,timeout=20);req(p.returncode==0 and 'ok' in p.stdout,'fresh_import');print(json.dumps({'ok':True,'suite':'v1286.6-8-dynamic-replanning-reliability','passed':len(C),'failed':0,'checks':C},sort_keys=True))
