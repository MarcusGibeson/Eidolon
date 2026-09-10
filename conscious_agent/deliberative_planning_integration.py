from __future__ import annotations
"""v1330 integrated, bounded deliberative-planning evidence chain."""
from pathlib import Path
from typing import Any, Mapping, Sequence

from cognitive_coding_foundations import digest
from candidate_approaches import PLANNING_DENIED_AUTHORITY, build_candidate_approaches
from tradeoff_evaluation import evaluate_tradeoffs
from assumption_ledger import create_assumption_ledger
from plan_construction import build_plan
from plan_critique import critique_plan
from risk_sensitive_planning import assess_plan_risk
from evidence_dynamic_replanning import replan_from_evidence
from planning_stop_escalation import evaluate_stop_escalation
from plan_quality_scoring import score_plan_quality
from project_evidence_store import atomic_json, evidence_root, read_json, seal, valid

CONTRACT_VERSION="v1330.8"
CHAIN_STAGES=("candidate_approaches","tradeoff_evaluation","assumption_ledger","plan_construction","plan_critique","risk_sensitive_planning","dynamic_replanning","stop_escalation","plan_quality")


def _path(checkpoint_id:str,runtime_root=None)->Path:
    return evidence_root("deliberative_planning_checkpoint",runtime_root)/"records"/f"{checkpoint_id}.json"


def build_deliberative_planning_checkpoint(
    goal:Mapping[str,Any],project_understanding:Mapping[str,Any],*,decision_context:Mapping[str,Any]|None=None,
    explicit_options:Sequence[Mapping[str,Any]]=(),evidence_by_approach:Mapping[str,Mapping[str,Any]]|None=None,
    assumptions:Sequence[Mapping[str,Any]]=(),impact_analysis:Mapping[str,Any]|None=None,selected_approach_id:str='',
    completed_step_codes:Sequence[str]=(),evidence_change:Mapping[str,Any]|None=None,replan_reason_code:str='new_evidence',replacement_specs:Sequence[Mapping[str,Any]]=(),
    failure_count:int=0,uncertainty:Mapping[str,Any]|None=None,boundary_conflict:bool=False,resource_exhausted:bool=False,unsafe_side_effect:bool=False,
    outcome_evidence:Mapping[str,Any]|None=None,runtime_root=None,
)->dict[str,Any]:
    candidates=build_candidate_approaches(goal,project_understanding,decision_context=decision_context,explicit_options=explicit_options,runtime_root=runtime_root)['candidate_approaches']
    tradeoffs={}
    if int(candidates.get('approach_count') or 0)>1:
        tradeoffs=evaluate_tradeoffs(candidates,evidence_by_approach=evidence_by_approach,runtime_root=runtime_root)['tradeoff_evaluation']
        if tradeoffs.get('tie') and not selected_approach_id:
            return {'ok':False,'status':'tradeoff_tie_requires_explicit_planning_choice','candidate_approaches':candidates,'tradeoff_evaluation':tradeoffs,'action_executed':False,**PLANNING_DENIED_AUTHORITY}
    ledger={}
    if assumptions:
        ledger=create_assumption_ledger(goal_digest=str(goal.get('goal_digest') or ''),workspace_digest=str(project_understanding.get('workspace_digest') or ''),source_manifest_digest=str(project_understanding.get('source_manifest_digest') or ''),assumptions=assumptions,runtime_root=runtime_root)['assumption_ledger']
    plan_result=build_plan(goal,candidates,tradeoff_evaluation=tradeoffs or None,assumption_ledger=ledger or None,selected_approach_id=selected_approach_id,runtime_root=runtime_root)
    if not plan_result.get('ok'):
        return {'ok':False,'status':plan_result.get('status') or 'plan_not_constructed','candidate_approaches':candidates,'tradeoff_evaluation':tradeoffs,'assumption_ledger':ledger,'action_executed':False,**PLANNING_DENIED_AUTHORITY}
    plan=plan_result['plan']
    critique=critique_plan(plan,goal=goal,impact_analysis=impact_analysis,assumption_ledger=ledger or None,runtime_root=runtime_root)['plan_critique']
    risk=assess_plan_risk(plan,plan_critique=critique,impact_analysis=impact_analysis,runtime_root=runtime_root)['risk_sensitive_planning']
    replan={}
    if completed_step_codes or evidence_change or replacement_specs:
        replan=replan_from_evidence(plan,completed_step_codes=completed_step_codes,evidence_change=evidence_change,reason_code=replan_reason_code,replacement_specs=replacement_specs,runtime_root=runtime_root)['dynamic_replanning']
    stop=evaluate_stop_escalation(failure_count=failure_count,uncertainty=uncertainty,boundary_conflict=boundary_conflict,resource_exhausted=resource_exhausted,unsafe_side_effect=unsafe_side_effect,risk_sensitive_planning=risk,runtime_root=runtime_root)['stop_escalation']
    quality=score_plan_quality(plan,outcome_evidence,runtime_root=runtime_root)['plan_quality']
    checkpoint_id='deliberative_'+digest({'goal':goal.get('goal_digest'),'manifest':project_understanding.get('source_manifest_digest'),'candidates':candidates.get('approach_set_id'),'tradeoffs':tradeoffs.get('evaluation_id'),'plan':plan.get('plan_id'),'critique':critique.get('critique_id'),'risk':risk.get('assessment_id'),'replan':replan.get('replan_id'),'stop':stop.get('decision_id'),'quality':quality.get('score_id')})[:24]
    ready=not bool(critique.get('blocking_count')) and bool(risk.get('planning_progress_allowed')) and not bool(stop.get('stop_required'))
    stage_ids={"candidate_approaches":candidates.get('approach_set_id'),"tradeoff_evaluation":tradeoffs.get('evaluation_id'),"assumption_ledger":ledger.get('ledger_id'),"plan_construction":plan.get('plan_id'),"plan_critique":critique.get('critique_id'),"risk_sensitive_planning":risk.get('assessment_id'),"dynamic_replanning":replan.get('replan_id'),"stop_escalation":stop.get('decision_id'),"plan_quality":quality.get('score_id')}
    row=seal({'contract_version':CONTRACT_VERSION,'checkpoint_id':checkpoint_id,'goal_digest':goal.get('goal_digest'),'workspace_digest':project_understanding.get('workspace_digest'),'source_manifest_digest':project_understanding.get('source_manifest_digest'),
              'chain_stages':list(CHAIN_STAGES),'stage_ids':stage_ids,'completed_stage_count':sum(bool(x) for x in stage_ids.values()),'candidate_count':int(candidates.get('approach_count') or 0),'tradeoff_tie':bool(tradeoffs.get('tie')),
              'plan_step_count':int(plan.get('step_count') or 0),'critique_blocking_count':int(critique.get('blocking_count') or 0),'risk_tier':risk.get('risk_tier'),'stop_required':bool(stop.get('stop_required')),
              'quality_evaluable':bool(quality.get('evaluable')),'planning_chain_ready':ready,'grounded_rationale_available':True,'efficient_execution_order_preserved':bool(plan.get('acyclic')),
              'faithful_stop_behavior':True,'checkpoint_executes_work':False,'action_executed':False,**PLANNING_DENIED_AUTHORITY})
    atomic_json(_path(checkpoint_id,runtime_root),row)
    public=public_deliberative_planning_checkpoint(row)
    public.update({'candidate_approaches':candidates,'tradeoff_evaluation':tradeoffs,'assumption_ledger':ledger,'plan':plan,'plan_critique':critique,'risk_sensitive_planning':risk,'dynamic_replanning':replan,'stop_escalation':stop,'plan_quality':quality})
    return {'ok':True,'status':'deliberative_planning_ready' if ready else 'deliberative_planning_stopped','deliberative_planning':public,'action_executed':False,**PLANNING_DENIED_AUTHORITY}


