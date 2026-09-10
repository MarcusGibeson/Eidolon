from pathlib import Path
import tempfile,sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'conscious_agent')]
from conscious_agent.endogenous_curiosity import EndogenousCuriosityStore
from conscious_agent.curiosity_arbitration import CuriosityArbitrator
from conscious_agent.curiosity_question_formulation import CuriosityQuestionStore
from conscious_agent.curiosity_quality_arbitration import CuriosityQualityArbitrator
def req(x,m='failed'):
 if not x:raise AssertionError(m)
def setup(root,ev='e'):
 c=EndogenousCuriosityStore(root);c.register_candidate(ev,origin_kind='knowledge_gap',subject_summary='State drift cause',evidence_refs=['r'],uncertainty=.9,novelty=.8,answerability=.9,relevance=.9);sel=CuriosityArbitrator(root).select('s'+ev)['result'];q=CuriosityQuestionStore(root);return q.formulate('q'+ev,selection_receipt_id=sel['receipt_id'],question_text='Which structural change caused the state drift?',specificity=.9,answerability=.9,information_value=.9,sensitivity=.1,resource_cost=.1)['result']['question_id']
def main():
 root=Path(tempfile.mkdtemp())/'cognition';qid=setup(root);a=CuriosityQualityArbitrator(root);r=a.evaluate('d1',question_id=qid);req(r['result']['outcome']=='eligible_for_inquiry');req(r['result']['inquiry_id']=='' and not r['result']['authority_granted']);req(a.evaluate('d1',question_id=qid)['idempotent']);req(a.evaluate('d2',question_id=qid,quiet=True)['result']['outcome']=='deliberate_silence');req(a.evaluate('d3',question_id=qid,user_relevant=False)['result']['outcome']=='internal_only');req(a.evaluate('d4',question_id=qid,topic_allowed=False)['result']['outcome']=='defer');req(a.evaluate('d5',question_id='missing')['result']['outcome']=='abandon');req(not any(a.inspection_summary()['authority_boundary'].values()));print('{"passed":8,"total":8,"suite":"v1111.4"}')
if __name__=='__main__':main()
