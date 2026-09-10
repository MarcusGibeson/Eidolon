from conscious_agent.conversation_outcome_attribution_v2700 import build_conversation_outcome_attribution
from conscious_agent.response_quality_evaluation_v2701 import evaluate_response_quality

def run():
    checks=[]
    def ck(name, cond): checks.append((name, bool(cond)))
    u=build_conversation_outcome_attribution()
    ck('silence_unknown',u['disposition']=='unknown' and not u['silence_treated_as_success'])
    q=evaluate_response_quality(u); ck('unknown_preserved',q['state']=='unknown' and q['unknown_preserved'])
    a=build_conversation_outcome_attribution(grounding_feedback={'adverse_calibration_evidence':True})
    ck('grounding_adverse',a['disposition']=='adverse' and 'grounding_correction_or_retraction' in a['negative_signals'])
    qa=evaluate_response_quality(a); ck('negative_learning',qa['eligible_for_negative_learning'] and not qa['eligible_for_positive_learning'])
    p=build_conversation_outcome_attribution(explicit_resolution={'explicit':True,'kind':'confirmed_resolution'})
    ck('explicit_positive_only',p['disposition']=='supported_positive' and p['positive_signal_count']==1)
    qp=evaluate_response_quality(p); ck('positive_learning_requires_explicit',qp['eligible_for_positive_learning'])
    m=build_conversation_outcome_attribution(memory_feedback={'state':'weak_context_only','should_preserve_uncertainty':True})
    ck('weak_memory_restraint_not_negative',m['disposition']=='unknown' and 'weak_memory_uncertainty_preserved' in m['neutral_signals'])
    bad=build_conversation_outcome_attribution(memory_feedback={'state':'weak_context_only','should_preserve_uncertainty':False})
    ck('weak_memory_overclaim_negative',bad['disposition']=='adverse')
    mix=build_conversation_outcome_attribution(target_outcome={'repair_signal_count':1},explicit_resolution={'explicit':True,'kind':'accepted_answer'})
    ck('mixed_preserved',mix['disposition']=='mixed')
    ck('content_minimized',not mix['raw_prompt_stored'] and not mix['raw_response_stored'] and not mix['raw_memory_text_stored'])
    ck('no_authority',not mix['authority_granted'] and not evaluate_response_quality(mix)['automatic_policy_change'])
    return {'ok':all(v for _,v in checks),'checks':checks,'passed':sum(v for _,v in checks),'total':len(checks)}
if __name__=='__main__':
    r=run();print(r);raise SystemExit(0 if r['ok'] else 1)