def public_deliberative_planning_checkpoint(row:Mapping[str,Any])->dict[str,Any]:
    return {'contract_version':CONTRACT_VERSION,'checkpoint_id':row.get('checkpoint_id'),'goal_digest':row.get('goal_digest'),'workspace_digest':row.get('workspace_digest'),'source_manifest_digest':row.get('source_manifest_digest'),
            'chain_stages':list(CHAIN_STAGES),'stage_ids':dict(row.get('stage_ids') or {}),'completed_stage_count':int(row.get('completed_stage_count') or 0),'candidate_count':int(row.get('candidate_count') or 0),
            'tradeoff_tie':bool(row.get('tradeoff_tie')),'plan_step_count':int(row.get('plan_step_count') or 0),'critique_blocking_count':int(row.get('critique_blocking_count') or 0),'risk_tier':row.get('risk_tier'),
            'stop_required':bool(row.get('stop_required')),'quality_evaluable':bool(row.get('quality_evaluable')),'planning_chain_ready':bool(row.get('planning_chain_ready')),
            'grounded_rationale_available':True,'efficient_execution_order_preserved':bool(row.get('efficient_execution_order_preserved')),'faithful_stop_behavior':True,
            'checkpoint_executes_work':False,'read_only':True,'action_executed':False,**PLANNING_DENIED_AUTHORITY}


def load_deliberative_planning_checkpoint(checkpoint_id:str,*,runtime_root=None,include_private:bool=False)->dict[str,Any]:
    row=read_json(_path(str(checkpoint_id),runtime_root));
    if not row or not valid(row):return {}
    return row if include_private else public_deliberative_planning_checkpoint(row)


def process_deliberative_planning_control(text:str,*,goal=None,project_understanding=None,runtime_root=None,**kwargs)->dict[str,Any]:
    if str(text or '').strip().lower() not in {'show deliberative planning','inspect deliberative planning','show planning checkpoint'}:return {'active':False}
    if not goal or not project_understanding:return {'active':True,'ok':False,'status':'planning_goal_and_project_understanding_required','action_executed':False,**PLANNING_DENIED_AUTHORITY}
    return {'active':True,**build_deliberative_planning_checkpoint(goal,project_understanding,runtime_root=runtime_root,**kwargs)}


__all__=['CONTRACT_VERSION','CHAIN_STAGES','build_deliberative_planning_checkpoint','public_deliberative_planning_checkpoint','load_deliberative_planning_checkpoint','process_deliberative_planning_control']
