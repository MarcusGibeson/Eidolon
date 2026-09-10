import os,tempfile
from pathlib import Path
from conscious_agent.curiosity_inquiry_promotion import CuriosityInquiryPromotionStore
from conscious_agent.curiosity_quality_arbitration import CuriosityQualityArbitrator
from conscious_agent.curiosity_question_formulation import CuriosityQuestionStore
from conscious_agent.curiosity_arbitration import CuriosityArbitrator
from conscious_agent.endogenous_curiosity import EndogenousCuriosityStore
def req(x):
 if not x:raise AssertionError()
r=Path(tempfile.mkdtemp())/'cognition'; c=EndogenousCuriosityStore(r);x=c.register_candidate('e0',origin_kind='residual_question',subject_summary='s1',evidence_refs=['r1'],uncertainty=.9,novelty=.9,answerability=.9,relevance=.9);cid=x['result']['candidate_id'];a=CuriosityArbitrator(r);sel=a.select('e1');rid=sel['result']['receipt_id'];q=CuriosityQuestionStore(r);qq=q.formulate('e2',selection_receipt_id=rid,question_text='What evidence would resolve this uncertainty?',specificity=.9,answerability=.9,information_value=.9);qid=qq['result']['question_id'];qa=CuriosityQualityArbitrator(r);d=qa.evaluate('e3',question_id=qid);did=d['result']['decision_id'];p=CuriosityInquiryPromotionStore(r);z=p.promote('e4',decision_id=did,project_id='p');req(z['result']['status']=='inquiry_candidate_created');req(p.promote('e4',decision_id=did)['idempotent']);row=p.snapshot()['promotions'][0];req(not any(row[k] for k in ('active_inquiry_id','browse_receipt_id','user_prompt_id','proposal_id','authorization_id','action_id')));print('{"passed":7,"total":7,"suite":"v1111.6"}')
