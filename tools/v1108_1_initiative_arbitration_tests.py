from pathlib import Path
import tempfile
from conscious_agent.initiative_arbitration import InitiativeArbitrator
from conscious_agent.json_storage import write_json_atomic

def run():
 root=Path(tempfile.mkdtemp())/'cognition';a=InitiativeArbitrator(root);p=a.initiative._load();p['candidates']=[{'candidate_id':'c1','intention_id':'i1','subject_digest':'d','active_influence':True,'eligible':True,'resource_cost':.1,'salience':.9,'urgency':.8,'uncertainty':.5,'continuity_value':.8,'selection_count':0,'created_at':'2026'}];write_json_atomic(a.initiative.path,p,expected_type=dict,sort_keys=True)
 r=a.select('e1');d=a.select('e1');s=a._load();s['controls']['quiet']=True;write_json_atomic(a.path,s,expected_type=dict,sort_keys=True);q=a.select('e2');tests=[r['status']=='initiative_selected',d['status']=='duplicate_selection_ignored',q['status']=='deliberate_silence',r['receipt']['message_id']=='',not r['receipt']['provider_contacted']]
 print({'suite':'v1108.1','passed':sum(tests),'total':len(tests)});return all(tests)
if __name__=='__main__':raise SystemExit(0 if run() else 1)
