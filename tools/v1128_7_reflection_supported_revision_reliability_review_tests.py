from pathlib import Path
import tempfile
from conscious_agent.reflection_supported_revision_reliability_review import ReflectionSupportedRevisionReliabilityReviewer
x=Path(tempfile.mkdtemp()); r=ReflectionSupportedRevisionReliabilityReviewer(x); a=r.review(target_type='goal',target_id='g'); i=r.inspection_summary(); checks=[a['contract_version']=='v1128.7',a['false_pattern_suppressed'],a['status']=='insufficient_evidence',a['sample_size']==0,i['ok'],not i['visible_status']['raw_content_exposed'],not i['hidden_reasoning_exposed'],not i['revision_applied'],not i['target_revised'],not i['external_action_executed']]; print(f"v1128.7 revision reliability tests: {sum(checks)}/{len(checks)} passed"); raise SystemExit(0 if all(checks) else 1)
