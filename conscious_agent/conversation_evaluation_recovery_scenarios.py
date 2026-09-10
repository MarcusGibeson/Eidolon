from __future__ import annotations
"""v1087.5 structured restart/outage evaluation coverage without provider calls."""
from typing import Any
from conversation_daily_evaluation import load_daily_evaluation
REQUIRED_RECOVERY_SIGNALS=('restart_resume','provider_outage','provider_return','generation_interruption','failed_retry','completed_regeneration','explicit_resend')
def build_restart_outage_evaluation(evaluation_id:str)->dict[str,Any]:
    summary=load_daily_evaluation(evaluation_id); observed={str(s) for row in summary.get('observations') or () for s in row.get('signals') or ()}
    coverage={s:(s in observed) for s in REQUIRED_RECOVERY_SIGNALS}; missing=[s for s,v in coverage.items() if not v]
    return {'type':'desktop_alpha_restart_outage_evaluation','schema_version':'1','evaluation_id':summary['evaluation_id'],
      'evaluation_state':summary['state'],'required_signals':list(REQUIRED_RECOVERY_SIGNALS),'signal_coverage':coverage,
      'covered_count':sum(coverage.values()),'required_count':len(coverage),'missing_signals':missing,
      'coverage_status':'complete' if not missing else 'incomplete','automatic_replay_allowed':False,'automatic_resend_allowed':False,
      'provider_invoked':False,'generation_invoked':False,'writes_state':False,'operator_observation_required':True,
      'content_free':True,'redacted':True}
