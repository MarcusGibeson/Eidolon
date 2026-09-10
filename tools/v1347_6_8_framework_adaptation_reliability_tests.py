from __future__ import annotations
import sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'conscious_agent'),str(ROOT/'tools')]
from framework_adaptation import *
from v1347_framework_adaptation_test_support import *
def main():
 p=0
 def req(v):nonlocal p;assert v;p+=1
 with tempfile.TemporaryDirectory() as td:
  src,*_=source_fixture(Path(td));e=evaluate_framework_change(source_root=src,relative_path='src/pkg/core.py',patches=[{'type':'replace_text','old':'from .util import double','new':'from flask import Flask','expected_occurrences':1}]);req(not e['ok'] and 'undeclared_framework_introduction' in e['reasons']);e2=evaluate_framework_change(source_root=src,relative_path='src/pkg/core.py',patches=[{'type':'replace_text','old':'from .util import double','new':'from flask import Flask','expected_occurrences':1}],architecture_change_declared=True);req(e2['ok'])
 with tempfile.TemporaryDirectory() as td:
  src,*_=source_fixture(Path(td));e=evaluate_framework_change(source_root=src,relative_path='src/pkg/core.py',patches=[{'type':'replace_text','old':'from .util import double','new':'from pkg.util import double','expected_occurrences':1}]);req(not e['ok'] and 'undeclared_import_style_drift' in e['reasons'])
 with tempfile.TemporaryDirectory() as td:
  src,runtime,grant,pres,git=source_fixture(Path(td));r=run_framework_adaptation(**args(src,runtime,grant,pres,git,test_argv=[sys.executable,'-c','raise SystemExit(2)']));req(not r['ok'] and r['framework_adaptation']['adaptation_state']=='failed')
 for bad in ('../x.py','data/x.py','x.txt'):
  r=run_framework_adaptation(source_root='.',source_workspace_digest='x',active_grant={},precondition_record_ids={},relative_path=bad,expected_content_digest='',patches=[],test_argv=[]);req(not r['ok'])
 req(not FRAMEWORK_DENIED_AUTHORITY['dependency_installation_authorized'] and not FRAMEWORK_DENIED_AUTHORITY['architecture_rewrite_authorized'])
 print({'ok':True,'suite':'v1347.6-8-framework-adaptation-reliability','passed':p,'total':8})
if __name__=='__main__':main()
