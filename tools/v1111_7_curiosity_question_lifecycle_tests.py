import tempfile
from pathlib import Path
from conscious_agent.curiosity_question_lifecycle import CuriosityQuestionLifecycleStore
from conscious_agent.curiosity_inquiry_promotion import CuriosityInquiryPromotionStore
from conscious_agent.curiosity_quality_arbitration import CuriosityQualityArbitrator
from conscious_agent.curiosity_question_formulation import CuriosityQuestionStore
from conscious_agent.curiosity_arbitration import CuriosityArbitrator
from conscious_agent.endogenous_curiosity import EndogenousCuriosityStore
def req(x):
 if not x:raise AssertionError()
r=Path(tempfile.mkdtemp())/'cognition';cid=EndogenousCuriosityStore(r).register_candidate('a',origin_kind='residual_question',subject_summary='s',evidence_refs=['r'],uncertainty=.9,novelty=.9,answerability=.9,relevance=.9)['result']['candidate_id'];rid=CuriosityArbitrator(r).select('b')['result']['receipt_id'];qid=CuriosityQuestionStore(r).formulate('c',selection_receipt_id=rid,question_text='What evidence would resolve this uncertainty?',specificity=.9,answerability=.9,information_value=.9)['result']['question_id'];did=CuriosityQualityArbitrator(r).evaluate('d',question_id=qid)['result']['decision_id'];iid=CuriosityInquiryPromotionStore(r).promote('e',decision_id=did)['result']['inquiry_candidate_id'];s=CuriosityQuestionLifecycleStore(r);req(s.decide('f',inquiry_candidate_id=iid,outcome='reformulate',replacement_digest='a'*64)['result']['outcome']=='reformulate');req(s.decide('g',inquiry_candidate_id=iid,outcome='retire_obsolete')['result']['active_influence'] is False);req(s.decide('g',inquiry_candidate_id=iid,outcome='retain')['idempotent']);req(s.inspection_summary()['authority_boundary']['can_browse'] is False);print('{"passed":7,"total":7,"suite":"v1111.7"}')
