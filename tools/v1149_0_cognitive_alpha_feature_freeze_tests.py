from conscious_agent.cognitive_alpha_feature_freeze import build_cognitive_alpha_feature_freeze
r=build_cognitive_alpha_feature_freeze();checks=[r['contract_version']=='v1149.0',r['feature_count']==12,not r['duplicate_feature_ids'],not r['new_feature_intake_open'],all(not x['new_capability_allowed'] for x in r['features']),all(x['repair_allowed'] for x in r['features']),all(x['operator_review_required'] for x in r['features']),not any(r['authority_boundary'].values()),r['content_free']]
print(f"v1149.0: {sum(checks)}/{len(checks)}");raise SystemExit(0 if all(checks) else 1)
