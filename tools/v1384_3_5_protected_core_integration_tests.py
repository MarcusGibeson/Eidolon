import sys;from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'conscious_agent'),str(R/'tools')]
from protected_core import *;from ordinary_chat_development_campaign import process_ordinary_chat_development_turn;from v1384_test_support import *
N=0;r=classify_self_change_scope(changed_paths=['conscious_agent/release_authority.py']);s=r['scope']
q=review_protected_scope(scope=s,expected_scope_digest=s['scope_digest'],operator_reviewed=True,protected_review_acknowledged=True);req(q['ok'],'review');N+=1
req(q['review']['review_level']=='stronger_review','level');N+=1
req(not q['review']['execution_authorized'],'nonexec');N+=1
chat=process_ordinary_chat_development_turn('show protected core',project_state={'protected_scope':s});req(chat.get('active') and chat.get('ok'),'chat');N+=1
req(chat['protected_core']['source_architecture_only'] and not chat['release_authorized'],'visible');N+=1
print({'ok':N==5,'passed':N,'total':5,'suite':'v1384-integration'})
