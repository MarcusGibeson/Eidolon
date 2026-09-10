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
from conscious_agent.cognitive_recovery_arbitration import CognitiveRecoveryArbitrator
with tempfile.TemporaryDirectory() as td:
 root=Path(td);s=CognitiveHomeostasisSignalStore(root);sid=s.register('s1',origin_type='load_checkpoint',origin_id='l1',load_pressure=.9,fragmentation=.2,recovery_margin=.1)['result']['signal_id'];a=CognitiveRecoveryArbitrator(root);r=a.review('r1',signal_ids=[sid]);check('reviewed',r['status']=='review_completed');check('recovery',r['result']['outcome']=='recovery_window_recommended');check('idempotent',a.review('r1',signal_ids=[sid])['idempotent']);check('missing_unknown',a.review('r2',signal_ids=['missing'])['result']['outcome']=='insufficient_evidence');check('rest',a.review('r3',signal_ids=[sid],force_rest=True)['result']['outcome']=='deliberate_rest_recommended');check('nonexecuting',not any(r['result'][k] for k in ('schedule_changed','work_paused','work_resumed','attention_id','intention_id','authorization_id','action_id')));check('authority',all(v is False for v in a.snapshot()['authority_boundary'].values()));check('content_free',all(x.get('content_free') for x in a.snapshot()['reviews']))
print(json.dumps({'passed':passed,'total':8,'suite':'v1116.1'}))
