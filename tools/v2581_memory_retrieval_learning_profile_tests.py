from conscious_agent.memory_retrieval_learning_profile_v2581 import build_memory_retrieval_learning_profile

def main():
 rows=[{'retrieval_state':'grounded_relevant_memory','outcome_disposition':'positive_evidence'} for _ in range(5)]+[{'retrieval_state':'weak_context_only','outcome_disposition':'negative_evidence','correction_detected':True} for _ in range(4)]
 p=build_memory_retrieval_learning_profile(rows);m={x['retrieval_state']:x for x in p['profiles']}
 checks=[m['grounded_relevant_memory']['history_label']=='supportive_history',m['weak_context_only']['history_label']=='adverse_history',p['observation_count']==9,not p['retrieval_policy_mutated'],not p['automatic_weight_change_permitted'],p['raw_content_stored'] is False,len(p['profile_digest'])==64]
 print({'suite':'v2581-memory-retrieval-learning-profile','passed':sum(map(bool,checks)),'total':len(checks),'ok':all(checks)});raise SystemExit(0 if all(checks) else 1)
if __name__=='__main__':main()
