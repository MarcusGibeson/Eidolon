from pathlib import Path

def main():
 files=['conscious_agent/memory_retrieval_outcome_v2579.py','conscious_agent/memory_retrieval_outcome_history_v2580.py','conscious_agent/memory_retrieval_learning_profile_v2581.py','conscious_agent/memory_retrieval_learning_advisory_v2582.py','conscious_agent/memory_retrieval_followup_learning_v2583.py','conscious_agent/memory_retrieval_learning_observability_v2584.py','conscious_agent/memory_retrieval_policy_review_v2585.py']
 s=Path('conscious_agent/conversation_runtime.py').read_text();obs=Path('conscious_agent/cognitive_observability_v2533.py').read_text();dash=Path('conscious_agent/dashboard.py').read_text()
 checks=[all(Path(f).exists() for f in files),s.count('learn_from_followup_correction(')>=2,s.count('load_memory_retrieval_observability()')>=2,'memory_retrieval_learning' in obs,'Memory learning' in dash,'automatic_policy_change_permitted' in Path('conscious_agent/memory_retrieval_policy_review_v2585.py').read_text(),'raw_memory_text_stored' in Path('conscious_agent/memory_retrieval_outcome_v2579.py').read_text()]
 print({'suite':'v2586.9-memory-retrieval-outcome-learning-checkpoint','passed':sum(map(bool,checks)),'total':len(checks),'ok':all(checks)});raise SystemExit(0 if all(checks) else 1)
if __name__=='__main__':main()
