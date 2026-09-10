from __future__ import annotations
import hashlib,json,os,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.dont_write_bytecode=True;os.environ['PYTHONDONTWRITEBYTECODE']='1';sys.path[:0]=[str(ROOT/'conscious_agent'),str(ROOT)]
from hierarchical_goal_management_foundations import *
C=[]
def req(v,l):
 if not v:raise AssertionError(l)
 C.append(l)
i=hashlib.sha256(b'operator-intent').hexdigest();h=build_goal_hierarchy(objective_code='improve_parser',original_intent_digest=i,milestone_codes=['inspect','implement','verify'],acceptance_codes=['tests_pass'],risk_codes=['regression']);v=validate_goal_hierarchy(h);req(v['ok'],'valid');req(h['milestone_count']==3 and h['hierarchy_depth']==4,'shape');req(v['intent_preserved'],'intent');req(v['dependencies_acyclic'],'acyclic');req(all(len(x['task_codes'])<=4 and x['test_codes'] and x['recovery_codes'] and x['completion_codes'] for x in h['milestones']),'components');tasks=[t for m in h['milestones'] for t in m['task_codes']];tests=[t for m in h['milestones'] for t in m['test_codes']];p=hierarchy_completion_state(h,completed_task_codes=tasks,passed_test_codes=tests);req(p['all_complete'] and p['completed_milestone_count']==3,'completion');req(p['original_intent_digest']==i,'progress_intent');bad=dict(h);bad['original_intent_digest']='0'*64;req(not validate_goal_hierarchy(bad)['ok'],'tamper');req(all(v is False for v in AUTHORITY_FLAGS.values()),'no_authority');print(json.dumps({'ok':True,'suite':'v1285.0-2-hierarchical-goal-management-foundations','passed':len(C),'failed':0,'checks':C},sort_keys=True))
