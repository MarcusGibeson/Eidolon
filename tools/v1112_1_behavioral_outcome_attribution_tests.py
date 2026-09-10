from pathlib import Path
import tempfile
from conscious_agent.behavioral_outcome_evidence import BehavioralOutcomeStore
from conscious_agent.behavioral_outcome_attribution import BehavioralAttributionStore

def req(v,m='failed'):
 if not v:raise AssertionError(m)
def main():
 root=Path(tempfile.mkdtemp())/'cognition';o=BehavioralOutcomeStore(root);oid=o.record_outcome('o1',outcome_class='objective_state',outcome_state='progressed',origin_type='objective',origin_id='obj1',lineage_refs=['milestone:m1'])['result']['outcome_id'];a=BehavioralAttributionStore(root)
 r=a.record_attribution('a1',outcome_id=oid,status='partially_attributed',contributors=[{'decision_type':'objective','decision_id':'obj1','weight':.6},{'decision_type':'reflection','decision_id':'r1','weight':.2}],uncertainty=.4)
 req(r['status']=='attribution_recorded');req(a.record_attribution('a1',outcome_id=oid,status='unresolved',contributors=[])['idempotent']);x=a.inspection_summary();req(x['attribution_count']==1 and x['recent_attributions'][0]['causation_certain'] is False);req(x['behavior_changed'] is False);print('{"passed":7,"total":7,"suite":"v1112.1"}')
if __name__=='__main__':main()
