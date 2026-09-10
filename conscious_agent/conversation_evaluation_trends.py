from __future__ import annotations
"""v1087.4 bounded content-free longitudinal daily-evaluation trends."""
from typing import Any, Mapping
import hashlib,json
from conversation_daily_evaluation import DAILY_EVALUATIONS_DIR, load_daily_evaluation, DailyEvaluationError
MAX_TREND_EVALUATIONS=256

def _digest(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=True).encode()).hexdigest()
def build_daily_evaluation_trends(*,maximum_evaluations:int=MAX_TREND_EVALUATIONS)->dict[str,Any]:
    limit=max(1,min(int(maximum_evaluations),MAX_TREND_EVALUATIONS)); rows=[]
    for p in sorted(DAILY_EVALUATIONS_DIR.glob('daily_eval_*.json'),reverse=True)[:limit]:
      try: rows.append(load_daily_evaluation(p.stem))
      except DailyEvaluationError: continue
    outcomes={}; domains={}; signals={}; completed=aborted=active=repro=0
    for row in rows:
      st=str(row.get('state') or 'active'); active+=st=='active'; completed+=st=='completed'; aborted+=st=='aborted'
      outcome = row.get('outcome') or {}
      oc=str(outcome.get('outcome') or outcome.get('outcome_code') or 'unclassified'); outcomes[oc]=outcomes.get(oc,0)+1
      for obs in row.get('observations') or ():
        d=str(obs.get('issue_domain') or 'none'); domains[d]=domains.get(d,0)+1
        repro+=bool(obs.get('reproducible'))
        for s in obs.get('signals') or (): signals[str(s)]=signals.get(str(s),0)+1
    evidence=[{'evaluation_id':r.get('evaluation_id'),'revision':r.get('revision'),'state':r.get('state'),'digest':r.get('observation_evidence_digest')} for r in rows]
    return {'type':'desktop_alpha_daily_evaluation_trends','schema_version':'1','evaluation_count':len(rows),'maximum_evaluations':limit,
      'state_counts':{'active':active,'completed':completed,'aborted':aborted},'outcome_counts':dict(sorted(outcomes.items())),
      'issue_domain_counts':dict(sorted(domains.items())),'signal_counts':dict(sorted(signals.items())),
      'reproducible_observation_count':repro,'evidence_digest':_digest(evidence),'sample_too_small':len(rows)<5,
      'statistical_significance_claimed':False,'transcript_inspected':False,'private_notes_returned':False,'provider_invoked':False,
      'writes_state':False,'content_free':True,'redacted':True}
