import sys,tempfile,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'conscious_agent'),str(ROOT/'tools')]
from campaign_records import *
from v1371_test_support import *
P=0
b=dict(BASE);b['standing_session_active']=False;req(not build_campaign_record(**b)['ok'],'grant');P+=1
b=dict(BASE);b['completed_steps']=6;req(not build_campaign_record(**b)['ok'],'progress');P+=1
b=dict(BASE);b['source_manifest_digest']='bad';req(not build_campaign_record(**b)['ok'],'lineage');P+=1
with tempfile.TemporaryDirectory() as td:
 v=build_campaign_record(**BASE)['campaign_record'];req(persist_campaign_record(runtime_root=td,record=v)['ok'],'store');P+=1;req(persist_campaign_record(runtime_root=td,record=v)['status']=='campaign_record_already_stored','idempotent');P+=1
 newer=dict(BASE);newer.update(generation=2,prior_record_digest=v['record_digest'],completed_steps=2,current_step_id='step-3',recovery_state='checkpointed');n=build_campaign_record(**newer)['campaign_record'];req(persist_campaign_record(runtime_root=td,record=n)['ok'],'generation');P+=1
 stale=dict(newer);stale['prior_record_digest']='b'*64;sv=build_campaign_record(**stale)['campaign_record'];req(not persist_campaign_record(runtime_root=td,record=sv)['ok'],'stale');P+=1
 path=Path(td)/'campaign_records/campaign-1/record.json';raw=json.loads(path.read_text());raw['state']='completed';path.write_text(json.dumps(raw));req(not load_campaign_record(runtime_root=td,campaign_id='campaign-1',expected_record_digest=n['record_digest'])['ok'],'tamper');P+=1
print({'ok':P==8,'passed':P,'total':8,'suite':'v1371-reliability'})
