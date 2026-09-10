from conscious_agent.developer_portfolio_checkpoint_v2617 import build_developer_portfolio_review

def main():
 rows=[{'project_id':'a','strategy_code':'safe','expected_value':.8,'effort':2,'risk':.2,'operator_priority':.7,'verification_confidence':.8,'exclusive_resources':['repo']},{'project_id':'b','strategy_code':'safe','expected_value':.79,'effort':2,'risk':.2,'operator_priority':.7,'verification_confidence':.8,'exclusive_resources':['repo'],'depends_on':['missing']}]
 x=build_developer_portfolio_review(rows)
 checks=[x['ok'],x['conflicts']['conflict_count']>=2,x['sensitivity']['state'] in {'fragile','close'},x['review']['operator_selection_required'],not x['automatic_project_selection_permitted'],not x['campaign_start_authorized'],not x['source_mutation_authorized'],not x['authority_granted']]
 print({'suite':'v2615-v2617-portfolio-conflict-sensitivity','passed':sum(map(bool,checks)),'total':len(checks),'ok':all(checks)});raise SystemExit(0 if all(checks) else 1)
if __name__=='__main__':main()
