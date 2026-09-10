from __future__ import annotations
"""v1329 evidence-backed plan quality scoring from observed outcomes only."""
from pathlib import Path
from typing import Any, Mapping

from cognitive_coding_foundations import digest
from candidate_approaches import PLANNING_DENIED_AUTHORITY
from project_evidence_store import atomic_json, evidence_root, read_json, seal, valid

CONTRACT_VERSION="v1329.8"
METRICS=("prediction_accuracy","rework_efficiency","step_necessity","dependency_coverage","acceptance_coverage")


def _path(score_id:str,runtime_root=None)->Path:
    return evidence_root("plan_quality_scoring",runtime_root)/"records"/f"{score_id}.json"


def _ratio(n:int,d:int)->int|None:
    if d<=0:return None
    return max(0,min(100,round(100*n/d)))


def _validated_count(outcome:Mapping[str,Any],name:str,default:int=0)->int:
    value=int(outcome.get(name,default) or 0)
    if value<0:raise ValueError(f"negative_{name}")
    return value


def score_plan_quality(plan:Mapping[str,Any],outcome_evidence:Mapping[str,Any]|None=None,*,runtime_root=None)->dict[str,Any]:
    if not plan.get('plan_id') or not plan.get('steps'):raise ValueError('constructed_plan_required')
    if any(bool(plan.get(k)) for k in ('execution_authorized','project_mutation_authorized','source_application_authorized')):raise ValueError('authority_bearing_plan_rejected')
    out=dict(outcome_evidence or {});evidence=sorted({str(x) for x in out.get('verification_evidence_digests') or [] if str(x)})[:32]
    observed=bool(out.get('outcome_observed')) and bool(evidence)
    plan_steps=len(plan.get('steps') or [])
    predicted_total=_validated_count(out,'prediction_total');predicted_hits=_validated_count(out,'prediction_hits')
    rework=_validated_count(out,'rework_step_count');unnecessary=_validated_count(out,'unnecessary_step_count');missed=_validated_count(out,'missed_dependency_count')
    acceptance_total=_validated_count(out,'acceptance_criteria_total',int(plan.get('acceptance_criterion_count') or 0));acceptance_met=_validated_count(out,'acceptance_criteria_met_count')
    if predicted_hits>predicted_total:raise ValueError('prediction_hits_exceed_total')
    if acceptance_met>acceptance_total:raise ValueError('acceptance_met_exceeds_total')
    if rework>max(plan_steps*4,1) or unnecessary>plan_steps:raise ValueError('outcome_counts_implausible')
    metrics={
      'prediction_accuracy':_ratio(predicted_hits,predicted_total),
      'rework_efficiency':max(0,100-round(100*rework/max(plan_steps,1))),
      'step_necessity':max(0,100-round(100*unnecessary/max(plan_steps,1))),
      'dependency_coverage':max(0,100-round(100*missed/max(plan_steps,1))),
      'acceptance_coverage':_ratio(acceptance_met,acceptance_total),
    }
    if not observed:
        metrics={k:None for k in METRICS};overall=None;evaluable=False;status='plan_quality_not_evaluable'
    else:
        available=[v for v in metrics.values() if v is not None];overall=round(sum(available)/len(available)) if available else None;evaluable=overall is not None;status='plan_quality_scored' if evaluable else 'plan_quality_not_evaluable'
    score_id='quality_'+digest({'plan':plan.get('plan_id'),'manifest':plan.get('source_manifest_digest'),'evidence':evidence,'metrics':metrics,'observed':observed})[:24]
    row=seal({'contract_version':CONTRACT_VERSION,'score_id':score_id,'plan_id':plan.get('plan_id'),'goal_digest':plan.get('goal_digest'),'source_manifest_digest':plan.get('source_manifest_digest'),
              'outcome_observed':observed,'verification_evidence_digests':evidence,'evaluable':evaluable,'metrics':metrics,'overall_score':overall,
              'rework_step_count':rework if observed else None,'unnecessary_step_count':unnecessary if observed else None,'missed_dependency_count':missed if observed else None,
              'acceptance_criteria_met_count':acceptance_met if observed else None,'acceptance_criteria_total':acceptance_total if observed else None,
              'score_is_outcome_evidence_not_authority':True,'self_asserted_score_rejected':not observed,'action_executed':False,**PLANNING_DENIED_AUTHORITY})
    atomic_json(_path(score_id,runtime_root),row)
    return {'ok':True,'status':status,'plan_quality':public_plan_quality(row),'action_executed':False,**PLANNING_DENIED_AUTHORITY}


def public_plan_quality(row:Mapping[str,Any])->dict[str,Any]:
    return {'contract_version':CONTRACT_VERSION,'score_id':row.get('score_id'),'plan_id':row.get('plan_id'),'goal_digest':row.get('goal_digest'),'source_manifest_digest':row.get('source_manifest_digest'),
            'outcome_observed':bool(row.get('outcome_observed')),'evaluable':bool(row.get('evaluable')),'metrics':dict(row.get('metrics') or {}),'overall_score':row.get('overall_score'),
            'score_is_outcome_evidence_not_authority':True,'self_asserted_score_rejected':bool(row.get('self_asserted_score_rejected')),'read_only':True,'action_executed':False,**PLANNING_DENIED_AUTHORITY}


def load_plan_quality(score_id:str,*,runtime_root=None,include_private:bool=False)->dict[str,Any]:
    row=read_json(_path(str(score_id),runtime_root));
    if not row or not valid(row):return {}
    return row if include_private else public_plan_quality(row)


def process_plan_quality_control(text:str,*,plan=None,outcome_evidence=None,runtime_root=None,**_)->dict[str,Any]:
    if str(text or '').strip().lower() not in {'show plan quality','inspect plan quality','score plan quality'}:return {'active':False}
    if not plan:return {'active':True,'ok':False,'status':'constructed_plan_required','action_executed':False,**PLANNING_DENIED_AUTHORITY}
    return {'active':True,**score_plan_quality(plan,outcome_evidence,runtime_root=runtime_root)}


__all__=['CONTRACT_VERSION','METRICS','score_plan_quality','public_plan_quality','load_plan_quality','process_plan_quality_control']
