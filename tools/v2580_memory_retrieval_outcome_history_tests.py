import tempfile
from conscious_agent.memory_retrieval_outcome_v2579 import build_memory_retrieval_outcome
from conscious_agent.memory_retrieval_outcome_history_v2580 import append_memory_retrieval_outcome,load_memory_retrieval_outcome_history

def main():
 with tempfile.TemporaryDirectory() as d:
  o=build_memory_retrieval_outcome({'state':'weak_context_only','selected_count':1},turn_completed=True,uncertainty_preserved=True)
  a=append_memory_retrieval_outcome(o,operation_id='conversation_1',runtime_root=d);append_memory_retrieval_outcome(o,operation_id='conversation_1',runtime_root=d);h=load_memory_retrieval_outcome_history(d)
  checks=[a['row_count']==1,len(h['rows'])==1,h['rows'][0]['outcome_disposition']=='appropriate_restraint',h['raw_memory_text_stored'] is False,not a['memory_mutated'],not a['policy_mutated'],len(a['history_digest'])==64]
 print({'suite':'v2580-memory-retrieval-outcome-history','passed':sum(map(bool,checks)),'total':len(checks),'ok':all(checks)});raise SystemExit(0 if all(checks) else 1)
if __name__=='__main__':main()
