from __future__ import annotations
import hashlib, json, shutil, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'conscious_agent'));sys.path.insert(0,str(ROOT/'tools'))
from v1333_workspace_isolation_test_support import WS,active_grant,precondition

JSON='''{"name":"eidolon","limits":{"retries":3,"enabled":true},"tags":["local","safe"]}\n'''
YAML='''name: eidolon\nlimits:\n  retries: 3\n  enabled: true\ntags:\n  - local\n  - safe\n'''
TOML='''[service]\nport = 8000\nenabled = true\n'''
SQL='''CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT NOT NULL);\nCREATE INDEX idx_users_name ON users(name);\n'''
MIGRATION='''CREATE TABLE notes (id INTEGER PRIMARY KEY, body TEXT NOT NULL);\n'''

def init_repo(src:Path):
 git=shutil.which('git');assert git
 subprocess.run([git,'init'],cwd=src,check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
 subprocess.run([git,'config','user.email','fixture@example.invalid'],cwd=src,check=True)
 subprocess.run([git,'config','user.name','Fixture'],cwd=src,check=True)
 subprocess.run([git,'add','-A'],cwd=src,check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
 subprocess.run([git,'commit','-m','data schema fixture'],cwd=src,check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
 return git

def source_fixture(base:Path):
 src=base/'source';(src/'config').mkdir(parents=True);(src/'db'/'migrations').mkdir(parents=True)
 (src/'config'/'settings.json').write_text(JSON,encoding='utf-8')
 (src/'config'/'settings.yaml').write_text(YAML,encoding='utf-8')
 (src/'config'/'settings.toml').write_text(TOML,encoding='utf-8')
 (src/'db'/'schema.sql').write_text(SQL,encoding='utf-8')
 (src/'db'/'migrations'/'001_notes.sql').write_text(MIGRATION,encoding='utf-8')
 (src/'README.md').write_text('# v1344 fixture\n',encoding='utf-8')
 git=init_repo(src);runtime=base/'runtime';grant=active_grant(commands=('git','git_worktree','shell'));pres={k:precondition(runtime,k) for k in ('git','file_read','file_patch','shell')};return src,runtime,grant,pres,git

def patch(src:Path,rel:str,old:str,new:str):
 p=src.joinpath(*rel.split('/'));return [{'type':'replace_text','old':old,'new':new,'expected_occurrences':1}]

def test_argv(rel:str):
 py=sys.executable
 if rel.endswith('.json'): return [py,'-c',f'import json;json.load(open({rel!r},encoding="utf-8"))']
 if rel.endswith(('.yaml','.yml')): return [py,'-c',f'import yaml;yaml.safe_load(open({rel!r},encoding="utf-8"))']
 if rel.endswith('.toml'): return [py,'-c',f'import tomllib;tomllib.load(open({rel!r},"rb"))']
 return [py,'-c',f'import sqlite3,pathlib;c=sqlite3.connect(":memory:");c.executescript(pathlib.Path({rel!r}).read_text());c.close()']

def args(src,runtime,grant,pres,git,*,relative_path='config/settings.json',patches=None,**extra):
 target=src.joinpath(*relative_path.split('/'));expected=hashlib.sha256(target.read_bytes()).hexdigest()
 if patches is None:
  if relative_path.endswith('.json'): patches=patch(src,relative_path,'"retries":3','"retries":4')
  elif relative_path.endswith(('.yaml','.yml')): patches=patch(src,relative_path,'retries: 3','retries: 4')
  elif relative_path.endswith('.toml'): patches=patch(src,relative_path,'port = 8000','port = 8001')
  elif 'migrations' in relative_path: patches=patch(src,relative_path,'body TEXT NOT NULL','body TEXT NOT NULL, created_at TEXT')
  else: patches=patch(src,relative_path,'name TEXT NOT NULL','name TEXT NOT NULL, email TEXT')
 out=dict(source_root=src,source_workspace_digest=WS,active_grant=grant,precondition_record_ids=pres,relative_path=relative_path,expected_content_digest=expected,patches=patches,test_argv=test_argv(relative_path),commit_message='Refine structured data schema',runtime_root=runtime,now_unix=101,git_executable=git,cleanup_on_complete=True);out.update(extra);return out

def manifest(src:Path):return sorted((p.relative_to(src).as_posix(),hashlib.sha256(p.read_bytes()).hexdigest()) for p in src.rglob('*') if p.is_file() and '.git' not in p.parts)
