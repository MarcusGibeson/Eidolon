from conscious_agent.precision_memory_retrieval_v2569 import refine_memory_retrieval

def main():
 base={'selected_memory_records':[{'content':'alpha'},{'content':'alpha'},{'content':'weak'}],'decisions':[{'selected':True,'reason':'literal_relevance'},{'selected':True,'reason':'literal_relevance'},{'selected':True,'reason':'bounded_context'}]}
 o=refine_memory_retrieval(base);d=o['precision_diagnostics']
 checks=[len(o['selected_memory_records'])==1,o['selected_memory_records'][0]['content']=='alpha',d['duplicate_suppressed_count']==1,d['weak_context_suppressed_count']==1,d['precise_evidence_present'],d['memory_mutated'] is False,d['provider_contacted'] is False,d['raw_memory_text_stored'] is False,not d['action_execution_authorized'],len(d['diagnostics_digest'])==64]
 print({'suite':'v2569-precision-memory-retrieval','passed':sum(map(bool,checks)),'total':len(checks),'ok':all(checks)});raise SystemExit(0 if all(checks) else 1)
if __name__=='__main__':main()
