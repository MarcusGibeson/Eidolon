import tempfile
from conscious_agent.memory_retrieval_outcome_v2579 import build_memory_retrieval_outcome
from conscious_agent.memory_retrieval_outcome_history_v2580 import append_memory_retrieval_outcome
from conscious_agent.memory_retrieval_learning_observability_v2584 import build_memory_retrieval_learning_observability

def main():
 with tempfile.TemporaryDirectory() as d:
  for i in range(4):
   o=build_memory_retrieval_outcome({'state':'weak_context_only','selected_count':1},turn_completed=True,correction_detected=True)
   append_memory_retrieval_outcome(o,operation_id=f'conversation_{i}',runtime_root=d)
  x=build_memory_retrieval_learning_observability(d)
  checks=[x['state']=='attention',x['observation_count']==4,x['adverse_state_count']==1,x['profiles'][0]['history_label']=='adverse_history',not x['automatic_policy_change_permitted'],not x['memory_mutation_permitted'],x['raw_memory_text_stored'] is False,x['raw_response_stored'] is False]
 print({'suite':'v2584-memory-retrieval-learning-observability','passed':sum(map(bool,checks)),'total':len(checks),'ok':all(checks)});raise SystemExit(0 if all(checks) else 1)
if __name__=='__main__':main()
