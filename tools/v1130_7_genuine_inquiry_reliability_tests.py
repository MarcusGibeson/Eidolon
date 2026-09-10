from pathlib import Path
import tempfile
from conscious_agent.genuine_inquiry_reliability_review import GenuineInquiryReliabilityReviewer
r=Path(tempfile.mkdtemp());v=GenuineInquiryReliabilityReviewer(r);x=v.review(purpose_category='pursue_curiosity');i=v.inspection_summary();checks=[x['ok'],x['contract_version']=='v1130.7',x['false_pattern_suppressed'],x['status']=='insufficient_evidence',i['visible_status']['raw_content_exposed'] is False,not i['message_sent'],not i['notification_created'],not i['initiative_created'],not i['hidden_reasoning_exposed']];print(f"v1130.7 genuine inquiry reliability tests: {sum(checks)}/{len(checks)} passed");raise SystemExit(0 if all(checks) else 1)
