from pathlib import Path
import json,tempfile
from conscious_agent.bounded_intention_formation import BoundedIntentionStore
from conscious_agent.intention_conflict_resolution import IntentionConflictResolver
from conscious_agent.json_storage import write_json_atomic

def req(x,m):
 if not x: raise AssertionError(m)
def seed(root):
 s=BoundedIntentionStore(root); st=s._load(); base={'intention_key':'k','intake_id':'x','agenda_id':'a','subject_digest':'d','kind':'reflect','created_at':'2026-01-01T00:00:00Z','updated_at':'','expires_at':'','active':True,'lifecycle':'active','proposal_id':'','authorized_action_id':'','completed_action_id':''}; st['intentions']=[dict(base,intention_id='low',priority=.4,confidence=.9),dict(base,intention_id='high',priority=.8,confidence=.5)]; write_json_atomic(s.path,st,expected_type=dict,sort_keys=True)
def tests():
 rows=[]
 def run(n,f):
  try:f();rows.append({'name':n,'status':'pass'})
  except Exception as e:rows.append({'name':n,'status':'fail','error':repr(e)})
 def deterministic():
  r=Path(tempfile.mkdtemp())/'cognition';seed(r);q=IntentionConflictResolver(r).resolve('e',intention_ids=['low','high']);req(q['result']['winner_id']=='high',q);req(q['result']['proposal_created'] is False,q)
 def duplicate():
  r=Path(tempfile.mkdtemp())/'cognition';seed(r);x=IntentionConflictResolver(r);x.resolve('e',intention_ids=['low','high']);req(x.resolve('e',intention_ids=['low','high'])['idempotent'],'dup')
 def historical():
  r=Path(tempfile.mkdtemp())/'cognition';seed(r);x=IntentionConflictResolver(r);x.resolve('e',intention_ids=['low','high']);q=x.inspection_summary();req(q['replaced_intention_count']==1 and q['external_action_executed'] is False,q)
 for n,f in [('deterministic',deterministic),('duplicate',duplicate),('historical',historical)]:run(n,f)
 return rows
if __name__=='__main__':
 rows=tests();out={'suite':'v1107.7-intention-conflict-resolution','passed':sum(x['status']=='pass' for x in rows),'total':len(rows),'tests':rows};print(json.dumps(out,indent=2));raise SystemExit(0 if out['passed']==out['total'] else 1)
