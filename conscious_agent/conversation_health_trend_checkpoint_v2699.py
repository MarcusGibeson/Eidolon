from __future__ import annotations
from conversation_health_trend_v2698 import build_conversation_health_trend
def build_checkpoint():
 rows=[{'state':'degraded'},{'state':'attention'},{'state':'nominal'},{'state':'nominal'}];t=build_conversation_health_trend(rows,window=2);checks={'trend':t['direction']=='improving','recent_better':t['recent_score']<t['prior_score'],'no_policy':not t['automatic_policy_change'],'no_text':not t['raw_conversation_text_stored'],'no_authority':not t['authority_granted']};return {'ok':all(checks.values()),'checks':checks,'passed':sum(checks.values()),'total':len(checks)}
