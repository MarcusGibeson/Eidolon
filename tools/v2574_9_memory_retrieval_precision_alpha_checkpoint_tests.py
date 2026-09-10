from conscious_agent.memory_retrieval_relevance import build_memory_retrieval_relevance
from conscious_agent.precision_memory_retrieval_v2569 import refine_memory_retrieval
from conscious_agent.memory_retrieval_budget_v2571 import apply_memory_retrieval_budget
from conscious_agent.memory_retrieval_sufficiency_v2573 import assess_memory_retrieval_sufficiency

def main():
 rows=[{'content':'Marcus likes local AI','fact_key':'pref','current':True},{'content':'Marcus likes local AI','fact_key':'pref'},{'content':'irrelevant historical filler'}]
 refs=[{'relevance_score':8,'age_band':'current','confidence_band':'high'},{'relevance_score':1,'age_band':'historical','confidence_band':'medium'},{'relevance_score':0,'age_band':'archival','confidence_band':'low'}]
 base=build_memory_retrieval_relevance('local AI',rows,refs); precise=refine_memory_retrieval(base); bounded=apply_memory_retrieval_budget(precise,max_chars=600); suff=assess_memory_retrieval_sufficiency(bounded)
 checks=[len(base['selected_memory_records'])>=1,len(bounded['selected_memory_records'])==1,bounded['prompt_budget_diagnostics']['estimated_prompt_chars']<=600,suff['state']=='grounded_relevant_memory',not suff['should_preserve_uncertainty'],not bounded['precision_diagnostics']['memory_mutated'],not bounded['prompt_budget_diagnostics']['memory_mutated'],not suff['provider_contact_authorized'],not suff['response_claim_authorized'],len(suff['sufficiency_digest'])==64]
 print({'suite':'v2574.9-memory-retrieval-precision-alpha-checkpoint','passed':sum(map(bool,checks)),'total':len(checks),'ok':all(checks)});raise SystemExit(0 if all(checks) else 1)
if __name__=='__main__':main()
