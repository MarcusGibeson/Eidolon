import sys,tempfile;from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'conscious_agent'),str(R/'tools')]
from automatic_self_rollback import *;from ordinary_chat_development_campaign import process_ordinary_chat_development_turn;from v1388_test_support import *
N=0
with tempfile.TemporaryDirectory() as td:
 r=Path(td);old,cand=trees(r,1);c=canary();q=execute_self_update_with_auto_rollback(installed_root=old,candidate_work_root=cand,runtime_root=r/'rt',transaction_id=TX,canary_self_update=c,expected_canary_digest=c['canary_digest'],health_scenarios=['health/post.py'],operator_authorized=True);req(not q['ok'],'health fail');N+=1
 v=q['self_update_transaction'];req(v['rollback_performed'] and v['rollback_verified'],'rollback');N+=1
 req('old' in (old/'app.py').read_text(),'restored');N+=1
 chat=process_ordinary_chat_development_turn('show automatic self rollback',project_state={'self_update_transaction':v});req(chat.get('active') and chat.get('ok'),'chat');N+=1
 req(v['diagnostic_evidence_retained'] and len(v['failure_digest'])==64,'diagnostic');N+=1
print({'ok':N==5,'passed':N,'total':5,'suite':'v1388-integration'})
