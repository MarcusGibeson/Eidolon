from __future__ import annotations
import json,sys,tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.dont_write_bytecode=True
from revisable_belief_world_model import assess_belief_evidence,integrate_reviewed_belief
import revisable_belief_world_model as belief_world_model
from belief_revision import BeliefRevisionStore
from metadata_mutation_coordination import MetadataMutationBusy
checks=[]
def req(v,n): checks.append(n); assert v,n
now=datetime.now(timezone.utc)
rows=[
 {'id':'u1','provenance_class':'user','stance':'supports','confidence':.9,'created_at':now.isoformat()},
 {'id':'a1','provenance_class':'assistant','stance':'supports','confidence':1,'created_at':now.isoformat()},
 {'id':'u2','provenance_class':'user','stance':'contradicts','confidence':.8,'created_at':now.isoformat()},
 {'id':'r1','provenance_class':'action_receipt','stance':'supports','confidence':1,'created_at':now.isoformat()},
]
a=assess_belief_evidence('service is healthy',rows,now=now)
req(a['counted_evidence']==3,'assistant_not_counted')
req(a['assistant_authored_rejected_count']==1,'assistant_rejected_explicitly')
req(a['source_disagreement'] is True and a['state']=='contested','source_disagreement_contested')
req(a['raw_evidence_text_exposed'] is False,'content_free_public_assessment')
old=assess_belief_evidence('version is current',[{'id':'e','provenance_class':'external_source','stance':'supports','confidence':1,'created_at':(now-timedelta(days=800)).isoformat()}],now=now)
req(old['stale_evidence_count']==1,'stale_evidence_visible')
with tempfile.TemporaryDirectory(prefix='eidolon-v1875-') as td:
 rt=Path(td)/'runtime'
 first=integrate_reviewed_belief('evt-1',proposition='service is healthy',subject_key='service:health',evidence_rows=rows,runtime_root=rt)
 req(first['ok'] and first['second_belief_store_created'] is False,'existing_store_reused')
 req(first['action_authority_changed'] is False,'no_action_authority')
 snap=BeliefRevisionStore(rt).inspection_summary(item_limit=20)
 req(snap['active_belief_count']==1,'durable_belief_created')
 req(snap['contested_belief_count']==1,'contradiction_persists')
 replay=integrate_reviewed_belief('evt-1',proposition='service is healthy',subject_key='service:health',evidence_rows=rows,runtime_root=rt)
 req(replay['ok'],'idempotent_event_replay')
 empty=integrate_reviewed_belief('evt-2',proposition='claim',subject_key='x',evidence_rows=[{'id':'a','provenance_class':'assistant','stance':'supports'}],runtime_root=rt)
 req(empty['ok'] is False and empty['status']=='insufficient_attributable_evidence','assistant_only_cannot_create_belief')
 original_integrate=belief_world_model.BeliefRevisionStore.integrate_candidate
 try:
  def busy(*args,**kwargs): raise MetadataMutationBusy()
  belief_world_model.BeliefRevisionStore.integrate_candidate=busy
  contention=integrate_reviewed_belief('evt-busy',proposition='claim',subject_key='busy',evidence_rows=[{'id':'u','provenance_class':'user','stance':'supports'}],runtime_root=rt)
 finally:
  belief_world_model.BeliefRevisionStore.integrate_candidate=original_integrate
 req(contention['ok'] is False and contention['status']=='belief_store_busy_retry_safe' and contention['retryable'] is True,'lock_contention_returns_safe_retry')
print(json.dumps({'suite':'v1875.9-revisable-belief-world-model','ok':True,'passed':len(checks),'failed':0,'checks':checks},sort_keys=True))
