from conscious_agent.memory_retrieval_feedback_v2575 import build_memory_retrieval_feedback

def main():
 p={'retrieval_sufficiency':{'state':'weak_context_only','selected_count':2,'should_preserve_uncertainty':True},'precision_diagnostics':{'duplicate_suppressed_count':1,'weak_context_suppressed_count':2},'prompt_budget_diagnostics':{'fact_conflict_suppressed_count':1,'budget_suppressed_count':1,'estimated_prompt_chars':700}}
 o=build_memory_retrieval_feedback(p)
 checks=[o['state']=='weak_context_only',o['selected_count']==2,o['duplicate_suppressed_count']==1,o['fact_conflict_suppressed_count']==1,o['should_preserve_uncertainty'],o['raw_memory_text_stored'] is False,not o['memory_mutation_authorized'],not o['response_claim_authorized'],len(o['feedback_digest'])==64]
 print({'suite':'v2575-memory-retrieval-feedback','passed':sum(map(bool,checks)),'total':len(checks),'ok':all(checks)});raise SystemExit(0 if all(checks) else 1)
if __name__=='__main__':main()
