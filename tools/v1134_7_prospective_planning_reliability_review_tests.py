from pathlib import Path
from tempfile import TemporaryDirectory
from conscious_agent.prospective_planning_reliability_review import ProspectivePlanningReliabilityReviewer
with TemporaryDirectory() as td:
 r=ProspectivePlanningReliabilityReviewer(Path(td)); x=r.review(plan_class='development'); assert x['status']=='insufficient_evidence' and x['false_pattern_suppressed']; assert not x['external_action_executed']; s=r.inspection_summary(); assert s['ok'] and not s['visible_status']['raw_content_exposed']
print('v1134.7 checks: 5/5')
