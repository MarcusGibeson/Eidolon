from __future__ import annotations
"""Evidence-oriented planning quality contract for v1489 Bundle 14."""
from dataclasses import dataclass,asdict
from typing import Any,Iterable,Mapping
import hashlib,json

@dataclass(frozen=True)
class PlanningRequirement:
    requirement_id:str; text:str; testable:bool; source_class:str='operator_request'

def requirement_id(text:str)->str:
    return 'req-'+hashlib.sha256(str(text or '').strip().lower().encode()).hexdigest()[:16]

def build_requirements(items:Iterable[str])->list[PlanningRequirement]:
    out=[]
    for raw in items:
        text=' '.join(str(raw or '').split())
        if not text: continue
        testable=any(k in text.lower() for k in ('must','verify','test','pass','less than','at most','exactly','without','preserve','produce','do not'))
        out.append(PlanningRequirement(requirement_id(text),text,testable))
    return out

def epistemic_partition(*,facts:Iterable[str]=(),assumptions:Iterable[str]=(),uncertainties:Iterable[str]=(),questions:Iterable[str]=())->dict[str,Any]:
    def clean(xs): return [' '.join(str(x).split()) for x in xs if str(x).strip()]
    return {'known_facts':clean(facts),'assumptions':clean(assumptions),'uncertainties':clean(uncertainties),'unanswered_questions':clean(questions),'content_free':False}

def candidate_approaches(labels:Iterable[str],minimum:int=2)->dict[str,Any]:
    rows=[]
    for label in labels:
        text=' '.join(str(label or '').split())
        if text and text not in rows: rows.append(text)
    return {'approaches':rows,'sufficient_variety':len(rows)>=max(2,int(minimum)),'selected':None,'authority_granted':False}

def score_tradeoff(*,evidence_strength:float,reversibility:float,testability:float,scope_cost:float)->float:
    e=max(0,min(1,float(evidence_strength))); r=max(0,min(1,float(reversibility))); t=max(0,min(1,float(testability))); c=max(0,min(1,float(scope_cost)))
    return round(.35*e+.25*r+.30*t+.10*(1-c),4)

def missing_prerequisites(required:Iterable[str],available:Iterable[str])->list[str]:
    have={str(x).strip().lower() for x in available}; return [str(x) for x in required if str(x).strip().lower() not in have]

def revise_plan(*,steps:list[Mapping[str,Any]],invalidated_assumption:str,new_evidence:str)->dict[str,Any]:
    revised=[]
    for step in steps:
        row=dict(step); deps=[str(x) for x in row.get('depends_on_assumptions',[])];
        if invalidated_assumption in deps: row['status']='needs_revision'; row['revision_reason']='assumption_invalidated'
        revised.append(row)
    return {'steps':revised,'invalidated_assumption_digest':hashlib.sha256(str(invalidated_assumption).encode()).hexdigest()[:24],'new_evidence_present':bool(str(new_evidence).strip()),'automatic_execution':False,'content_free':True}

def authority_stop(*,next_step:str,requires_operator:bool,requires_approval:bool=False)->dict[str,Any]:
    stop=bool(requires_operator or requires_approval)
    return {'next_step_class':str(next_step or '')[:80],'stop_before_execution':stop,'requires_operator':bool(requires_operator),'requires_approval':bool(requires_approval),'execution_authorized':False,'content_free':True}

def plain_language_plan(steps:Iterable[Mapping[str,Any]])->list[str]:
    out=[]
    for i,s in enumerate(steps,1):
        action=' '.join(str(s.get('action') or '').split()); evidence=' '.join(str(s.get('evidence') or '').split())
        if action: out.append(f"{i}. {action}" + (f" Verify with {evidence}." if evidence else '.'))
    return out
