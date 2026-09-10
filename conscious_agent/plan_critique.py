from __future__ import annotations
"""v1325 independent bounded critique of constructed plans."""
from pathlib import Path
from typing import Any, Mapping

from cognitive_coding_foundations import digest
from candidate_approaches import PLANNING_DENIED_AUTHORITY
from project_evidence_store import atomic_json, evidence_root, read_json, seal, valid

CONTRACT_VERSION='v1325.8'
CATEGORIES=('missing_requirements','hidden_coupling','unsafe_authority','weak_verification')
SEVERITY={'info':0,'low':1,'medium':2,'high':3,'critical':4}


def _path(critique_id:str,runtime_root=None)->Path:
    return evidence_root('plan_critique',runtime_root)/'records'/f'{critique_id}.json'

def _finding(category:str,code:str,severity:str,*,blocking:bool,evidence=())->dict[str,Any]:
    row={'category':category,'finding_code':code,'severity':severity,'blocking':blocking,'evidence_digests':sorted({str(x) for x in evidence if str(x)})[:16],
         'content_free':True,'repair_applied':False,'action_executed':False};row['finding_digest']=digest(row);return row

def critique_plan(plan:Mapping[str,Any],*,goal:Mapping[str,Any]|None=None,impact_analysis:Mapping[str,Any]|None=None,assumption_ledger:Mapping[str,Any]|None=None,runtime_root=None)->dict[str,Any]:
    if not plan.get('plan_id') or not plan.get('steps'):raise ValueError('constructed_plan_required')
    findings=[];steps=list(plan.get('steps') or []);codes={str(x.get('step_code') or '') for x in steps};mut=[x for x in steps if x.get('mutation_expected')]
    # Requirements: represented acceptance criteria must survive into the plan and a review step.
    goal_ac=len((goal or {}).get('acceptance_criteria_digests') or [])
    if goal_ac and int(plan.get('acceptance_criterion_count') or 0)<goal_ac:
        findings.append(_finding('missing_requirements','acceptance_criteria_not_fully_carried', 'high', blocking=True,evidence=[(goal or {}).get('goal_digest')]))
    if goal_ac and 'acceptance_review' not in codes:
        findings.append(_finding('missing_requirements','acceptance_review_step_missing','high',blocking=True))
    # Coupling: broad predicted impact requires explicit inspection and verification checkpoints.
    impact=impact_analysis or {};affected=int(impact.get('affected_path_count') or 0)
    if affected>=8 and ('inspect_scope' not in codes or int(plan.get('checkpoint_count') or 0)<2):
        findings.append(_finding('hidden_coupling','broad_impact_underplanned','high',blocking=True,evidence=[impact.get('analysis_id')]))
    if impact.get('ui_impact_predicted') and not any('verification' in c or 'ui' in c for c in codes):
        findings.append(_finding('hidden_coupling','ui_impact_without_validation_step','medium',blocking=False,evidence=[impact.get('analysis_id')]))
    # Authority: planning artifacts must never self-authorize, and mutation steps need rollback.
    authority_keys=('execution_authorized','project_mutation_authorized','source_application_authorized','approval_consumed','standing_authority_granted')
    if any(bool(plan.get(k)) for k in authority_keys):
        findings.append(_finding('unsafe_authority','plan_contains_authority_escalation','critical',blocking=True))
    if impact.get('protected_authority_surface_predicted'):
        findings.append(_finding('unsafe_authority','protected_surface_requires_separate_governance','high',blocking=True,evidence=[impact.get('analysis_id')]))
    if mut and int(plan.get('rollback_step_count') or 0)<len(mut):
        findings.append(_finding('unsafe_authority','mutation_without_sufficient_rollback','high',blocking=True))
    # Verification: each mutation needs verification; known test candidates should not disappear.
    if mut and int(plan.get('verification_step_count') or 0)<len(mut):
        findings.append(_finding('weak_verification','mutation_verification_gap','high',blocking=True))
    if int(impact.get('candidate_test_count') or 0)>0 and not any('verification' in c or 'test' in c for c in codes):
        findings.append(_finding('weak_verification','predicted_tests_not_reflected','high',blocking=True,evidence=[impact.get('analysis_id')]))
    if assumption_ledger and any(x.get('status') in {'invalidated','stale'} for x in assumption_ledger.get('assumptions') or []):
        findings.append(_finding('missing_requirements','plan_relies_on_invalid_or_stale_assumption','high',blocking=True,evidence=[assumption_ledger.get('ledger_id')]))
    critique_id='critique_'+digest({'plan':plan.get('plan_id'),'plan_manifest':plan.get('source_manifest_digest'),'findings':[x['finding_digest'] for x in findings]})[:24]
    row=seal({'contract_version':CONTRACT_VERSION,'critique_id':critique_id,'plan_id':plan.get('plan_id'),'goal_digest':plan.get('goal_digest'),
              'source_manifest_digest':plan.get('source_manifest_digest'),'categories':list(CATEGORIES),'findings':findings,'finding_count':len(findings),
              'blocking_count':sum(x['blocking'] for x in findings),'highest_severity':max((x['severity'] for x in findings),key=lambda x:SEVERITY[x],default='info'),
              'plan_acceptable_for_next_planning_stage':not any(x['blocking'] for x in findings),'critique_mutated_plan':False,'action_executed':False,**PLANNING_DENIED_AUTHORITY})
    atomic_json(_path(critique_id,runtime_root),row)
    return {'ok':True,'status':'plan_critique_blocked' if row['blocking_count'] else 'plan_critique_clear','plan_critique':public_plan_critique(row),'action_executed':False,**PLANNING_DENIED_AUTHORITY}

def public_plan_critique(row:Mapping[str,Any])->dict[str,Any]:
    return {'contract_version':CONTRACT_VERSION,'critique_id':row.get('critique_id'),'plan_id':row.get('plan_id'),'goal_digest':row.get('goal_digest'),'source_manifest_digest':row.get('source_manifest_digest'),
            'categories':list(CATEGORIES),'findings':[{'category':x.get('category'),'finding_code':x.get('finding_code'),'severity':x.get('severity'),'blocking':bool(x.get('blocking'))} for x in row.get('findings') or []],
            'finding_count':int(row.get('finding_count') or 0),'blocking_count':int(row.get('blocking_count') or 0),'highest_severity':row.get('highest_severity'),
            'plan_acceptable_for_next_planning_stage':bool(row.get('plan_acceptable_for_next_planning_stage')),'critique_mutated_plan':False,'read_only':True,'action_executed':False,**PLANNING_DENIED_AUTHORITY}

def load_plan_critique(critique_id:str,*,runtime_root=None,include_private:bool=False)->dict[str,Any]:
    row=read_json(_path(str(critique_id),runtime_root));
    if not row or not valid(row):return {}
    return row if include_private else public_plan_critique(row)

def process_plan_critique_control(text:str,*,plan=None,goal=None,impact_analysis=None,assumption_ledger=None,runtime_root=None,**_)->dict[str,Any]:
    if str(text or '').strip().lower() not in {'show plan critique','inspect plan critique'}:return {'active':False}
    if not plan:return {'active':True,'ok':False,'status':'constructed_plan_required','action_executed':False,**PLANNING_DENIED_AUTHORITY}
    return {'active':True,**critique_plan(plan,goal=goal,impact_analysis=impact_analysis,assumption_ledger=assumption_ledger,runtime_root=runtime_root)}

__all__=['CONTRACT_VERSION','CATEGORIES','critique_plan','public_plan_critique','load_plan_critique','process_plan_critique_control']
