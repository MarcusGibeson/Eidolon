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
  src,*_=source_fixture(Path(td));r=inspect_framework_conventions(src);req(r['layout_style']=='src');req(r['import_style'] in {'relative','mixed'});req(r['test_file_count']==1);req(r['convention_inferred']);e=evaluate_framework_change(source_root=src,relative_path='src/pkg/core.py',patches=[{'type':'replace_text','old':'return double(value) + 1','new':'return double(value) + 2','expected_occurrences':1}]);req(e['ok'])
 print({'ok':True,'suite':'v1347.0-2-framework-adaptation-foundations','passed':p,'total':5})
if __name__=='__main__':main()
