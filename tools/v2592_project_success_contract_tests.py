from conscious_agent.project_success_contract_v2592 import build_project_success_contract,architecture_acceptance_to_success_contract

def main():
 g='a'*64;c=build_project_success_contract(project_id='p',goal_digest=g,criteria=[{'criterion_id':'latency','metric':'latency_ms','comparison':'less_or_equal','target':100,'required':True}])
 a=architecture_acceptance_to_success_contract({'goal_id':'arch','goal_evidence_digest':g,'acceptance_criteria':{'target_line_count_should_decrease':1000,'target_top_level_symbol_count_should_decrease':100,'baseline_dependency_cycle_count':0}})
 checks=[c['criterion_count']==1,c['criteria'][0]['metric']=='latency_ms',not c['project_completion_authorized'],a['criterion_count']==6,any(x['criterion_id']=='no_new_dependency_cycles' for x in a['criteria']),not a['source_mutation_authorized'],len(c['contract_digest'])==64]
 print({'suite':'v2592-project-success-contract','passed':sum(map(bool,checks)),'total':len(checks),'ok':all(checks)});raise SystemExit(0 if all(checks) else 1)
if __name__=='__main__':main()
