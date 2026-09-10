from conscious_agent.memory_retrieval_learning_advisory_v2582 import build_memory_retrieval_learning_advisory

def main():
 p={'profiles':[{'retrieval_state':'weak_context_only','history_label':'adverse_history','evidence_confidence':.7},{'retrieval_state':'grounded_relevant_memory','history_label':'supportive_history','evidence_confidence':.8}]}
 a=build_memory_retrieval_learning_advisory(p);m={x['retrieval_state']:x for x in a['advisories']}
 checks=[m['weak_context_only']['recommendation']=='review_precision_for_state',m['grounded_relevant_memory']['recommendation']=='retain_current_policy',not a['automatic_policy_change_permitted'],not a['score_mutation_performed'],a['operator_review_required_for_policy_change'],not a['provider_contacted'],len(a['advisory_digest'])==64]
 print({'suite':'v2582-memory-retrieval-learning-advisory','passed':sum(map(bool,checks)),'total':len(checks),'ok':all(checks)});raise SystemExit(0 if all(checks) else 1)
if __name__=='__main__':main()
