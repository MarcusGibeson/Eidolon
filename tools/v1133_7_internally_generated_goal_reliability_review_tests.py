from pathlib import Path
from tempfile import TemporaryDirectory
from conscious_agent.internally_generated_goal_reliability_review import InternallyGeneratedGoalReliabilityReviewer
with TemporaryDirectory() as td:
 r=InternallyGeneratedGoalReliabilityReviewer(Path(td)); x=r.review(goal_class='development'); assert x['status']=='insufficient_evidence' and x['false_pattern_suppressed']; assert not x['external_action_executed']; s=r.inspection_summary(); assert s['ok'] and not s['visible_status']['raw_content_exposed']
print('v1133.7 checks: 5/5')
