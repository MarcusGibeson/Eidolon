from __future__ import annotations
from conversation_target_outcome_learning_v2690 import build_conversation_target_outcome
def build_checkpoint():
 a=build_conversation_target_outcome({'applied':True,'whole_response_replaced':True,'constraint_sentences_removed':1});checks={'repair_detected':a['repair_signal_count']==2,'high':a['severity']=='high','no_policy_mutation':not a['conversation_policy_mutated'],'no_text':not a['raw_response_stored'],'no_provider':not a['provider_contacted'],'no_authority':not a['authority_granted']};return {'ok':all(checks.values()),'checks':checks,'passed':sum(checks.values()),'total':len(checks)}
