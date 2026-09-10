from pathlib import Path

def main():
 s=Path('conscious_agent/conversation_runtime.py').read_text();obs=Path('conscious_agent/cognitive_observability_v2533.py').read_text();dash=Path('conscious_agent/dashboard.py').read_text()
 checks=[s.count('build_conversation_context_attribution(')>=2,s.count('build_context_relevance_arbitration(')>=2,s.count('assess_context_sufficiency(')>=2,s.count('record_conversation_context_observability(')>=2,'conversation_context' in obs,'mind-context-state' in dash,'raw_prompt_stored' in Path('conscious_agent/conversation_context_attribution_v2587.py').read_text(), 'automatic_context_truncation_permitted' in Path('conscious_agent/conversation_context_sufficiency_v2589.py').read_text()]
 print({'suite':'v2591.9-conversation-context-attribution-checkpoint','passed':sum(map(bool,checks)),'total':len(checks),'ok':all(checks)});raise SystemExit(0 if all(checks) else 1)
if __name__=='__main__':main()
