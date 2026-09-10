from __future__ import annotations

"""v2504.2 deterministic arbitration over registered cognitive operations."""

from copy import deepcopy
import hashlib
import json
from typing import Any, Mapping

from cognitive_operation_registry import build_cognitive_operation_registry

CONTRACT_VERSION = "v2504.2"


def _bounded(value: Any, default: float = 0.0) -> float:
    try:return max(0.0,min(1.0,float(value)))
    except (TypeError,ValueError):return default


def _score_rows(frame: Mapping[str, Any], *, unfinished_thought_count: int = 0, new_experience: bool = False, self_model_evidence: bool = False) -> list[dict[str, Any]]:
    p=frame.get('projection') if isinstance(frame.get('projection'),Mapping) else {}
    h=p.get('homeostasis') if isinstance(p.get('homeostasis'),Mapping) else {}
    d=p.get('demands') if isinstance(p.get('demands'),Mapping) else {}
    b=p.get('beliefs') if isinstance(p.get('beliefs'),Mapping) else {}
    pl=p.get('planning') if isinstance(p.get('planning'),Mapping) else {}
    c=p.get('continuity') if isinstance(p.get('continuity'),Mapping) else {}
    i=p.get('initiative') if isinstance(p.get('initiative'),Mapping) else {}
    pressure=_bounded(h.get('pressure'));fragment=_bounded(h.get('fragmentation'));margin=_bounded(h.get('recovery_margin'),1.0);uncertainty=_bounded(h.get('uncertainty'))
    conflicts=max(0,int(b.get('active_conflict_count') or 0));contested=max(0,int(b.get('contested_count') or 0));plans=max(0,int(pl.get('active_count') or 0));due=max(0,int(c.get('due_subject_count') or 0));demands=max(0,int(d.get('candidate_count') or 0))
    paused=bool(i.get('quiet') or i.get('paused') or i.get('sleeping'))
    overload=max(pressure,fragment,1.0-margin)
    scores={
      'REST':0.18 + overload*0.82 + (0.35 if paused else 0.0),
      'CONTINUE_THOUGHT':min(1.0,0.12+0.55*min(unfinished_thought_count,1)+0.12*due),
      'RECONSIDER_BELIEF':min(1.0,0.08+0.42*min(conflicts,1)+0.20*min(contested,1)+0.18*uncertainty),
      'RESOLVE_CONFLICT':min(1.0,0.05+0.58*min(conflicts,1)+0.14*uncertainty),
      'REVIEW_GOAL':min(1.0,0.08+0.30*min(plans,1)+0.18*min(demands,1)+0.12*due),
      'PLAN':min(1.0,0.05+0.24*min(demands,1)+0.20*uncertainty+(0.12 if plans==0 and demands else 0)),
      'REPLAN':min(1.0,0.04+0.22*min(plans,1)+0.28*min(conflicts,1)+0.15*uncertainty),
      'RECALL_MEMORY':min(1.0,0.08+0.18*min(demands+due,1)+0.16*uncertainty),
      'INTEGRATE_EXPERIENCE':0.52 if new_experience else 0.04,
      'REVIEW_SELF_MODEL':0.48 if self_model_evidence else 0.03,
      'REFLECT':min(1.0,0.10+0.18*min(demands+due,1)+0.16*uncertainty+0.12*min(conflicts,1)),
    }
    registry={row['operation']:row for row in build_cognitive_operation_registry()['operations']}
    rows=[]
    for op,score in scores.items():
      cost=float(registry[op]['cost']); utility=max(0.0,min(1.0,score-cost*0.18))
      if paused and op!='REST':utility*=0.25
      rows.append({'operation':op,'salience':round(score,4),'cost':round(cost,4),'utility':round(utility,4),'eligible':True})
    return sorted(rows,key=lambda row:(row['utility'],row['salience'],-row['cost'],row['operation']),reverse=True)


def arbitrate_cognitive_operation(frame: Mapping[str, Any], *, unfinished_thought_count: int = 0, new_experience: bool = False, self_model_evidence: bool = False, minimum_utility: float = 0.22) -> dict[str, Any]:
    if not isinstance(frame,Mapping) or not frame.get('ok') or not frame.get('frame_digest'):
        raise ValueError('valid cognitive frame required')
    rows=_score_rows(frame,unfinished_thought_count=max(0,int(unfinished_thought_count)),new_experience=bool(new_experience),self_model_evidence=bool(self_model_evidence))
    chosen=rows[0] if rows else {'operation':'REST','utility':0.0,'salience':0.0,'cost':0.02,'eligible':True}
    if chosen['operation']!='REST' and float(chosen['utility'])<max(0.0,min(1.0,float(minimum_utility))):
        chosen=next(row for row in rows if row['operation']=='REST')
    payload={'frame_digest':str(frame['frame_digest']),'operation':chosen['operation'],'utility':chosen['utility'],'alternatives':[(r['operation'],r['utility']) for r in rows[:5]]}
    arbitration_id='cognitive-arbitration-'+hashlib.sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest()[:24]
    return {
      'ok':True,'contract_version':CONTRACT_VERSION,'arbitration_id':arbitration_id,'frame_id':str(frame.get('frame_id') or ''),'frame_digest':str(frame['frame_digest']),
      'selected_operation':chosen['operation'],'selected_utility':chosen['utility'],'selected_cost':chosen['cost'],'candidate_scores':rows,
      'deliberate_inactivity':chosen['operation']=='REST','provider_contacted':False,'message_sent':False,'external_action_executed':False,'authority_broadened':False,'hidden_reasoning_exposed':False,
    }
