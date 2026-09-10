import tempfile,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'conscious_agent'),str(ROOT/'tools')]
from security_verification import *
from ordinary_chat_development_campaign import process_ordinary_chat_development_turn
from v1358_test_support import *
P=0
with tempfile.TemporaryDirectory() as td:
 root=Path(td)/'p';clean(root);r=scan_security(project_root=root,source_manifest_digest=SOURCE,file_paths=['app.py'],dependency_evidence=deps());v=r['security_verification'];req(r['ok'],'scan');P+=1;c=process_ordinary_chat_development_turn('show security tests',project_state={'security_verification':v});req(c['active'] and c['ok'],'chat');P+=1;req(not c['action_executed'],'readonly');P+=1;req(v['source_manifest_digest']==SOURCE,'lineage');P+=1;req(v['content_free'],'public');P+=1
print({'ok':P==5,'passed':P,'total':5,'suite':'v1358.3-5-security-integration'})
