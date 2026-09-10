from __future__ import annotations
import hashlib,subprocess,sys,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.path.insert(0,str(ROOT/'tools'))
from v1333_workspace_isolation_test_support import WS,active_grant,precondition
JS='''export async function normalize(value) {\n  const state = new Map([["value", value]]);\n  await Promise.resolve();\n  return state.get("value").trim();\n}\n'''
BROWSER='''export function mount() {\n  const node = document.createElement("div");\n  window.document.body.append(node);\n  return node;\n}\n'''
TS='''export async function add(a: number, b: number): Promise<number> {\n  return a + b;\n}\n'''
TEST='''import test from "node:test";\nimport assert from "node:assert/strict";\nimport { normalize } from "../src/tool.mjs";\ntest("normalizes", async () => assert.equal(await normalize(" x "), "x"));\n'''

def init_repo(src:Path):
 git=shutil.which('git');assert git
 subprocess.run([git,'init'],cwd=src,check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE);subprocess.run([git,'config','user.email','fixture@example.invalid'],cwd=src,check=True);subprocess.run([git,'config','user.name','Fixture'],cwd=src,check=True);subprocess.run([git,'add','-A'],cwd=src,check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE);subprocess.run([git,'commit','-m','js ts fixture'],cwd=src,check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE);return git

def source_fixture(base:Path):
 src=base/'source';(src/'src').mkdir(parents=True);(src/'tests').mkdir();(src/'src'/'tool.mjs').write_text(JS,encoding='utf-8');(src/'src'/'browser.mjs').write_text(BROWSER,encoding='utf-8');(src/'src'/'math.ts').write_text(TS,encoding='utf-8');(src/'tests'/'tool.test.mjs').write_text(TEST,encoding='utf-8');(src/'package.json').write_text('{"name":"fixture","private":true,"type":"module","scripts":{"test":"node --test"}}\n',encoding='utf-8');(src/'tsconfig.json').write_text('{"compilerOptions":{"strict":true,"target":"ES2022","module":"NodeNext","moduleResolution":"NodeNext","noEmit":true},"include":["src/**/*.ts"]}\n',encoding='utf-8');(src/'README.md').write_text('# v1342 fixture\n',encoding='utf-8');git=init_repo(src);runtime=base/'runtime';grant=active_grant(commands=('git','git_worktree','shell'));pres={k:precondition(runtime,k) for k in ('git','file_read','file_patch','shell')};return src,runtime,grant,pres,git

def args(src,runtime,grant,pres,git,*,relative_path='src/tool.mjs',patches=None,test_argv=None,**extra):
 target=src.joinpath(*relative_path.split('/'));expected=hashlib.sha256(target.read_bytes()).hexdigest();node=shutil.which('node');tsc=shutil.which('tsc')
 if patches is None:
  patches=[{'type':'replace_text','old':'  return state.get("value").trim();','new':'  const result = state.get("value").trim();\n  return result;','expected_occurrences':1}] if relative_path.endswith('.mjs') else [{'type':'replace_text','old':'  return a + b;','new':'  const total: number = a + b;\n  return total;','expected_occurrences':1}]
 if test_argv is None:
  test_argv=[node,'--test','tests/tool.test.mjs'] if relative_path.endswith('.mjs') else [tsc,'--noEmit','--pretty','false','--strict','--target','ES2022','--module','NodeNext','--moduleResolution','NodeNext',relative_path]
 out=dict(source_root=src,source_workspace_digest=WS,active_grant=grant,precondition_record_ids=pres,relative_path=relative_path,expected_content_digest=expected,patches=patches,test_argv=test_argv,commit_message='Refine JavaScript TypeScript implementation',runtime_root=runtime,now_unix=101,git_executable=git,node_executable=node,tsc_executable=tsc,cleanup_on_complete=True);out.update(extra);return out

def manifest(src:Path): return sorted((p.relative_to(src).as_posix(),hashlib.sha256(p.read_bytes()).hexdigest()) for p in src.rglob('*') if p.is_file() and '.git' not in p.parts and 'node_modules' not in p.parts)
