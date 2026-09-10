from pathlib import Path
import json,tempfile
from conscious_agent.reflection_quality_reliability_review import ReflectionQualityReliabilityReviewer
r=ReflectionQualityReliabilityReviewer(Path(tempfile.mkdtemp())); x=r.review(reflection_outcome_id='missing'); checks=[x['contract_version']=='v1126.7',x['ok'],x['sample_size']==0,x['false_pattern_suppressed'],x['status']=='insufficient_evidence',not x['belief_updated'],not x['goal_updated'],not x['self_model_updated'],not x['message_sent'],not x['external_action_executed']]; print(json.dumps({'passed':sum(checks),'total':10,'suite':'v1126.7'})); raise SystemExit(0 if all(checks) else 1)
