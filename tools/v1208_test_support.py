from __future__ import annotations
import hashlib, json, shutil, sys, tempfile
from pathlib import Path
from typing import Callable
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT/'conscious_agent') not in sys.path: sys.path.insert(0,str(ROOT/'conscious_agent'))
from ordinary_chat_development_campaign import process_ordinary_chat_development_turn
from python_cli_implementation_foundations import run_or_resume_python_cli_implementation

def source_signature()->str:
 h=hashlib.sha256(); ignored={'.git','data','__pycache__','.pytest_cache','.venv','venv'}
 for p in sorted(ROOT.rglob('*')):
  if not p.is_file(): continue
  rel=p.relative_to(ROOT)
  if any(x in ignored for x in rel.parts) or p.suffix in {'.pyc','.pyo'}: continue
  h.update(rel.as_posix().encode()); h.update(hashlib.sha256(p.read_bytes()).digest())
 return h.hexdigest()

def runtime(prefix:str)->Path: return Path(tempfile.mkdtemp(prefix=f'eid-v1208-{prefix}-'))
def cleanup(path:Path)->None: shutil.rmtree(path,ignore_errors=True)
def approved(rt:Path,session_id='v1208')->dict:
 turn=process_ordinary_chat_development_turn('Build me a Python CLI that counts words',action_projection={'intent':{'category':'action_request'}},session_id=session_id,runtime_root=rt)
 p=turn['proposal']; a=process_ordinary_chat_development_turn(f"Approve development proposal {p['proposal_id']} revision {p['revision']}.",runtime_root=rt)
 if a.get('event')!='approval_consumed': raise AssertionError(a)
 return p

def provider(mode='unittest',calls:list[int]|None=None)->Callable[[str],str]:
 calls=calls if calls is not None else []
 def gen(prompt:str)->str:
  calls.append(1); q=json.loads(prompt)
  test="import unittest\nfrom tool import count_words\nclass ToolTest(unittest.TestCase):\n    def test_counts(self): self.assertEqual(count_words('one two'),2)\n"
  if mode=='fail': test=test.replace(',2)',',3)')
  elif mode=='network': test='import socket\n'+test
  elif mode=='process': test='import os\nos.system(\'echo nope\')\n'+test
  elif mode=='timeout': test='while True: pass\n'
  elif mode=='output': test="print('x'*540000)\n"
  elif mode=='pytest': test="import pytest\nfrom tool import count_words\ndef test_counts(): assert count_words('one two') == 2\n"
  elif mode=='pytest_fail': test="import pytest\nfrom tool import count_words\ndef test_counts(): assert count_words('one two') == 3\n"
  elif mode=='write': test="open('forbidden.txt','w').write('x')\n"
  elif mode=='pathlib_write': test="import pathlib\npathlib.Path('forbidden-pathlib.txt').write_text('x',encoding='utf-8')\n"
  elif mode=='syntax': test='def broken(:\n'
  content={'main.py':"import argparse\nfrom tool import count_words\np=argparse.ArgumentParser();p.add_argument('text',nargs='*');a=p.parse_args();print(count_words(' '.join(a.text)))\n",'tool.py':"def count_words(text):\n    return len(str(text).split())\n",'tests/test_tool.py':test,'README.md':'# Word counter\n'}
  return json.dumps({'authority':q['authority'],'files':[{'path':x,'operation':'create','content':content[x]} for x in q['planned_paths']]})
 return gen

def campaign(rt:Path,mode='unittest',calls:list[int]|None=None,session_id='v1208'):
 p=approved(rt,session_id); impl=run_or_resume_python_cli_implementation(p['proposal_id'],expected_revision=1,expected_revision_digest=p['revision_digest'],runtime_root=rt,provider_generate=provider(mode,calls))
 if not impl.get('workspace_digest'): raise AssertionError(impl)
 return p,impl
