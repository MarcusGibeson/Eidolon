import json, os, tempfile
os.environ['PYTHONDONTWRITEBYTECODE']='1'; os.environ['EIDOLON_DATA_DIR']=tempfile.mkdtemp()
from conscious_agent.architecture_startup_consolidation import build_startup_tier_plan, inspect_startup_consolidation, run_bounded_startup_tier
from conscious_agent.conversation_startup_runtime import _reset_conversation_startup_for_tests
_reset_conversation_startup_for_tests(); plan=build_startup_tier_plan(); tiers={r['tier']:r for r in plan['tiers']}
checks=[plan['contract_version']=='v1147.4',plan['tier_order']==['core','conversation_critical','deferred'],tiers['conversation_critical']['automatic_execution_allowed'],not tiers['deferred']['automatic_execution_allowed'],plan['deferred_tier_remains_lazy'],not plan['provider_contact_allowed']]
deferred=run_bounded_startup_tier('deferred'); checks += [deferred['outcome']=='deferred',not deferred['execution_performed'],not deferred['provider_contacted']]
critical=run_bounded_startup_tier('conversation_critical'); checks += [critical['execution_performed'],critical['outcome'] in {'ready','review_required'},not critical['provider_contacted'],not critical['accepted_turn_replayed'],not critical['deferred_services_started']]
inspection=inspect_startup_consolidation(); checks += [inspection['read_only'],not inspection['runtime_mutated'],not inspection['deferred_tier_started']]
assert all(checks); print(json.dumps({'suite':'v1147.4','passed':len(checks),'total':len(checks)}))
