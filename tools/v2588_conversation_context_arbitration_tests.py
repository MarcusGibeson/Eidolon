from conscious_agent.conversation_context_arbitration_v2588 import build_context_relevance_arbitration

def main():
 a=build_context_relevance_arbitration({'budget_pressure':.95,'memory_retrieval_state':'weak_context_only','memories_included':2,'history_turns_included':0,'history_turns_omitted':4,'included_lanes':['memory'],'omitted_lanes':['history']})
 codes={x['code'] for x in a['advisories']}
 checks=['high_prompt_pressure' in codes,'weak_memory_context_present' in codes,'history_fully_omitted' in codes,a['current_message_priority']=='protected',not a['prompt_rebuild_permitted'],not a['context_lane_mutation_performed'],not a['automatic_budget_change_permitted'],not a['provider_contacted'],len(a['arbitration_digest'])==64]
 print({'suite':'v2588-conversation-context-arbitration','passed':sum(map(bool,checks)),'total':len(checks),'ok':all(checks)});raise SystemExit(0 if all(checks) else 1)
if __name__=='__main__':main()
