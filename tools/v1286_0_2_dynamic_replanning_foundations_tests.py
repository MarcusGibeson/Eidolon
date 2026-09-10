from __future__ import annotations
import hashlib,json,os,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.dont_write_bytecode=True;os.environ['PYTHONDONTWRITEBYTECODE']='1';sys.path[:0]=[str(ROOT/'conscious_agent'),str(ROOT)]
from hierarchical_goal_management_foundations import build_goal_hierarchy
from dynamic_replanning_foundations import *
C=[]
def req(v,l):
 if not v:raise AssertionError(l)
 C.append(l)
i=hashlib.sha256(b'intent').hexdigest();h=build_goal_hierarchy(objective_code='x',original_intent_digest=i,milestone_codes=['inspect','implement','verify']);
for kind in EVENT_KINDS:
 e=build_replanning_event(event_kind=kind,event_code=f'{kind}_event',operator_supplied=kind=='new_requirement',requested_priority_codes=['verify','implement'] if kind=='priority_change' else [],failed_strategy_codes=['retry_same_patch'] if kind=='failed_assumption' else []);req(validate_replanning_event(e),f'event_{kind}');r=build_replan_candidate(hierarchy=h,completed_milestone_codes=['inspect'],event=e);v=validate_replan_candidate(r);req(v['ok'],f'replan_{kind}');req(v['completed_work_preserved'],f'preserve_{kind}');req(r['original_intent_digest']==i,f'intent_{kind}');req(not r['work_executed'] and not r['tests_executed'] and not r['provider_contacted'],f'no_side_effect_{kind}')
e=build_replanning_event(event_kind='failed_assumption',event_code='f',failed_strategy_codes=['same']);r=build_replan_candidate(hierarchy=h,completed_milestone_codes=['inspect'],event=e,failed_strategy_codes=['same']);req(r['failed_strategy_codes']==['same'] and r['failed_strategies_may_not_repeat'],'failed_dedupe');e=build_replanning_event(event_kind='new_requirement',event_code='n',operator_supplied=False);r=build_replan_candidate(hierarchy=h,completed_milestone_codes=[],event=e);req(r['new_requirement_requires_operator_confirmation'],'requirement_confirmation');req(all(v is False for v in AUTHORITY_FLAGS.values()),'no_authority');print(json.dumps({'ok':True,'suite':'v1286.0-2-dynamic-replanning-foundations','passed':len(C),'failed':0,'checks':C},sort_keys=True))
