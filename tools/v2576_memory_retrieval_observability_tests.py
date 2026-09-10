from pathlib import Path
import tempfile
from conscious_agent.memory_retrieval_observability_v2576 import record_memory_retrieval_observability,load_memory_retrieval_observability

def main():
 with tempfile.TemporaryDirectory() as td:
  p={'retrieval_sufficiency':{'state':'no_useful_memory','selected_count':0,'should_preserve_uncertainty':True},'precision_diagnostics':{},'prompt_budget_diagnostics':{}}
  r=record_memory_retrieval_observability(p,operation_id='turn-1',runtime_root=td);l=load_memory_retrieval_observability(td)
  checks=[r['ok'],r['timeline_status']=='timeline_event_recorded',r['feedback']['state']=='no_useful_memory',l['present'],l['feedback']['state']=='no_useful_memory',r['raw_memory_text_stored'] is False,r['raw_prompt_stored'] is False,r['memory_mutated'] is False,not r['authority_granted']]
 print({'suite':'v2576-memory-retrieval-observability','passed':sum(map(bool,checks)),'total':len(checks),'ok':all(checks)});raise SystemExit(0 if all(checks) else 1)
if __name__=='__main__':main()
