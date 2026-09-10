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
  src,runtime,grant,pres,git=source_fixture(Path(td));c=changes(src);c[0]['expected_content_digest']='0'*64;r=run_cross_language_change(**args(src,runtime,grant,pres,git,changes=c));req(not r['ok'] and not r['cross_language_change']['partial_commit_created'])
 with tempfile.TemporaryDirectory() as td:
  src,runtime,grant,pres,git=source_fixture(Path(td));c=changes(src);c[3]['patches']=[{'type':'replace_text','old':'"old"','new':'broken','expected_occurrences':1}];r=run_cross_language_change(**args(src,runtime,grant,pres,git,changes=c));req(not r['ok'] and 'structure_invalid' in r['cross_language_change']['failure_stage'] and not r['cross_language_change']['partial_commit_created'])
 with tempfile.TemporaryDirectory() as td:
  src,runtime,grant,pres,git=source_fixture(Path(td));r=run_cross_language_change(**args(src,runtime,grant,pres,git,verification_commands=[[sys.executable,'-c','raise SystemExit(4)']]));req(not r['ok'] and r['cross_language_change']['failure_stage']=='cross_language_verification_failed' and not r['cross_language_change']['partial_commit_created'])
 req(not inspect_change_set([{'relative_path':'x.py'},{'relative_path':'x.py'}])['ok']);req(not CROSS_LANGUAGE_DENIED_AUTHORITY['network_authorized']);req(not CROSS_LANGUAGE_DENIED_AUTHORITY['dependency_installation_authorized']);req(not CROSS_LANGUAGE_DENIED_AUTHORITY['release_authorized'])
 print({'ok':True,'suite':'v1349.6-8-cross-language-reliability','passed':p,'total':7})
if __name__=='__main__':main()
