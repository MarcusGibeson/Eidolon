from __future__ import annotations
import hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'conscious_agent'),str(ROOT/'tools')]
from v1333_workspace_isolation_test_support import WS,active_grant,precondition
FILES={'api.py':'def message():\n    return "old"\n','web/app.js':'const message = "old";\nconsole.log(message);\n','web/index.html':'<!doctype html><html><body><p>old</p></body></html>\n','config.json':'{"message":"old"}\n','README.md':'# Fixture\n\nold\n'}
def init_repo(src):
 subprocess.run(['git','init'],cwd=src,check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE);subprocess.run(['git','config','user.email','fixture@example.invalid'],cwd=src,check=True);subprocess.run(['git','config','user.name','Fixture'],cwd=src,check=True);subprocess.run(['git','add','-A'],cwd=src,check=True);subprocess.run(['git','commit','-m','mixed fixture'],cwd=src,check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE);return 'git'
def source_fixture(base:Path):
 src=base/'source';src.mkdir();
 for rel,text in FILES.items():p=src/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text)
 git=init_repo(src);runtime=base/'runtime';grant=active_grant(commands=('git','git_worktree','shell'));pres={k:precondition(runtime,k) for k in ('git','file_read','file_patch','shell')};return src,runtime,grant,pres,git
def changes(src):
 olds={'api.py':'"old"','web/app.js':'"old"','web/index.html':'<p>old</p>','config.json':'"old"','README.md':'old'};news={'api.py':'"new"','web/app.js':'"new"','web/index.html':'<p>new</p>','config.json':'"new"','README.md':'new'};out=[]
 for rel in FILES:
  p=src/rel;out.append({'relative_path':rel,'expected_content_digest':hashlib.sha256(p.read_bytes()).hexdigest(),'patches':[{'type':'replace_text','old':olds[rel],'new':news[rel],'expected_occurrences':1}]})
 return out
def args(src,runtime,grant,pres,git,**extra):
 commands=[[sys.executable,'-c','import api;assert api.message()=="new"'],['node','--check','web/app.js'],[sys.executable,'-c','import json;assert json.load(open("config.json"))["message"]=="new"']];out=dict(source_root=src,source_workspace_digest=WS,active_grant=grant,precondition_record_ids=pres,changes=changes(src),verification_commands=commands,commit_message='Coordinate mixed-stack change',runtime_root=runtime,now_unix=101,git_executable=git,cleanup_on_complete=True);out.update(extra);return out
def manifest(src):return sorted((p.relative_to(src).as_posix(),hashlib.sha256(p.read_bytes()).hexdigest()) for p in src.rglob('*') if p.is_file() and '.git' not in p.parts and '__pycache__' not in p.parts)
