from conscious_agent.memory_retrieval_outcome_v2579 import build_memory_retrieval_outcome

def main():
 f={'state':'grounded_relevant_memory','selected_count':2}
 pos=build_memory_retrieval_outcome(f,turn_completed=True,memory_supported_resolution=True)
 neg=build_memory_retrieval_outcome(f,turn_completed=True,correction_detected=True)
 empty=build_memory_retrieval_outcome({'state':'no_useful_memory','selected_count':0},turn_completed=True,uncertainty_preserved=True)
 checks=[pos['outcome_disposition']=='positive_evidence',neg['outcome_disposition']=='negative_evidence',empty['outcome_disposition']=='appropriate_restraint',not pos['memory_mutation_authorized'],not pos['retrieval_policy_mutation_authorized'],pos['raw_memory_text_stored'] is False,pos['raw_response_stored'] is False,len(pos['outcome_digest'])==64]
 print({'suite':'v2579-memory-retrieval-outcome','passed':sum(map(bool,checks)),'total':len(checks),'ok':all(checks)});raise SystemExit(0 if all(checks) else 1)
if __name__=='__main__':main()
