from conscious_agent.project_strategy_developer_evidence_v2603 import build_project_strategy_developer_evidence

def main():
 x=build_project_strategy_developer_evidence({'candidates':[{'strategy_code':'a','recommendation':'review_strategy_before_reuse','reliability':'underperforming','calibration':'over'}]});checks=[x['evidence_count']==1,x['strategy_evidence'][0]['strategy_code']=='a',not x['candidate_selection_authorized'],not x['campaign_start_authorized'],not x['source_mutation_authorized'],not x['automatic_priority_change_permitted'],x['raw_project_content_stored'] is False,len(x['evidence_digest'])==64]
 print({'suite':'v2603-project-strategy-developer-evidence','passed':sum(map(bool,checks)),'total':len(checks),'ok':all(checks)});raise SystemExit(0 if all(checks) else 1)
if __name__=='__main__':main()
