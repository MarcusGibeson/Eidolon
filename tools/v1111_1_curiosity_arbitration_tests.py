from pathlib import Path
import tempfile,sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'conscious_agent')]
from conscious_agent.endogenous_curiosity import EndogenousCuriosityStore
from conscious_agent.curiosity_arbitration import CuriosityArbitrator
def req(x,m='failed'):
 if not x:raise AssertionError(m)
def main():
 root=Path(tempfile.mkdtemp())/'cognition';s=EndogenousCuriosityStore(root);a=CuriosityArbitrator(root)
 s.register_candidate('c1',origin_kind='unresolved_inquiry',subject_summary='What evidence would resolve this?',evidence_refs=['inq-1'],uncertainty=.9,novelty=.8,answerability=.8,relevance=.9,resource_cost=.2)
 x=a.select('a1');y=a.select('a1');z=a.select('a2',quiet=True);w=a.select('a3',resource_available=0)
 req(x['result']['status']=='curiosity_selected');req(y['status']=='duplicate_event_ignored');req(z['result']['status']=='no_curiosity_selected' and z['result']['reason']=='control_boundary');req(w['result']['reason']=='resource_boundary')
 req(not x['result']['inquiry_id'] and x['result']['authority_granted'] is False);summary=a.inspection_summary();req(summary['selection_count']==1 and summary['no_selection_count']==2);req(not any(summary['authority_boundary'].values()))
 print('{"passed":7,"total":7,"suite":"v1111.1"}')
if __name__=='__main__':main()
