import importlib
import json
from conscious_agent.architecture_ownership_manifest import build_architecture_ownership_manifest
r=build_architecture_ownership_manifest(); checks=[r['contract_version']=='v1147.0',r['domain_count']==9,r['unique_owner_count']==9,not r['duplicate_domain_owners'],all(x['owner_id'] and x['structural_digest'] for x in r['domains']),all(x['startup_tier'] in {'core','conversation_critical','deferred'} for x in r['domains']),all(importlib.import_module(x['owner_module']) for x in r['domains']),r['content_free'] and r['read_only'],not any(r['authority_boundary'].values())]
assert all(checks); print(json.dumps({'suite':'v1147.0','passed':len(checks),'total':len(checks)}))
