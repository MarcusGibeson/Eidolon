from __future__ import annotations
"""v1322 evidence-aware tradeoff evaluation for candidate approaches.

Scores are advisory comparisons, not authority. Missing evidence stays explicit
and is pulled toward a neutral expectation rather than being silently treated as
proof. Ties remain ties.
"""
from pathlib import Path
from typing import Any, Mapping

from cognitive_coding_foundations import digest
from candidate_approaches import PLANNING_DENIED_AUTHORITY
from project_evidence_store import atomic_json, evidence_root, read_json, seal, valid

CONTRACT_VERSION = "v1322.8"
CRITERIA = ("correctness", "complexity", "compatibility", "reversibility", "performance", "privacy", "maintenance")
DEFAULT_WEIGHTS = {"correctness": 30, "complexity": 10, "compatibility": 15, "reversibility": 10, "performance": 10, "privacy": 15, "maintenance": 10}
TIE_TOLERANCE = 2.0


def _path(evaluation_id: str, runtime_root=None) -> Path:
    return evidence_root("tradeoff_evaluation", runtime_root) / "records" / f"{evaluation_id}.json"


def _weights(raw: Mapping[str, Any] | None) -> dict[str, float]:
    base = {k: max(0.0, float((raw or {}).get(k, DEFAULT_WEIGHTS[k]))) for k in CRITERIA}
    total = sum(base.values())
    if total <= 0:
        base = {k: float(DEFAULT_WEIGHTS[k]) for k in CRITERIA}; total = 100.0
    return {k: round(v / total, 6) for k, v in base.items()}


def _heuristic(code: str, criterion: str) -> tuple[float, float, str]:
    code = str(code or "")
    table = {
        "minimal_targeted_change": {"complexity": 88, "compatibility": 78, "reversibility": 92, "maintenance": 64},
        "existing_pattern_extension": {"complexity": 76, "compatibility": 92, "reversibility": 84, "maintenance": 82},
        "boundary_refactor": {"complexity": 42, "compatibility": 58, "reversibility": 62, "maintenance": 90},
        "routine_reversible_choice": {"complexity": 92, "compatibility": 86, "reversibility": 96, "maintenance": 72},
    }
    if criterion in table.get(code, {}):
        return float(table[code][criterion]), 0.45, "inferred_from_strategy"
    return 50.0, 0.0, "unverified"


def _signal(raw: Mapping[str, Any] | None, *, code: str, criterion: str) -> dict[str, Any]:
    if raw and criterion in raw:
        value = raw[criterion]
        if isinstance(value, Mapping):
            score = max(0.0, min(100.0, float(value.get("score", 50))))
            confidence = max(0.0, min(1.0, float(value.get("confidence", 0))))
            evidence = sorted({str(x) for x in value.get("evidence_digests") or [] if str(x)})[:16]
        else:
            score = max(0.0, min(100.0, float(value))); confidence = 0.5; evidence = []
        state = "evidence_backed" if evidence and confidence > 0 else "asserted_signal"
    else:
        score, confidence, state = _heuristic(code, criterion); evidence = []
    calibrated = 50.0 + (score - 50.0) * confidence
    return {
        "criterion": criterion,
        "score": round(score, 3),
        "confidence": round(confidence, 3),
        "calibrated_score": round(calibrated, 3),
        "state": state,
        "evidence_digests": evidence,
        "unknown": confidence == 0.0,
        "content_free": True,
    }


