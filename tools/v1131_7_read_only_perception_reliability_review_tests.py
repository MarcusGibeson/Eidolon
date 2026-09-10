from pathlib import Path
import tempfile
from conscious_agent.read_only_perception_reliability_review import ReadOnlyPerceptionReliabilityReviewer
root=Path(tempfile.mkdtemp()); r=ReadOnlyPerceptionReliabilityReviewer(root); x=r.review(category='failure'); checks=[x['ok'],x['contract_version']=='v1131.7',x['false_pattern_suppressed'],x['status']=='insufficient_evidence',x['operator_review_proposal'] is None,not x['raw_file_content_exposed'],not x['filesystem_modified']]
print(f"v1131.7 perception reliability tests: {sum(checks)}/{len(checks)} passed"); raise SystemExit(0 if all(checks) else 1)
