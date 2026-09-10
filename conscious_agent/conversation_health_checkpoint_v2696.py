from __future__ import annotations
from conversation_policy_review_v2695 import build_conversation_policy_review_packet
def build_checkpoint():
 h={'state':'attention','concern_count':1,'concerns':['conversation_target_coherence_review_due'],'health_digest':'a'*64};r=build_conversation_policy_review_packet(h);checks={'review':r['review_required'],'target_review':'review_target_and_repetition_policy' in r['action_codes'],'no_policy':not r['automatic_policy_change'],'no_prompt':not r['automatic_prompt_change'],'no_rewrite':not r['automatic_response_rewrite'],'no_provider':not r['provider_contacted'],'no_authority':not r['authority_granted']};return {'ok':all(checks.values()),'checks':checks,'passed':sum(checks.values()),'total':len(checks)}