def evaluate_tradeoffs(
    candidate_approaches: Mapping[str, Any],
    *,
    evidence_by_approach: Mapping[str, Mapping[str, Any]] | None = None,
    weights: Mapping[str, Any] | None = None,
    runtime_root=None,
) -> dict[str, Any]:
    approaches = list(candidate_approaches.get("approaches") or [])
    if not approaches:
        raise ValueError("candidate_approaches_required")
    w = _weights(weights)
    scored=[]
    for approach in approaches:
        aid=str(approach.get("approach_id") or "")
        code=str(approach.get("approach_code") or "")
        if not aid or not code: raise ValueError("approach_identity_required")
        supplied=(evidence_by_approach or {}).get(aid) or (evidence_by_approach or {}).get(code) or {}
        criteria=[_signal(supplied,code=code,criterion=c) for c in CRITERIA]
        weighted=sum(next(x for x in criteria if x['criterion']==c)['calibrated_score']*w[c] for c in CRITERIA)
        scored.append({
            "approach_id":aid,"approach_code":code,"criteria":criteria,"weighted_score":round(weighted,3),
            "unknown_criterion_count":sum(x['unknown'] for x in criteria),
            "evidence_backed_criterion_count":sum(bool(x['evidence_digests']) for x in criteria),
            "executed":False,"content_free":True,**PLANNING_DENIED_AUTHORITY,
        })
    scored.sort(key=lambda x:(-x['weighted_score'],x['approach_code']))
    best=scored[0]['weighted_score']; top=[x for x in scored if best-x['weighted_score']<=TIE_TOLERANCE]
    tie=len(top)>1
    recommended="" if tie else top[0]['approach_id']
    all_unknown=all(x['unknown_criterion_count']==len(CRITERIA) for x in scored)
    evaluation_id='tradeoffs_'+digest({
        'approach_set_id':candidate_approaches.get('approach_set_id'),'source_manifest_digest':candidate_approaches.get('source_manifest_digest'),
        'weights':w,'scores':[(x['approach_id'],x['weighted_score'],x['unknown_criterion_count']) for x in scored],
    })[:24]
    row=seal({
        'contract_version':CONTRACT_VERSION,'evaluation_id':evaluation_id,'approach_set_id':candidate_approaches.get('approach_set_id'),
        'goal_digest':candidate_approaches.get('goal_digest'),'workspace_digest':candidate_approaches.get('workspace_digest'),
        'source_manifest_digest':candidate_approaches.get('source_manifest_digest'),'weights':w,'criteria':list(CRITERIA),'approach_scores':scored,
        'tie':tie,'tie_tolerance':TIE_TOLERANCE,'recommended_approach_id':recommended,'recommendation_is_authority':False,
        'all_criteria_unverified':all_unknown,'comparison_performed':True,'action_executed':False,**PLANNING_DENIED_AUTHORITY,
    })
    atomic_json(_path(evaluation_id,runtime_root),row)
    return {'ok':True,'status':'tradeoff_tie_requires_judgment' if tie else 'tradeoff_evaluation_ready','tradeoff_evaluation':public_tradeoff_evaluation(row),'action_executed':False,**PLANNING_DENIED_AUTHORITY}


def public_tradeoff_evaluation(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        'contract_version':CONTRACT_VERSION,'evaluation_id':row.get('evaluation_id'),'approach_set_id':row.get('approach_set_id'),
        'goal_digest':row.get('goal_digest'),'workspace_digest':row.get('workspace_digest'),'source_manifest_digest':row.get('source_manifest_digest'),
        'criteria':list(CRITERIA),'approach_scores':[
            {'approach_id':x.get('approach_id'),'approach_code':x.get('approach_code'),'weighted_score':x.get('weighted_score'),
             'unknown_criterion_count':x.get('unknown_criterion_count'),'evidence_backed_criterion_count':x.get('evidence_backed_criterion_count')}
            for x in row.get('approach_scores') or []],
        'tie':bool(row.get('tie')),'recommended_approach_id':row.get('recommended_approach_id') or '',
        'recommendation_is_authority':False,'all_criteria_unverified':bool(row.get('all_criteria_unverified')),
        'read_only':True,'action_executed':False,**PLANNING_DENIED_AUTHORITY,
    }


def load_tradeoff_evaluation(evaluation_id: str, *, runtime_root=None, include_private: bool=False) -> dict[str, Any]:
    row=read_json(_path(str(evaluation_id),runtime_root))
    if not row or not valid(row): return {}
    return row if include_private else public_tradeoff_evaluation(row)


def process_tradeoff_evaluation_control(text: str, *, candidate_approaches=None, project_root=None, project_understanding=None, goal=None, decision_context=None, evidence_by_approach=None, runtime_root=None) -> dict[str, Any]:
    if str(text or '').strip().lower() not in {'show tradeoff evaluation','inspect tradeoff evaluation'}: return {'active':False}
    candidates=candidate_approaches
    if not candidates:
        if not goal: return {'active':True,'ok':False,'status':'planning_goal_required','action_executed':False,**PLANNING_DENIED_AUTHORITY}
        from candidate_approaches import build_candidate_approaches
        if project_understanding is None:
            if not project_root: return {'active':True,'ok':False,'status':'project_root_required','action_executed':False,**PLANNING_DENIED_AUTHORITY}
            from project_understanding_checkpoint import build_project_understanding_checkpoint
            project_understanding=build_project_understanding_checkpoint(project_root,runtime_root=runtime_root)['project_understanding']
        candidates=build_candidate_approaches(goal,project_understanding,decision_context=decision_context,runtime_root=runtime_root)['candidate_approaches']
    return {'active':True,**evaluate_tradeoffs(candidates,evidence_by_approach=evidence_by_approach,runtime_root=runtime_root)}


__all__=['CONTRACT_VERSION','CRITERIA','DEFAULT_WEIGHTS','TIE_TOLERANCE','evaluate_tradeoffs','public_tradeoff_evaluation','load_tradeoff_evaluation','process_tradeoff_evaluation_control']
