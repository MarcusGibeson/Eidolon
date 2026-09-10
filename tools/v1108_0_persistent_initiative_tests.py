from pathlib import Path
import tempfile
from conscious_agent.persistent_initiative import PersistentInitiativeStore
from conscious_agent.bounded_intention_formation import BoundedIntentionStore

def run():
 root=Path(tempfile.mkdtemp())/'cognition';i=BoundedIntentionStore(root);s=i._load();s['intentions']=[{'intention_id':'i1','agenda_id':'a1','subject_digest':'d1','active':True}];from conscious_agent.json_storage import write_json_atomic;write_json_atomic(i.path,s,expected_type=dict,sort_keys=True)
 p=PersistentInitiativeStore(root);a=p.register('e1',intention_id='i1');b=p.register('e1',intention_id='i1');x=p.inspection_summary();tests=[a['status']=='initiative_candidate_registered',b['status']=='duplicate_event_ignored',x['candidate_count']==1,not any(x['authority_boundary'].values()),x['message_sent'] is False]
 print({'suite':'v1108.0','passed':sum(tests),'total':len(tests)});return all(tests)
if __name__=='__main__':raise SystemExit(0 if run() else 1)
