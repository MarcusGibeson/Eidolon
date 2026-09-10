import tempfile,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'conscious_agent'),str(ROOT/'tools')]
from security_verification import *
from v1358_test_support import *
P=0
cases=[('secret.py','API_KEY="1234567890abcdef"','secret_material'),('shell.py','import subprocess\nsubprocess.run("x", shell=True)','unsafe_shell_construction'),('eval.py','x=eval("1+1")','unsafe_dynamic_execution'),('zip.py','import zipfile\na=zipfile.ZipFile("x")\na.extractall("out")','archive_extraction_requires_containment'),('log.py','def f(token):\n print(token)','possible_secret_logging')]
for name,text,cat in cases:
 with tempfile.TemporaryDirectory() as td:
  root=Path(td)/'p';root.mkdir();(root/name).write_text(text);r=scan_security(project_root=root,source_manifest_digest=SOURCE,file_paths=[name]);req(not r['ok'] and any(x['category']==cat for x in r['security_verification']['findings']),cat);P+=1
with tempfile.TemporaryDirectory() as td:
 root=Path(td)/'p';clean(root);r=scan_security(project_root=root,source_manifest_digest=SOURCE,file_paths=['app.py'],dependency_evidence=deps(False));req(not r['ok'] and any(x['category']=='dependency_risk' for x in r['security_verification']['findings']),'dependency');P+=1
with tempfile.TemporaryDirectory() as td:
 root=Path(td)/'p';clean(root);req(not scan_security(project_root=root,source_manifest_digest=SOURCE,file_paths=['../x'])['ok'],'path');P+=1
req(not scan_security(project_root='.',source_manifest_digest='bad',file_paths=[])['ok'],'lineage');P+=1
req(all('secret' not in str(x.get('evidence_digest','')) for x in r['security_verification']['findings']),'redacted');P+=1
print({'ok':P==9,'passed':P,'total':9,'suite':'v1358.6-8-security-reliability'})
