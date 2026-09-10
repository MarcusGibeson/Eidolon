import json
from conscious_agent.checkpoint_registry import inspect_checkpoint_registry, resolve_checkpoint_builder
r=inspect_checkpoint_registry(); checks=[r['contract_version']=='v1150.2',r['checkpoint_count']>=150,not r['duplicate_checkpoint_ids'],r['read_only'],all(x['read_only_required'] and not x['post_available'] for x in r['checkpoints']),callable(resolve_checkpoint_builder('conversation-cognition-unification')),callable(resolve_checkpoint_builder('understandable-cognitive-controls')),r['content_free'],r['all_compatibility_targets_available']]
assert all(checks); print(json.dumps({'suite':'v1147.1-compatibility','passed':len(checks),'total':len(checks)}))
