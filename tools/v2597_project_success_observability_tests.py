import tempfile
from conscious_agent.project_success_review_v2596 import build_project_success_review_packet
from conscious_agent.project_success_observability_v2597 import record_project_success_observability,load_project_success_observability

def main():
 with tempfile.TemporaryDirectory() as d:
  p=build_project_success_review_packet({'project_id':'p','goal_digest':'a'*64,'evaluation_digest':'b'*64,'criteria_satisfied':True,'evidence_complete':True,'failed_required_criteria':[]});r=record_project_success_observability(p,runtime_root=d);x=load_project_success_observability(d)
  checks=[x['present'],r['criteria_satisfied'],r['operator_completion_decision_required'],not r['project_completed'],r['raw_project_content_stored'] is False,not r['authority_granted'],not r['source_mutated'],len(r['project_ref_digest'])==64]
 print({'suite':'v2597-project-success-observability','passed':sum(map(bool,checks)),'total':len(checks),'ok':all(checks)});raise SystemExit(0 if all(checks) else 1)
if __name__=='__main__':main()
