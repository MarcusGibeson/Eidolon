import sys,tempfile;from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'conscious_agent'),str(R/'tools')]
from campaign_rollback import *
from ordinary_chat_development_campaign import process_ordinary_chat_development_turn
from v1378_test_support import *
P=0
with tempfile.TemporaryDirectory() as td,tempfile.TemporaryDirectory() as rr:
 w=Path(td);(w/'a.txt').write_bytes(b'after');(w/'new.txt').write_bytes(b'new');(w/'unrelated.txt').write_bytes(b'user')
 r=record_campaign_mutation_transaction(campaign_record_digest=C,transaction_id='tx2',workspace_root=w,operations=[{'relative_path':'a.txt','kind':'modified','before_bytes':b'before','after_digest':B(b'after')},{'relative_path':'new.txt','kind':'created','after_digest':B(b'new')}],recording_authorized=True,runtime_root=rr);x=r['transaction'];P+=int(r['ok'])
 p=prepare_campaign_rollback(campaign_record_digest=C,transaction_id='tx2',expected_transaction_digest=x['transaction_digest'],workspace_root=w,runtime_root=rr);req(p['rollback_plan']['rollback_ready'],'ready');P+=1
 e=execute_campaign_rollback(campaign_record_digest=C,transaction_id='tx2',expected_transaction_digest=x['transaction_digest'],expected_rollback_plan_digest=p['rollback_plan']['rollback_plan_digest'],authorization_phrase=p['authorization_phrase'],workspace_root=w,runtime_root=rr);req(e['ok'] and e['rollback_receipt']['restored_count']==2,'execute');P+=1
 req((w/'a.txt').read_bytes()==b'before' and not (w/'new.txt').exists() and (w/'unrelated.txt').read_bytes()==b'user','scope');P+=1
 c=process_ordinary_chat_development_turn('show campaign rollback',project_state={'campaign_rollback':p['rollback_plan']});req(c.get('active') and c.get('ok') and not c['action_executed'],'chat');P+=1
print({'ok':P==5,'passed':P,'total':5,'suite':'v1378-integration'})
