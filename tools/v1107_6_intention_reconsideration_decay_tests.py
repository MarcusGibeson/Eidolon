from pathlib import Path
import json,tempfile
from conscious_agent.bounded_intention_formation import BoundedIntentionStore
from conscious_agent.intention_reconsideration_decay import IntentionLifecycle

def req(x,m):
 if not x: raise AssertionError(m)
def seed(root, iid='i1'):
 s=BoundedIntentionStore(root); st=s._load(); st['intentions']=[{'intention_id':iid,'intention_key':iid,'intake_id':'x','agenda_id':'a','subject_digest':'d','kind':'reflect','priority':.5,'confidence':.5,'created_at':'2026-01-01T00:00:00Z','updated_at':'2026-01-01T00:00:00Z','expires_at':'','active':True,'lifecycle':'active','proposal_id':'','authorized_action_id':'','completed_action_id':''}]; from conscious_agent.json_storage import write_json_atomic; write_json_atomic(s.path,st,expected_type=dict,sort_keys=True); return s

def tests():
 rows=[]
 def run(name,fn):
  try: fn(); rows.append({'name':name,'status':'pass'})
  except Exception as e: rows.append({'name':name,'status':'fail','error':repr(e)})
 def transitions():
  r=Path(tempfile.mkdtemp())/'cognition'; seed(r); l=IntentionLifecycle(r,clock=lambda:'2026-02-01T00:00:00Z'); req(l.reconsider('e1',intention_id='i1',outcome='suspend')['result']['lifecycle']=='suspended','suspend'); req(l.reconsider('e2',intention_id='i1',outcome='resume')['result']['lifecycle']=='active','resume'); req(l.reconsider('e3',intention_id='i1',outcome='retire')['result']['lifecycle']=='retired','retire')
 def duplicate():
  r=Path(tempfile.mkdtemp())/'cognition'; seed(r); l=IntentionLifecycle(r); l.reconsider('same',intention_id='i1',outcome='suspend'); req(l.reconsider('same',intention_id='i1',outcome='resume')['idempotent'],'dup')
 def expiry():
  r=Path(tempfile.mkdtemp())/'cognition'; s=seed(r); st=s._load(); st['intentions'][0]['expires_at']='2026-01-02T00:00:00Z'; from conscious_agent.json_storage import write_json_atomic; write_json_atomic(s.path,st,expected_type=dict,sort_keys=True); q=IntentionLifecycle(r,clock=lambda:'2026-01-03T00:00:00Z').apply_due_expiry('sweep'); req(q['result']['expired_count']==1,q)
 def privacy():
  r=Path(tempfile.mkdtemp())/'cognition'; seed(r); q=IntentionLifecycle(r).inspection_summary(); b=json.dumps(q).lower(); req(q['provider_contacted'] is False and 'private subject' not in b,q)
 for n,f in [('transitions',transitions),('duplicate',duplicate),('expiry',expiry),('privacy',privacy)]:run(n,f)
 return rows
if __name__=='__main__':
 rows=tests(); out={'suite':'v1107.6-intention-reconsideration-decay','passed':sum(x['status']=='pass' for x in rows),'total':len(rows),'tests':rows}; print(json.dumps(out,indent=2)); raise SystemExit(0 if out['passed']==out['total'] else 1)
