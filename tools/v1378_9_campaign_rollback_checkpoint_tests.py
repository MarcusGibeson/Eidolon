import sys,tempfile;from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'conscious_agent'),str(R/'tools')]
from campaign_rollback import *
from v1378_test_support import *
P=0
with tempfile.TemporaryDirectory() as td,tempfile.TemporaryDirectory() as rr:
 w=Path(td);(w/'a').write_bytes(b'after')
 r=record_campaign_mutation_transaction(campaign_record_digest=C,transaction_id='checkpoint',workspace_root=w,operations=[{'relative_path':'a','kind':'modified','before_bytes':b'before','after_digest':B(b'after')}],recording_authorized=True,runtime_root=rr);x=r['transaction'];req(r['ok'],'record');P+=1
 p=prepare_campaign_rollback(campaign_record_digest=C,transaction_id='checkpoint',expected_transaction_digest=x['transaction_digest'],workspace_root=w,runtime_root=rr);req(p['rollback_plan']['rollback_ready'],'plan');P+=1
 e=execute_campaign_rollback(campaign_record_digest=C,transaction_id='checkpoint',expected_transaction_digest=x['transaction_digest'],expected_rollback_plan_digest=p['rollback_plan']['rollback_plan_digest'],authorization_phrase=p['authorization_phrase'],workspace_root=w,runtime_root=rr);req(e['ok'] and (w/'a').read_bytes()==b'before','rollback');P+=1
 req(e['rollback_receipt']['unrelated_paths_touched'] is False and e['rollback_receipt']['content_free'],'scope');P+=1
 req(not e['release_authorized'] and not e['independent_authority_granted'] and not e['source_mutation_authorized'],'authority');P+=1
print({'ok':P==5,'passed':P,'total':5,'suite':'v1378-checkpoint'})
