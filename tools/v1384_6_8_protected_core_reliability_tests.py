import sys;from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'conscious_agent'),str(R/'tools')]
from protected_core import *;from v1384_test_support import *
N=0
req(not classify_self_change_scope(changed_paths=[])['ok'],'empty');N+=1
req(not classify_self_change_scope(changed_paths=['../escape.py'])['ok'],'traversal');N+=1
req(not classify_self_change_scope(changed_paths=['x.py'],expected_protected_core_digest='0'*64)['ok'],'stale map');N+=1
r=classify_self_change_scope(changed_paths=['conscious_agent/release_installation.py']);s=r['scope'];req(s['protected_core_touched'],'release');N+=1
req(not review_protected_scope(scope=s,expected_scope_digest=s['scope_digest'],operator_reviewed=True)['ok'],'strong ack');N+=1
req(not review_protected_scope(scope=s,expected_scope_digest=s['scope_digest'],operator_reviewed=False,protected_review_acknowledged=True)['ok'],'operator');N+=1
t=dict(s);t['protected_path_count']=0;req(not review_protected_scope(scope=t,expected_scope_digest=s['scope_digest'],operator_reviewed=True,protected_review_acknowledged=True)['ok'],'tamper');N+=1
print({'ok':N==7,'passed':N,'total':7,'suite':'v1384-reliability'})
