from pathlib import Path
import json,tempfile
from conscious_agent.thought_thread_reliability_review import ThoughtThreadReliabilityReviewer
x=ThoughtThreadReliabilityReviewer(Path(tempfile.mkdtemp())).review(thread_id='missing'); checks=[x['contract_version']=='v1127.7',x['ok'],x['sample_size']==0,x['false_pattern_suppressed'],x['status']=='insufficient_evidence',not x['raw_content_exposed'],not x['provider_contacted'],not x['reflection_created'],not x['message_sent'],not x['external_action_executed']]; print(json.dumps({'passed':sum(checks),'total':10,'suite':'v1127.7'})); raise SystemExit(0 if all(checks) else 1)
