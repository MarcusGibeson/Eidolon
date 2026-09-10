from __future__ import annotations
import hashlib,shutil,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.path.insert(0,str(ROOT/'tools'))
from v1333_workspace_isolation_test_support import WS,active_grant,precondition
HTML='''<!doctype html>\n<html><head><meta name="viewport" content="width=device-width, initial-scale=1"><title>Fixture</title></head><body><main class="card"><img alt="Decorative" src="data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///ywAAAAAAQABAAACAUwAOw=="><label for="name">Name</label><input id="name"><button id="go" onclick="document.getElementById('out').textContent='Hello '+document.getElementById('name').value">Run</button><div id="out" aria-live="polite">Idle</div></main></body></html>\n'''
CSS='''.card { width: min(90vw, 32rem); margin: 1rem auto; }\nbutton:focus-visible, input:focus-visible { outline: 2px solid currentColor; }\n@media (max-width: 40rem) { .card { width: 95%; } }\n@media (prefers-reduced-motion: reduce) { * { scroll-behavior: auto; } }\n'''
def init_repo(src:Path):
 git=shutil.which('git');assert git;subprocess.run([git,'init'],cwd=src,check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE);subprocess.run([git,'config','user.email','fixture@example.invalid'],cwd=src,check=True);subprocess.run([git,'config','user.name','Fixture'],cwd=src,check=True);subprocess.run([git,'add','-A'],cwd=src,check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE);subprocess.run([git,'commit','-m','ui fixture'],cwd=src,check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE);return git
def source_fixture(base:Path):
 src=base/'source';src.mkdir();(src/'index.html').write_text(HTML,encoding='utf-8');(src/'styles.css').write_text(CSS,encoding='utf-8');(src/'README.md').write_text('# v1343 fixture\n',encoding='utf-8');git=init_repo(src);runtime=base/'runtime';grant=active_grant(commands=('git','git_worktree','browser'));pres={k:precondition(runtime,k) for k in ('git','file_read','file_patch','browser')};return src,runtime,grant,pres,git
def change(path:Path,old,new):return {'relative_path':path.name,'expected_content_digest':hashlib.sha256(path.read_bytes()).hexdigest(),'patches':[{'type':'replace_text','old':old,'new':new,'expected_occurrences':1}]}
def args(src,runtime,grant,pres,git,*,changes=None,checks=None,interactions=None,**extra):
 if changes is None:changes=[change(src/'index.html','<div id="out" aria-live="polite">Idle</div>','<div id="out" aria-live="polite">Ready</div>'),change(src/'styles.css','margin: 1rem auto;','margin: 1.25rem auto;')]
 if interactions is None:interactions=[{'op':'fill','selector':'#name','value':'Ada'},{'op':'press','selector':'#go','value':'Enter'}]
 if checks is None:checks=[{'kind':'text_equals','selector':'#out','expected':'Hello Ada'},{'kind':'visible','selector':'#go'}]
 out=dict(source_root=src,source_workspace_digest=WS,active_grant=grant,precondition_record_ids=pres,changes=changes,preview_html_relative_path='index.html',preview_css_relative_paths=['styles.css'],browser_interactions=interactions,browser_checks=checks,commit_message='Refine accessible responsive interface',runtime_root=runtime,now_unix=101,git_executable=git,browser_executable=shutil.which('chromium'),cleanup_on_complete=True);out.update(extra);return out
def manifest(src:Path):return sorted((p.relative_to(src).as_posix(),hashlib.sha256(p.read_bytes()).hexdigest()) for p in src.rglob('*') if p.is_file() and '.git' not in p.parts)
