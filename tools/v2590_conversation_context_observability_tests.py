import tempfile
from conscious_agent.conversation_context_observability_v2590 import record_conversation_context_observability,load_conversation_context_observability

def main():
 with tempfile.TemporaryDirectory() as d:
  r=record_conversation_context_observability({'budget_pressure':.8,'headroom_tokens':200,'memories_included':2,'history_turns_included':1},{'advisory_count':1},{'state':'context_supported','should_preserve_uncertainty':False},operation_id='conversation_test',runtime_root=d);x=load_conversation_context_observability(d)
  checks=[r['state']=='context_supported',x['present'],x['headroom_tokens']==200,x['memories_included']==2,x['raw_prompt_stored'] is False,x['raw_context_stored'] is False,not r['context_mutated'],not r['authority_granted'],len(r['state_digest'])==64]
 print({'suite':'v2590-conversation-context-observability','passed':sum(map(bool,checks)),'total':len(checks),'ok':all(checks)});raise SystemExit(0 if all(checks) else 1)
if __name__=='__main__':main()
