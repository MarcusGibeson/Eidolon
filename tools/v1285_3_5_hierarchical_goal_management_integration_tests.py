from __future__ import annotations
import json,os,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.dont_write_bytecode=True;os.environ['PYTHONDONTWRITEBYTECODE']='1';sys.path[:0]=[str(ROOT/'conscious_agent'),str(ROOT)]
from hierarchical_goal_management import *
C=[]
def req(v,l):
 if not v:raise AssertionError(l)
 C.append(l)
contract={'objective_code':'reliable_update','acceptance_codes':['focused_tests','rollback_ready'],'scope_codes':['self_candidate']};plan={'milestone_codes':['inspect','candidate','verify','review'],'risk_codes':['stale_source']};h=hierarchy_from_supervised_plan(plan,operator_contract=contract);req(validate_goal_hierarchy(h)['ok'],'hierarchy');req(h['original_intent_digest']==intent_digest_for_operator_contract(contract),'intent_digest');req([m['milestone_code'] for m in h['milestones']]==plan['milestone_codes'],'plan_bridge');s=public_goal_hierarchy_summary(h);req(s['ok'] and s['milestone_count']==4,'summary');req(not s['raw_operator_request_exposed'] and not s['plan_activated'],'privacy');req(not s['goal_hierarchy_is_execution_authority'],'no_authority');print(json.dumps({'ok':True,'suite':'v1285.3-5-hierarchical-goal-management-integration','passed':len(C),'failed':0,'checks':C},sort_keys=True))
