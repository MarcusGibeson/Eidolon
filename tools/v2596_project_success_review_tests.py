from conscious_agent.project_success_review_v2596 import build_project_success_review_packet

def main():
 r=build_project_success_review_packet({'project_id':'p','goal_digest':'a'*64,'evaluation_digest':'b'*64,'criteria_satisfied':True,'evidence_complete':True,'failed_required_criteria':[]},{'candidate_digest':'c'*64});f=build_project_success_review_packet({'project_id':'p','goal_digest':'a'*64,'evaluation_digest':'d'*64,'criteria_satisfied':False,'evidence_complete':True,'failed_required_criteria':['x']})
 checks=[r['review_disposition']=='ready_for_operator_completion_review',r['operator_completion_decision_required'],not r['project_completed'],not r['automatic_completion_permitted'],f['review_disposition']=='project_outcome_requires_more_work',not f['operator_completion_decision_required'],not r['durable_lesson_committed'],len(r['review_digest'])==64]
 print({'suite':'v2596-project-success-review','passed':sum(map(bool,checks)),'total':len(checks),'ok':all(checks)});raise SystemExit(0 if all(checks) else 1)
if __name__=='__main__':main()
