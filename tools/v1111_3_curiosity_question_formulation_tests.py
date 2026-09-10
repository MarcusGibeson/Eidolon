from pathlib import Path
import tempfile,sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'conscious_agent')]
from conscious_agent.endogenous_curiosity import EndogenousCuriosityStore
from conscious_agent.curiosity_arbitration import CuriosityArbitrator
from conscious_agent.curiosity_question_formulation import CuriosityQuestionStore
def req(x,m='failed'):
 if not x:raise AssertionError(m)
def main():
 root=Path(tempfile.mkdtemp())/'cognition';c=EndogenousCuriosityStore(root);c.register_candidate('e1',origin_kind='knowledge_gap',subject_summary='Why does state drift?',evidence_refs=['r1'],uncertainty=.9,novelty=.8,answerability=.8,relevance=.9);a=CuriosityArbitrator(root);sel=a.select('s1')['result'];q=CuriosityQuestionStore(root);r=q.formulate('q1',selection_receipt_id=sel['receipt_id'],question_text='Which structural change caused the state drift?',specificity=.9,answerability=.8,information_value=.9);req(r['result']['question_id']);req(q.formulate('q1',selection_receipt_id=sel['receipt_id'],question_text='ignored?')['idempotent']);bad=q.formulate('q2',selection_receipt_id='missing',question_text='What happened?');req(bad['result']['reason']=='invalid_selection_receipt');long=q.formulate('q3',selection_receipt_id=sel['receipt_id'],question_text=' '.join(['word']*30)+'?');req(long['result']['reason']=='bounded_formulation_failed');snap=q.inspection_summary();req(snap['question_count']==1 and not any(snap['authority_boundary'].values()));req(snap['recent_questions'][0]['inquiry_id']=='' and snap['recent_questions'][0]['user_prompt_id']=='');print('{"passed":8,"total":8,"suite":"v1111.3"}')
if __name__=='__main__':main()
