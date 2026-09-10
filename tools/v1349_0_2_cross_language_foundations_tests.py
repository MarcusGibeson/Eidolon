from __future__ import annotations
import sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'conscious_agent'),str(ROOT/'tools')]
from cross_language_changes import *
from v1349_cross_language_test_support import *
def main():
 p=0
 def req(v):nonlocal p;assert v;p+=1
 with tempfile.TemporaryDirectory() as td:
  src,*_=source_fixture(Path(td));r=inspect_change_set(changes(src));req(r['ok'] and r['change_count']==5);req(r['file_type_count']==5);req(len(r['change_set_digest'])==64)
 req(not inspect_change_set([])['ok']);req(not inspect_change_set([{'relative_path':'../x.py'}])['ok'])
 print({'ok':True,'suite':'v1349.0-2-cross-language-foundations','passed':p,'total':5})
if __name__=='__main__':main()
