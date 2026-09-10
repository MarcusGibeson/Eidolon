from __future__ import annotations
from tempfile import TemporaryDirectory
from daily_use_reliability_runtime_v2713 import build_daily_use_runtime_reliability
from daily_use_reliability_observability_v2714 import build_daily_use_reliability_observability

def build_checkpoint():
    with TemporaryDirectory() as td:
        r=build_daily_use_runtime_reliability(operation_id='daily-op',runtime_root=td);o=build_daily_use_reliability_observability(td)
        checks={'runtime':r['ok'],'history_written':o['observation_count']==1,'state_explicit':o['state'] in {'nominal','attention','degraded','insufficient_data'},'trend':o['trend']['direction']=='insufficient_history','no_action':not r['automatic_action'] and not o['automatic_action'],'no_policy':not o['automatic_policy_change'],'no_text':not o['raw_conversation_text_stored'],'no_authority':not r['authority_granted'] and not o['authority_granted']}
        return {'ok':all(checks.values()),'checks':checks,'passed':sum(checks.values()),'total':len(checks)}
__all__=['build_checkpoint']
