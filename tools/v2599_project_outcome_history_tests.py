import tempfile
from conscious_agent.project_outcome_history_v2599 import append_project_outcome_history,load_project_outcome_history

def main():
 r={'project_id':'p','goal_digest':'a'*64,'review_digest':'b'*64,'criteria_satisfied':True,'evidence_complete':True,'failed_required_criteria':[]}
 with tempfile.TemporaryDirectory() as d:
  x=append_project_outcome_history(r,strategy_code='refactor',predicted_value=1,realized_value=.8,effort_units=3,runtime_root=d);append_project_outcome_history(r,strategy_code='refactor',runtime_root=d);h=load_project_outcome_history(d)
  checks=[x['row_count']==1,len(h['rows'])==1,h['rows'][0]['strategy_code']=='refactor',h['rows'][0]['realized_value']==.8,h['raw_project_content_stored'] is False,not x['project_completed'],not x['strategy_policy_mutated'],len(x['history_digest'])==64]
 print({'suite':'v2599-project-outcome-history','passed':sum(map(bool,checks)),'total':len(checks),'ok':all(checks)});raise SystemExit(0 if all(checks) else 1)
if __name__=='__main__':main()
