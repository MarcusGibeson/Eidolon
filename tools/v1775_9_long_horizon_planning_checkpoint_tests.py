from __future__ import annotations
import json,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.dont_write_bytecode=True
from long_horizon_planning_intelligence import *
checks=[]
def req(v,n): checks.append(n); assert v,n
M=[
 {'milestone_code':'understand','tasks':[{'task_code':'inspect','success_codes':['model_ready']},{'task_code':'frame','depends_on':['inspect'],'success_codes':['requirements_ready']}], 'success_codes':['understood']},
 {'milestone_code':'implement','depends_on':['understand'],'tasks':[{'task_code':'change','strategy_code':'minimal_patch'},{'task_code':'verify','depends_on':['change']}], 'success_codes':['candidate_ready']},
 {'milestone_code':'review','depends_on':['implement'],'tasks':[{'task_code':'handoff'}], 'success_codes':['review_ready']},
]
with tempfile.TemporaryDirectory(prefix='eidolon-v1775-9-') as td:
 rt=Path(td)/'runtime'
 plan=create_long_horizon_plan('Deliver a bounded feature across several sessions',M,acceptance_codes=['tests_pass'],stop_condition_codes=['unsafe_state'],resource_codes=['bounded_time'],deferred_alternative_codes=['alternate_design'],runtime_root=rt)
 req(plan['ok'] and plan['milestone_count']==3 and plan['task_count']==5,'plan_ready')
 req(plan['original_objective_preserved'] and not plan['private_objective_exposed'],'objective_private')
 req(not plan['execution_authorized'] and not plan['scheduling_authorized'],'no_authority')
 pid=plan['plan_id'];d=plan['plan_digest']
 first=record_task_outcome(pid,d,task_code='inspect',outcome='complete',evidence_digest='a'*64,runtime_root=rt)
 req(first['completed_task_count']==1,'task_completed')
 replay=record_task_outcome(pid,first['plan_digest'],task_code='inspect',outcome='complete',evidence_digest='a'*64,runtime_root=rt)
 req(replay['status']=='task_outcome_replay','task_replay')
 fail=record_task_outcome(pid,replay['plan_digest'],task_code='change',outcome='failed',evidence_digest='b'*64,strategy_failed=True,runtime_root=rt)
 req('minimal_patch' in fail['failed_strategy_codes'],'failed_strategy_retained')
 newreq=revise_long_horizon_plan(pid,fail['plan_digest'],event_kind='new_requirement',event_code='extra_scope',operator_supplied=False,runtime_root=rt)
 req(not newreq['ok'] and newreq['status']=='unconfirmed_new_requirement_held','unconfirmed_requirement_held')
 revised=revise_long_horizon_plan(pid,fail['plan_digest'],event_kind='failed_assumption',event_code='minimal_patch_invalid',failed_strategy_codes=['minimal_patch'],runtime_root=rt)
 req(revised['ok'] and revised['completed_work_preserved'],'replan_preserves_completed')
 req('require_new_strategy_before_retry' in revised['replan_action_codes'],'failed_strategy_replan')
 req('minimal_patch' in revised['failed_strategy_codes'],'failed_strategy_persists')
 stale=revise_long_horizon_plan(pid,fail['plan_digest'],event_kind='new_evidence',event_code='stale',runtime_root=rt)
 req(not stale['ok'] and stale['status']=='stale_long_horizon_plan_digest','stale_replan_rejected')
 paused=set_plan_paused(pid,revised['plan_digest'],True,runtime_root=rt)
 req(paused['paused'] and paused['status']=='long_horizon_plan_paused','paused')
 blocked=record_task_outcome(pid,paused['plan_digest'],task_code='frame',outcome='complete',evidence_digest='c'*64,runtime_root=rt)
 req(not blocked['ok'] and blocked['status']=='plan_not_active_for_bookkeeping','paused_blocks_bookkeeping')
 resumed=set_plan_paused(pid,paused['plan_digest'],False,runtime_root=rt)
 req(not resumed['paused'],'resumed')
 # Priority changes may reorder pending milestones but cannot erase completed work.
 priority=revise_long_horizon_plan(pid,resumed['plan_digest'],event_kind='priority_change',event_code='review_first',requested_priority_codes=['review','implement'],operator_supplied=True,runtime_root=rt)
 req(priority['ok'] and priority['completed_work_preserved'],'priority_preserves')
 inspect=inspect_long_horizon_plan(pid,runtime_root=rt)
 req(inspect['completed_task_count']==1 and 'minimal_patch' in inspect['failed_strategy_codes'],'restart_continuity')
 legacy=legacy_hierarchy_projection(pid,runtime_root=rt)
 req(legacy.get('ok') and legacy.get('original_intent_preserved'),'legacy_hierarchy')
 invalid=create_long_horizon_plan('bad',[{'milestone_code':'second','depends_on':['missing'],'tasks':['x']}],runtime_root=rt)
 req(not invalid['ok'] and 'milestone_dependency_not_prior_or_unknown' in invalid['error_codes'],'unknown_dependency_rejected')
 ctl=process_long_horizon_planning_control('show long horizon planning requirements',runtime_root=rt)
 req(ctl['active'] and ctl['ok'] and 'failed_strategy_nonrepetition' in ctl['requirements'],'requirements_control')
 show=process_long_horizon_planning_control(f'show long horizon plan {pid}',runtime_root=rt)
 req(show['active'] and show['ok'],'show_control')
 compound=process_long_horizon_planning_control(f'show long horizon plan {pid} and execute',runtime_root=rt)
 req(compound['active'] and not compound['ok'],'compound_rejected')
print(json.dumps({'suite':'v1775.9-long-horizon-planning-checkpoint','ok':True,'passed':len(checks),'failed':0,'checks':checks},sort_keys=True))
