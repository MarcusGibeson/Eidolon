from pathlib import Path
import json,tempfile
from conscious_agent.thought_thread_outcome_lineage import ThoughtThreadOutcomeLineageStore
s=ThoughtThreadOutcomeLineageStore(Path(tempfile.mkdtemp())); out=s.inspection_summary(); checks=[out['contract_version']=='v1127.6',out['ok'],out['outcome_count']==0,not out['raw_content_exposed'],not out['hidden_reasoning_exposed'],not out['provider_contacted'],not out['reflection_created'],not out['belief_updated'],not out['message_sent'],not out['external_action_executed']]; print(json.dumps({'passed':sum(checks),'total':10,'suite':'v1127.6'})); raise SystemExit(0 if all(checks) else 1)
