from pathlib import Path
import tempfile
from conscious_agent.behavioral_outcome_evidence import BehavioralOutcomeStore

def req(v,m='failed'):
 if not v: raise AssertionError(m)
def main():
 root=Path(tempfile.mkdtemp())/'cognition';s=BehavioralOutcomeStore(root)
 r=s.record_outcome('e1',outcome_class='initiative_response',outcome_state='acknowledged',origin_type='initiative',origin_id='i1',lineage_refs=['proposal:p1'],score=.7)
 req(r['status']=='outcome_recorded');req(s.record_outcome('e1',outcome_class='initiative_response',outcome_state='acknowledged',origin_type='initiative',origin_id='i1',lineage_refs=['proposal:p1'])['idempotent'])
 try:s.record_outcome('e2',outcome_class='initiative_response',outcome_state='success',origin_type='initiative',origin_id='i2',lineage_refs=['p2'],feedback_known=False);raise AssertionError('missing feedback accepted')
 except ValueError:pass
 oid=r['result']['outcome_id'];s.record_outcome('e3',outcome_class='initiative_response',outcome_state='corrected',origin_type='initiative',origin_id='i1',lineage_refs=['proposal:p1'],correction_of=oid)
 x=s.inspection_summary();req(x['outcome_count']==2 and x['corrected_count']==1);req(not x['raw_content_exposed'] and not x['authority_boundary']['can_adapt']);print('{"passed":8,"total":8,"suite":"v1112.0"}')
if __name__=='__main__':main()
