from __future__ import annotations
import hashlib,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.path.insert(0,str(ROOT/'tools'))
from v1333_workspace_isolation_test_support import WS,active_grant,precondition
SH='''#!/bin/sh\nset -eu\nprintf '%s\\n' "hello"\n''';PS="Write-Output 'hello'\n"
def init_repo(src):
 git='git';subprocess.run([git,'init'],cwd=src,check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE);subprocess.run([git,'config','user.email','fixture@example.invalid'],cwd=src,check=True);subprocess.run([git,'config','user.name','Fixture'],cwd=src,check=True);subprocess.run([git,'add','-A'],cwd=src,check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE);subprocess.run([git,'commit','-m','portable fixture'],cwd=src,check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE);return git
def source_fixture(base:Path):
 src=base/'source';(src/'scripts').mkdir(parents=True);(src/'scripts'/'hello.sh').write_text(SH);(src/'scripts'/'hello.ps1').write_text(PS);git=init_repo(src);runtime=base/'runtime';grant=active_grant(commands=('git','git_worktree','shell'));pres={k:precondition(runtime,k) for k in ('git','file_read','file_patch','shell')};return src,runtime,grant,pres,git
def args(src,runtime,grant,pres,git,**extra):
 p=src/'scripts'/'hello.sh';out=dict(source_root=src,source_workspace_digest=WS,active_grant=grant,precondition_record_ids=pres,relative_path='scripts/hello.sh',expected_content_digest=hashlib.sha256(p.read_bytes()).hexdigest(),patches=[{'type':'replace_text','old':'"hello"','new':'"hello world"','expected_occurrences':1}],target='posix',test_argv=['sh','scripts/hello.sh'],commit_message='Refine portable script',runtime_root=runtime,now_unix=101,git_executable=git,cleanup_on_complete=True);out.update(extra);return out
def manifest(src):return sorted((p.relative_to(src).as_posix(),hashlib.sha256(p.read_bytes()).hexdigest()) for p in src.rglob('*') if p.is_file() and '.git' not in p.parts)
