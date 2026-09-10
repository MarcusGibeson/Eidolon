from pathlib import Path
import json,tempfile
from conscious_agent.reflection_quality_outcome_lineage import ReflectionQualityOutcomeLineageStore
r=Path(tempfile.mkdtemp()); s=ReflectionQualityOutcomeLineageStore(r); out=s.inspection_summary(); checks=[out['contract_version']=='v1126.6',out['ok'],out['outcome_count']==0,not out['conclusions_exposed'],not out['evidence_text_exposed'],not out['hidden_reasoning_exposed'],not out['belief_updated'],not out['goal_updated'],not out['self_model_updated'],not out['external_action_executed']]; print(json.dumps({'passed':sum(checks),'total':10,'suite':'v1126.6'})); raise SystemExit(0 if all(checks) else 1)
