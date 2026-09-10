from conscious_agent.memory_retrieval_budget_v2571 import apply_memory_retrieval_budget

def main():
 p={'selected_memory_records':[{'content':'old','fact_key':'pet','age_band':'historical'},{'content':'new','fact_key':'pet','current':True},{'content':'x'*700},{'content':'y'*700}]}
 o=apply_memory_retrieval_budget(p,max_chars=900);d=o['prompt_budget_diagnostics'];contents=[r['content'] for r in o['selected_memory_records']]
 checks=['new' in contents,'old' not in contents,d['fact_conflict_suppressed_count']==1,d['budget_suppressed_count']>=1,d['estimated_prompt_chars']<=900,d['memory_mutated'] is False,d['provider_contacted'] is False,d['raw_memory_text_stored'] is False,not d['action_execution_authorized'],len(d['diagnostics_digest'])==64]
 print({'suite':'v2571-memory-retrieval-budget','passed':sum(map(bool,checks)),'total':len(checks),'ok':all(checks)});raise SystemExit(0 if all(checks) else 1)
if __name__=='__main__':main()
