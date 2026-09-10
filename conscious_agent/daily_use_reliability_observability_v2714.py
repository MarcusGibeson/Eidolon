from __future__ import annotations
"""v2714 read-only daily-use reliability observability."""
from typing import Any
from daily_use_reliability_history_v2711 import load_daily_use_reliability_history, build_daily_use_reliability_trend
CONTRACT_VERSION='v2714.0'
def build_daily_use_reliability_observability(runtime_root=None)->dict[str,Any]:
    rows=load_daily_use_reliability_history(runtime_root).get('rows') or [];latest=dict(rows[-1]) if rows else {};trend=build_daily_use_reliability_trend(rows)
    return {'ok':True,'contract_version':CONTRACT_VERSION,'state':str(latest.get('state') or 'no_history'),'observation_count':len(rows),'concern_count':int(latest.get('concern_count') or 0),'strength_count':int(latest.get('strength_count') or 0),'unknown_dimension_count':int(latest.get('unknown_dimension_count') or 0),'trend':trend,'automatic_action':False,'automatic_policy_change':False,'raw_conversation_text_stored':False,'authority_granted':False}
__all__=['CONTRACT_VERSION','build_daily_use_reliability_observability']
