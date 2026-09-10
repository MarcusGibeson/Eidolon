import sys,tempfile;from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'conscious_agent'),str(R/'tools')]
from campaign_rollback import *
from v1378_test_support import *
P=0
with tempfile.TemporaryDirectory() as td,tempfile.TemporaryDirectory() as rr:
 w=Path(td);(w/'a').write_bytes(b'after')
 base=[{'relative_path':'a','kind':'modified','before_bytes':b'before','after_digest':B(b'after')}]
 req(not record_campaign_mutation_transaction(campaign_record_digest=C,transaction_id='x',workspace_root=w,operations=base,recording_authorized=False,runtime_root=rr)['ok'],'record auth');P+=1
 req(not record_campaign_mutation_transaction(campaign_record_digest=C,transaction_id='x',workspace_root=w,operations=[{'relative_path':'../x','kind':'created','after_digest':B(b'x')}],recording_authorized=True,runtime_root=rr)['ok'],'path escape');P+=1
 req(not record_campaign_mutation_transaction(campaign_record_digest=C,transaction_id='x',workspace_root=w,operations=[{'relative_path':'a','kind':'modified','after_digest':B(b'after')}],recording_authorized=True,runtime_root=rr)['ok'],'before');P+=1
 r=record_campaign_mutation_transaction(campaign_record_digest=C,transaction_id='tx',workspace_root=w,operations=base,recording_authorized=True,runtime_root=rr);x=r['transaction'];w.joinpath('a').write_bytes(b'operator edit')
 p=prepare_campaign_rollback(campaign_record_digest=C,transaction_id='tx',expected_transaction_digest=x['transaction_digest'],workspace_root=w,runtime_root=rr);req(p['ok'] and not p['rollback_plan']['rollback_ready'] and p['rollback_plan']['conflict_count']==1,'operator edit');P+=1
 w.joinpath('a').write_bytes(b'after');p=prepare_campaign_rollback(campaign_record_digest=C,transaction_id='tx',expected_transaction_digest=x['transaction_digest'],workspace_root=w,runtime_root=rr)
 bad=execute_campaign_rollback(campaign_record_digest=C,transaction_id='tx',expected_transaction_digest=x['transaction_digest'],expected_rollback_plan_digest=p['rollback_plan']['rollback_plan_digest'],authorization_phrase='wrong',workspace_root=w,runtime_root=rr);req(not bad['ok'],'exact auth');P+=1
 req(not prepare_campaign_rollback(campaign_record_digest=C,transaction_id='tx',expected_transaction_digest='a'*64,workspace_root=w,runtime_root=rr)['ok'],'stale tx');P+=1
 before=Path(rr)/'campaign_rollbacks'/C/'tx'/'before'/f"{D('a')}.bin";before.write_bytes(b'tamper');bad=execute_campaign_rollback(campaign_record_digest=C,transaction_id='tx',expected_transaction_digest=x['transaction_digest'],expected_rollback_plan_digest=p['rollback_plan']['rollback_plan_digest'],authorization_phrase=p['authorization_phrase'],workspace_root=w,runtime_root=rr);req(not bad['ok'],'before tamper');P+=1
print({'ok':P==7,'passed':P,'total':7,'suite':'v1378-reliability'})
