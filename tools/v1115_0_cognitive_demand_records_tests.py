from pathlib import Path
import json,sys,tempfile
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
passed=0
def check(name,cond):
 global passed
 if not cond: raise AssertionError(name)
 passed+=1
from conscious_agent.cognitive_demand_records import CognitiveDemandStore
with tempfile.TemporaryDirectory() as td:
 s=CognitiveDemandStore(Path(td)); r=s.register('e1',origin_type='objective',origin_id='o1',urgency=.7,importance=.8,cognitive_cost=.3,deadline_pressure=.4,overlap_key='x'); check('registered',r['status']=='demand_registered');check('idempotent',s.register('e1',origin_type='objective',origin_id='o1')['idempotent']);check('semantic_duplicate',s.register('e2',origin_type='objective',origin_id='o1',overlap_key='x')['status']=='duplicate_demand_ignored');snap=s.snapshot();row=snap['records'][0];check('bounded_scores',all(0<=row[k]<=1 for k in ('urgency','importance','cognitive_cost','freshness','deadline_pressure','interruptibility','sensitivity')));check('lineage',row['origin_type']=='objective' and row['origin_id']=='o1');check('content_free',not any(k in row for k in ('raw_text','prompt','message','reasoning')));check('authority',all(v is False for v in snap['authority_boundary'].values()));check('separation',all(v is False for v in snap['state_separation'].values()))
print(json.dumps({'passed':passed,'total':8,'suite':'v1115.0'}))
