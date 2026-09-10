import tempfile,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'conscious_agent'),str(ROOT/'tools')]
from security_verification import *
from v1358_test_support import *
P=0
with tempfile.TemporaryDirectory() as td:
 r0=Path(td)/'p';clean(r0);r=scan_security(project_root=r0,source_manifest_digest=SOURCE,file_paths=['app.py','config.json'],dependency_evidence=deps());req(r['ok'],'clean');P+=1;v=r['security_verification'];req(v['finding_count']==0,'findings');P+=1;req(v['read_only'] and not v['raw_source_persisted'],'readonly');P+=1;req(not v['secret_values_exposed'],'redact');P+=1;req(not r['network_authorized'] and not r['dependency_install_authorized'],'authority');P+=1
print({'ok':P==5,'passed':P,'total':5,'suite':'v1358.0-2-security-foundations'})
