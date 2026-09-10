from __future__ import annotations
"""v1324 dependency-aware construction of executable-but-not-authorized plans."""
from pathlib import Path
from typing import Any, Iterable, Mapping

from cognitive_coding_foundations import digest
from candidate_approaches import PLANNING_DENIED_AUTHORITY
from goal_representation import validate_goal
from goal_decomposition import decompose_goal
from project_evidence_store import atomic_json, evidence_root, read_json, seal, valid

CONTRACT_VERSION='v1324.8'
MAX_STEPS=64


def _path(plan_id:str,runtime_root=None)->Path:
    return evidence_root('plan_construction',runtime_root)/'records'/f'{plan_id}.json'

def _select_approach(candidates:Mapping[str,Any],tradeoffs:Mapping[str,Any]|None,explicit:str='')->tuple[str,str]:
    ids={str(x.get('approach_id') or '') for x in candidates.get('approaches') or []}
    if explicit:
        if explicit not in ids:raise ValueError('explicit_approach_not_found')
        return explicit,'explicit_planning_choice'
    routine=str(candidates.get('selected_approach_id') or '')
    if routine:
        if routine not in ids:raise ValueError('routine_approach_not_found')
        return routine,'routine_collapsed_choice'
    if tradeoffs:
        if tradeoffs.get('tie'):return '','tradeoff_tie'
        rec=str(tradeoffs.get('recommended_approach_id') or '')
        if rec and rec in ids:return rec,'tradeoff_recommendation'
    return '','approach_selection_required'

def _default_specs(approach_code:str)->list[dict[str,Any]]:
    return [
        {'code':'inspect_scope','deliverable':'current evidence and owned surface confirmed','test':'freshness and precondition checks','rollback':'none read-only','completion':'relevant source and constraints confirmed','checkpoint':True},
        {'code':'implement_change','depends_on':['inspect_scope'],'deliverable':f'implement {approach_code}','test':'syntax or unit checks for edited surface','rollback':'restore owned candidate changes','completion':'planned candidate change materialized','checkpoint':True},
        {'code':'focused_verification','depends_on':['implement_change'],'deliverable':'focused verification evidence','test':'smallest sufficient affected suite','rollback':'revert candidate if verification blocks','completion':'focused acceptance evidence recorded','checkpoint':True},
        {'code':'acceptance_review','depends_on':['focused_verification'],'deliverable':'acceptance and non-goal review','test':'acceptance criteria trace review','rollback':'defer application if criteria unmet','completion':'exit criteria or stop reason explicit','checkpoint':True},
    ]

def build_plan(goal:Mapping[str,Any],candidate_approaches:Mapping[str,Any],*,tradeoff_evaluation:Mapping[str,Any]|None=None,assumption_ledger:Mapping[str,Any]|None=None,task_specs:Iterable[Mapping[str,Any]]=(),selected_approach_id:str='',runtime_root=None)->dict[str,Any]:
    if not validate_goal(goal).get('ok'):raise ValueError('valid_goal_required')
    if candidate_approaches.get('goal_digest')!=goal.get('goal_digest'):raise ValueError('candidate_goal_mismatch')
    chosen,selection_source=_select_approach(candidate_approaches,tradeoff_evaluation,selected_approach_id)
    if not chosen:
        return {'ok':False,'status':selection_source,'plan':{},'action_executed':False,**PLANNING_DENIED_AUTHORITY}
    approach=next(x for x in candidate_approaches.get('approaches') or [] if x.get('approach_id')==chosen)
    specs=list(task_specs)[:MAX_STEPS] or _default_specs(str(approach.get('approach_code') or 'selected_approach'))
    decomposition=decompose_goal(goal,specs)
    task_by_code={x['code']:x for x in decomposition['tasks']}
    raw_by_code={str(x.get('code') or f't{i+1}'):x for i,x in enumerate(specs)}
    steps=[]
    for idx,t in enumerate(decomposition['tasks'],1):
        raw=raw_by_code[t['code']]
        steps.append({'step_index':idx,'step_code':t['code'],'depends_on':list(t['depends_on']),'deliverable_digest':t['deliverable_digest'],
                      'verification_digest':t['test_digest'],'rollback_digest':t['rollback_digest'],'completion_digest':t['completion_digest'],
                      'checkpoint_required':bool(raw.get('checkpoint',True)),'mutation_expected':bool(raw.get('mutation_expected',t['code'] in {'implement_change'})),
                      'executed':False,'content_free':True})
    plan_id='plan_'+digest({'goal':goal.get('goal_digest'),'approaches':candidate_approaches.get('approach_set_id'),'chosen':chosen,'steps':steps,'assumptions':(assumption_ledger or {}).get('ledger_id')})[:24]
    row=seal({'contract_version':CONTRACT_VERSION,'plan_id':plan_id,'goal_id':goal.get('goal_id'),'goal_digest':goal.get('goal_digest'),
              'workspace_digest':candidate_approaches.get('workspace_digest'),'source_manifest_digest':candidate_approaches.get('source_manifest_digest'),
              'approach_set_id':candidate_approaches.get('approach_set_id'),'selected_approach_id':chosen,'selection_source':selection_source,
              'tradeoff_evaluation_id':(tradeoff_evaluation or {}).get('evaluation_id') or '', 'assumption_ledger_id':(assumption_ledger or {}).get('ledger_id') or '',
              'steps':steps,'step_count':len(steps),'acyclic':True,'checkpoint_count':sum(x['checkpoint_required'] for x in steps),
              'verification_step_count':sum(bool(x['verification_digest']) for x in steps),'rollback_step_count':sum(bool(x['rollback_digest']) for x in steps),
              'acceptance_criterion_count':len(goal.get('acceptance_criteria_digests') or []),'stop_condition_count':len(goal.get('stop_condition_digests') or []),
              'execution_ready_structure':True,'execution_authorized':False,'source_modified':False,'action_executed':False,**PLANNING_DENIED_AUTHORITY})
    atomic_json(_path(plan_id,runtime_root),row)
    return {'ok':True,'status':'plan_ready','plan':public_plan(row),'action_executed':False,**PLANNING_DENIED_AUTHORITY}

