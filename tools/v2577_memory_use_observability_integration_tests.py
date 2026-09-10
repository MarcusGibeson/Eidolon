from pathlib import Path
import tempfile
from conscious_agent.memory_retrieval_observability_v2576 import record_memory_retrieval_observability
from conscious_agent.cognitive_observability_v2533 import build_cognitive_observability_snapshot
from conscious_agent import dashboard

def main():
 with tempfile.TemporaryDirectory() as td:
  projection={'retrieval_sufficiency':{'state':'grounded_relevant_memory','selected_count':1,'should_preserve_uncertainty':False},'precision_diagnostics':{'duplicate_suppressed_count':1},'prompt_budget_diagnostics':{'fact_conflict_suppressed_count':0,'budget_suppressed_count':0,'estimated_prompt_chars':120}}
  record_memory_retrieval_observability(projection,operation_id='turn-9',runtime_root=td)
  snap=build_cognitive_observability_snapshot(td,limit=10)
  html=dashboard.render_cognitive_observability_dashboard()
  checks=[snap['memory_retrieval']['present'],snap['memory_retrieval']['feedback']['state']=='grounded_relevant_memory',any(r['event_kind']=='memory' for r in snap['recent']),'mind-memory-state' in html,'mind-memory' in html,'memoryFeedback.state' in html,'preserve uncertainty' in html]
 print({'suite':'v2577-memory-use-observability-integration','passed':sum(map(bool,checks)),'total':len(checks),'ok':all(checks)});raise SystemExit(0 if all(checks) else 1)
if __name__=='__main__':main()
