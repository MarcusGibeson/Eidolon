from __future__ import annotations
import hashlib,shutil,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.path.insert(0,str(ROOT/'tools'))
from v1333_workspace_isolation_test_support import WS,active_grant,precondition,init_git
from v1338_service_orchestration_test_support import SERVER

HTML='''<!doctype html><html><body><div id="status">Old</div></body></html>\n'''
VERIFY='''from pathlib import Path\ntext=Path("index.html").read_text(encoding="utf-8")\nraise SystemExit(0 if ">New<" in text else 7)\n'''

def source_fixture(base:Path):
 src=base/'source';src.mkdir();(src/'app.py').write_text('print(\"seed\")\n',encoding='utf-8');(src/'index.html').write_text(HTML,encoding='utf-8');(src/'verify.py').write_text(VERIFY,encoding='utf-8');(src/'service_fixture.py').write_text(SERVER,encoding='utf-8');(src/'README.md').write_text('# v1340 fixture\n',encoding='utf-8');git=init_git(src);assert git
 # init_git stages only app.py/README, so rebuild this fixture repository coherently.
 subprocess.run([git,'add','-A'],cwd=src,check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
 subprocess.run([git,'commit','-m','multi tool fixture'],cwd=src,check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
 runtime=base/'runtime';grant=active_grant(commands=('git','git_worktree','shell','browser','service'))
 pres={k:precondition(runtime,k) for k in ('git','file_patch','shell','browser','service')}
 return src,runtime,grant,pres,git

def campaign_args(src:Path,runtime:Path,grant,pres,git,*,verify_ok=True,browser_ok=True):
 expected=hashlib.sha256((src/'index.html').read_bytes()).hexdigest()
 verify=[sys.executable,'verify.py'] if verify_ok else [sys.executable,'-c','raise SystemExit(9)']
 checks=[{'kind':'text_equals','selector':'#status','expected':'New'}] if browser_ok else [{'kind':'visible','selector':'#missing'}]
 service={'service_code':'web','argv':[sys.executable,'-u','service_fixture.py','ok'],'dependencies':[],'requested_port':0,'readiness':{'kind':'http','path':'/health','expected_status':200},'readiness_timeout_seconds':3,'process_timeout_seconds':30}
 return dict(source_root=src,source_workspace_digest=WS,active_grant=grant,precondition_record_ids=pres,file_relative_path='index.html',expected_content_digest=expected,patches=[{'type':'replace_text','old':'Old','new':'New','expected_occurrences':1}],commit_message='Update checkpoint fixture',verification_argv=verify,browser_target={'kind':'offline_document','html_relative_path':'index.html'},browser_checks=checks,service_definitions=[service],runtime_root=runtime,now_unix=101,git_executable=git,browser_executable=shutil.which('chromium'),cleanup_on_complete=True)

def content_manifest(src:Path):
 return sorted((p.relative_to(src).as_posix(),hashlib.sha256(p.read_bytes()).hexdigest()) for p in src.rglob('*') if p.is_file() and '.git' not in p.parts)