def public_plan(row:Mapping[str,Any])->dict[str,Any]:
    return {'contract_version':CONTRACT_VERSION,'plan_id':row.get('plan_id'),'goal_id':row.get('goal_id'),'goal_digest':row.get('goal_digest'),'workspace_digest':row.get('workspace_digest'),
            'source_manifest_digest':row.get('source_manifest_digest'),'approach_set_id':row.get('approach_set_id'),'selected_approach_id':row.get('selected_approach_id'),
            'selection_source':row.get('selection_source'),'tradeoff_evaluation_id':row.get('tradeoff_evaluation_id'),'assumption_ledger_id':row.get('assumption_ledger_id'),
            'steps':[{'step_index':x.get('step_index'),'step_code':x.get('step_code'),'depends_on':list(x.get('depends_on') or []),'checkpoint_required':bool(x.get('checkpoint_required')),
                      'mutation_expected':bool(x.get('mutation_expected')),'executed':False} for x in row.get('steps') or []],
            'step_count':int(row.get('step_count') or 0),'acyclic':bool(row.get('acyclic')),'checkpoint_count':int(row.get('checkpoint_count') or 0),
            'verification_step_count':int(row.get('verification_step_count') or 0),'rollback_step_count':int(row.get('rollback_step_count') or 0),
            'acceptance_criterion_count':int(row.get('acceptance_criterion_count') or 0),'stop_condition_count':int(row.get('stop_condition_count') or 0),
            'execution_ready_structure':bool(row.get('execution_ready_structure')),'execution_authorized':False,'read_only':True,'action_executed':False,**PLANNING_DENIED_AUTHORITY}

def load_plan(plan_id:str,*,runtime_root=None,include_private:bool=False)->dict[str,Any]:
    row=read_json(_path(str(plan_id),runtime_root));
    if not row or not valid(row):return {}
    return row if include_private else public_plan(row)

def process_plan_construction_control(text:str,*,goal=None,candidate_approaches=None,tradeoff_evaluation=None,assumption_ledger=None,task_specs=(),runtime_root=None,**_)->dict[str,Any]:
    if str(text or '').strip().lower() not in {'show plan construction','inspect plan construction'}:return {'active':False}
    if not goal or not candidate_approaches:return {'active':True,'ok':False,'status':'planning_inputs_required','action_executed':False,**PLANNING_DENIED_AUTHORITY}
    return {'active':True,**build_plan(goal,candidate_approaches,tradeoff_evaluation=tradeoff_evaluation,assumption_ledger=assumption_ledger,task_specs=task_specs,runtime_root=runtime_root)}

__all__=['CONTRACT_VERSION','build_plan','public_plan','load_plan','process_plan_construction_control']
