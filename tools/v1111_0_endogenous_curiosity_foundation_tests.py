from pathlib import Path
import tempfile,sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'conscious_agent')]
from conscious_agent.endogenous_curiosity import EndogenousCuriosityStore
def req(x,m='failed'):
 if not x:raise AssertionError(m)
def main():
 root=Path(tempfile.mkdtemp())/'cognition';s=EndogenousCuriosityStore(root)
 a=s.register_candidate('e1',origin_kind='knowledge_gap',subject_summary='Why did confidence change?',evidence_refs=['knowledge-1'],uncertainty=.8,novelty=.7,answerability=.6,relevance=.9)
 b=s.register_candidate('e1',origin_kind='knowledge_gap',subject_summary='Why did confidence change?',evidence_refs=['knowledge-1'])
 c=s.register_candidate('e2',origin_kind='knowledge_gap',subject_summary='Why did confidence change?',evidence_refs=['knowledge-2'])
 req(a['result']['status']=='candidate_registered');req(b['status']=='duplicate_event_ignored');req(c['result']['status']=='duplicate_candidate_ignored')
 row=s.snapshot()['candidates'][0];req(row['provider_bound'] is False and row['authority_granted'] is False);req(not row['inquiry_id'] and not row['proposal_id'] and not row['authorization_id'] and not row['action_id'])
 try:s.register_candidate('bad',origin_kind='knowledge_gap',subject_summary='retroactive',evidence_refs=['turn'],origin='generated_dialogue')
 except ValueError:pass
 else:raise AssertionError('post-hoc dialogue accepted')
 summary=s.inspection_summary();req(summary['private_content_exposed'] is False);req(not any(summary['authority_boundary'].values()))
 print('{"passed":8,"total":8,"suite":"v1111.0"}')
if __name__=='__main__':main()
