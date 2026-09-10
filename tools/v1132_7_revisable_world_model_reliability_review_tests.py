from tempfile import TemporaryDirectory
from conscious_agent.revisable_world_model_reliability_review import RevisableWorldModelReliabilityReviewer
with TemporaryDirectory() as td:
 out=RevisableWorldModelReliabilityReviewer(td).review(relation_category='supports'); assert out['false_pattern_suppressed'] and out['status']=='insufficient_evidence'; assert out['operator_review_proposal'] is None
print('v1132.7 3/3')
