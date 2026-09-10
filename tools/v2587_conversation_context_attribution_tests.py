from conscious_agent.conversation_context_attribution_v2587 import build_conversation_context_attribution

def main():
 m={'input_budget_tokens':1000,'estimated_prompt_tokens':800,'memory_candidates':6,'memories_included':2,'memories_omitted':4,'history_turn_candidates':5,'history_turns_included':2,'history_turns_omitted':3,'context_lanes_included':['memory','history'],'context_lanes_omitted':['project']}
 a=build_conversation_context_attribution(m,{'state':'grounded_relevant_memory','should_preserve_uncertainty':False})
 checks=[a['budget_pressure']==.8,a['headroom_tokens']==200,a['memories_included']==2,a['history_turns_omitted']==3,a['memory_retrieval_state']=='grounded_relevant_memory',a['current_message_protected'],a['raw_prompt_stored'] is False,a['raw_context_stored'] is False,not a['context_mutated'],len(a['attribution_digest'])==64]
 print({'suite':'v2587-conversation-context-attribution','passed':sum(map(bool,checks)),'total':len(checks),'ok':all(checks)});raise SystemExit(0 if all(checks) else 1)
if __name__=='__main__':main()
