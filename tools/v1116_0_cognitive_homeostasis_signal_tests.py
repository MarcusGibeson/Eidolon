from pathlib import Path
import json,sys,tempfile
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
passed=0
def check(n,c):
 global passed
 if not c:raise AssertionError(n)
 passed+=1
from conscious_agent.cognitive_homeostasis_signals import CognitiveHomeostasisSignalStore
with tempfile.TemporaryDirectory() as td:
 s=CognitiveHomeostasisSignalStore(Path(td));r=s.register('e1',origin_type='load_checkpoint',origin_id='load-1',load_pressure=.8,fragmentation=.4,recovery_margin=.2,structural_digest='abc');check('registered',r['status']=='signal_registered');check('idempotent',s.register('e1',origin_type='load_checkpoint',origin_id='load-1',load_pressure=.8,fragmentation=.4,recovery_margin=.2)['idempotent']);check('semantic_duplicate',s.register('e2',origin_type='load_checkpoint',origin_id='load-1',load_pressure=.8,fragmentation=.4,recovery_margin=.2,structural_digest='abc')['status']=='duplicate_signal_ignored');row=s.snapshot()['signals'][0];check('bounded',all(0<=row[k]<=1 for k in ('load_pressure','fragmentation','recovery_margin','interruption_density','stale_work_ratio','uncertainty')));check('lineage',row['origin_type']=='load_checkpoint' and row['origin_id']=='load-1');check('content_free',not any(k in row for k in ('raw_text','prompt','message','reasoning')));check('authority',all(v is False for v in s.snapshot()['authority_boundary'].values()));check('inactive',all(not row[k] for k in ('schedule_id','attention_id','intention_id','decision_id','proposal_id','approval_id','authorization_id','action_id')))
print(json.dumps({'passed':passed,'total':8,'suite':'v1116.0'}))
