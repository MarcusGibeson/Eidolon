from conscious_agent.project_outcome_evidence_v2593 import build_project_outcome_evidence

def main():
 e=build_project_outcome_evidence(project_id='p',goal_digest='b'*64,current_metrics={'latency_ms':90,'bad':[]},verification={'passed':True,'unexplained_regression_count':0,'behavior_preserved':True,'verification_digest':'c'*64},governance={'governance_authority_unchanged':True})
 checks=[e['current_metrics']['latency_ms']==90,'bad' not in e['current_metrics'],e['verification']['passed'],e['verification']['behavior_preserved'],e['raw_test_output_stored'] is False,e['raw_source_stored'] is False,not e['source_modified'],len(e['evidence_digest'])==64]
 print({'suite':'v2593-project-outcome-evidence','passed':sum(map(bool,checks)),'total':len(checks),'ok':all(checks)});raise SystemExit(0 if all(checks) else 1)
if __name__=='__main__':main()
