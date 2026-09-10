import tempfile,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'conscious_agent'),str(ROOT/'tools')]
from security_verification import *
from v1358_test_support import *
P=0
with tempfile.TemporaryDirectory() as td:
 root=Path(td)/'p';clean(root);r=scan_security(project_root=root,source_manifest_digest=SOURCE,file_paths=['app.py','config.json'],dependency_evidence=deps());v=r['security_verification'];req(r['ok'],'checkpoint');P+=1;req(v['verification_passed'] and v['finding_count']==0,'clean');P+=1;req(v['scanned_file_count']==2 and v['dependency_evidence_count']==1,'coverage');P+=1;req(v['content_free'] and not v['secret_values_exposed'],'privacy');P+=1;req(not r['release_authorized'] and not r['source_mutation_authorized'],'authority');P+=1
print({'ok':P==5,'passed':P,'total':5,'suite':'v1358.9-security-checkpoint'})
