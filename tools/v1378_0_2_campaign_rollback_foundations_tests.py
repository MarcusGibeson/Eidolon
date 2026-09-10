import sys,tempfile;from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'conscious_agent'),str(R/'tools')]
from campaign_rollback import *
from v1378_test_support import *
P=0
with tempfile.TemporaryDirectory() as td,tempfile.TemporaryDirectory() as rr:
 w=Path(td);(w/'a.txt').write_bytes(b'after');(w/'new.txt').write_bytes(b'new')
 r=record_campaign_mutation_transaction(campaign_record_digest=C,transaction_id='tx1',workspace_root=w,operations=[{'relative_path':'a.txt','kind':'modified','before_bytes':b'before','after_digest':B(b'after')},{'relative_path':'new.txt','kind':'created','after_digest':B(b'new')}],recording_authorized=True,runtime_root=rr);req(r['ok'],'record');P+=1
 x=r['transaction'];req(x['operation_count']==2 and len(x['owned_path_digests'])==2,'count');P+=1
 req(x['content_free'] and not x['raw_paths_exposed'] and not x['before_images_exposed'],'privacy');P+=1
 p=prepare_campaign_rollback(campaign_record_digest=C,transaction_id='tx1',expected_transaction_digest=x['transaction_digest'],workspace_root=w,runtime_root=rr);req(p['ok'] and p['rollback_plan']['rollback_ready'],'prepare');P+=1
 req(not p['project_mutation_authorized'] and not p['source_mutation_authorized'],'authority');P+=1
print({'ok':P==5,'passed':P,'total':5,'suite':'v1378-foundations'})
