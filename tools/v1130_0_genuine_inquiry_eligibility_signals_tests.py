from pathlib import Path
import tempfile
from conscious_agent.genuine_inquiry_eligibility_signals import GenuineInquiryEligibilitySignalStore
root=Path(tempfile.mkdtemp()); s=GenuineInquiryEligibilitySignalStore(root)
a=s.register('e1',origin_ids=['reflection-1'],source_categories=['uncertainty','knowledge_gap'],purpose='resolve_uncertainty',relevance=.8,importance=.7,uncertainty=.9,knowledge_gap=.8,contradiction_strength=.1,unfinished_thought_strength=.2,curiosity_strength=.6,cognitive_cost=.3,confidence=.8,structural_digest='abc')
b=s.register('e2',origin_ids=['reflection-2'],source_categories=['curiosity'],purpose='bounded_exploration',relevance=.4,importance=.2,uncertainty=.4,knowledge_gap=.3,contradiction_strength=0,unfinished_thought_strength=.1,curiosity_strength=.3,cognitive_cost=.2,novelty_only=True)
c=s.register('e1',origin_ids=['reflection-1'],source_categories=['uncertainty'],purpose='resolve_uncertainty',relevance=.8,importance=.7,uncertainty=.9,knowledge_gap=.8,contradiction_strength=.1,unfinished_thought_strength=.2,curiosity_strength=.6,cognitive_cost=.3)
r=s.inspection_summary(); checks=[a['result']['state']=='active',b['result']['state']=='suppressed',c['idempotent'],r['signal_count']==2,r['contract_version']=='v1130.0',not any(r['authority_boundary'].values()),not r['raw_content_exposed'],not r['question_text_exposed'],not r['provider_contacted'],not r['browser_contacted']];print(f"v1130.0 genuine inquiry eligibility tests: {sum(checks)}/{len(checks)} passed");raise SystemExit(0 if all(checks) else 1)
