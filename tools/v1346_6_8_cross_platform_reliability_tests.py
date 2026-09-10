from __future__ import annotations
import hashlib,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'conscious_agent'),str(ROOT/'tools')]
from cross_platform_automation import *
from v1346_cross_platform_automation_test_support import *
def main():
 p=0
 def req(v):
  nonlocal p;assert v;p+=1
 for bad in ('../x.sh','/tmp/x.sh','data/x.sh'):
  try:normalize_portable_relative(bad);ok=False
  except ValueError:ok=True
  req(ok)
 with tempfile.TemporaryDirectory() as td:
  src,runtime,grant,pres,git=source_fixture(Path(td));bad=args(src,runtime,grant,pres,git,expected_content_digest='0'*64);r=run_cross_platform_automation(**bad);req(not r['ok'] and r['cross_platform_automation']['failure_stage']=='stale_portable_content_digest')
 with tempfile.TemporaryDirectory() as td:
  src,runtime,grant,pres,git=source_fixture(Path(td));r=run_cross_platform_automation(**args(src,runtime,grant,pres,git,patches=[{'type':'replace_text','old':'set -eu','new':'if then','expected_occurrences':1}]));req(not r['ok'] and 'syntax' in r['cross_platform_automation']['failure_stage'])
 with tempfile.TemporaryDirectory() as td:
  src,runtime,grant,pres,git=source_fixture(Path(td));r=run_cross_platform_automation(**args(src,runtime,grant,pres,git,test_argv=['sh','-c','exit 3']));req(not r['ok'] and r['cross_platform_automation']['failure_stage']=='portable_tests_failed')
 req(not CROSS_PLATFORM_DENIED_AUTHORITY['network_authorized'] and not CROSS_PLATFORM_DENIED_AUTHORITY['release_authorized'])
 req(render_argument_vector(['printf','%s','a;b'],'posix').endswith("'a;b'"))
 print({'ok':True,'suite':'v1346.6-8-cross-platform-reliability','passed':p,'total':8})
if __name__=='__main__':main()
