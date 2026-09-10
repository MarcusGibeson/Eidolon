import json
from pathlib import Path
from conscious_agent.architecture_consolidation_reliability import build_architecture_consolidation_reliability
ROOT=Path(__file__).resolve().parents[1]
r=build_architecture_consolidation_reliability(source_root=str(ROOT))
checks=[r['contract_version']=='v1147.7',r['classification']=='reliable',r['reliability_score']==100,r['uncertainty']==0,r['checkpoint_dispatch_failure_count']==0,r['duplicate_plumbing_count']==0,r['historical_modules_preserved'],not r['deferred_tier_started'],r['content_free'] and r['read_only'],not r['provider_contacted']]
assert all(checks); print(json.dumps({'suite':'v1147.7','passed':len(checks),'total':len(checks)}))
