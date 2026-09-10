from conscious_agent.memory_retrieval_policy_review_v2585 import build_memory_retrieval_policy_review_packet

def main():
 o={'profiles':[{'retrieval_state':'weak_context_only','history_label':'adverse_history','count':8,'negative':4,'corrections':3,'evidence_confidence':.67}]}
 p=build_memory_retrieval_policy_review_packet(o)
 checks=[p['review_required'],p['operator_selection_required'],p['candidates'][0]['retrieval_state']=='weak_context_only',not p['automatic_policy_change_permitted'],not p['retrieval_weights_changed'],not p['thresholds_changed'],not p['memory_mutated'],not p['source_mutated'],p['raw_content_stored'] is False,len(p['review_digest'])==64]
 print({'suite':'v2585-memory-retrieval-policy-review','passed':sum(map(bool,checks)),'total':len(checks),'ok':all(checks)});raise SystemExit(0 if all(checks) else 1)
if __name__=='__main__':main()
