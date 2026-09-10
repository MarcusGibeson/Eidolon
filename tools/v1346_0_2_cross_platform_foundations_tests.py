from __future__ import annotations
import sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'conscious_agent'),str(ROOT/'tools')]
from cross_platform_automation import *
from v1346_cross_platform_automation_test_support import source_fixture
def main():
 p=0
 def req(v):
  nonlocal p;assert v;p+=1
 req(target_platform('linux')=='posix' and target_platform('nt')=='windows')
 req(render_argument_vector(['echo','a b'],'posix')=="echo 'a b'" and '"a b"' in render_argument_vector(['echo','a b'],'windows'))
 req(sanitize_environment({'SAFE':'1','LD_PRELOAD':'x','BAD-NAME':'x'},platform='posix')=={'SAFE':'1'})
 req(normalize_portable_relative('scripts/x.sh')=='scripts/x.sh')
 req(platform_capability_record('windows')['windows_semantics_preserved'] and not platform_capability_record('windows')['native_execution_validated'])
 with tempfile.TemporaryDirectory() as td:
  src,*_=source_fixture(Path(td));r=inspect_cross_platform_project(src);req(r['posix_script_count']==1 and r['windows_script_count']==1)
 print({'ok':True,'suite':'v1346.0-2-cross-platform-foundations','passed':p,'total':6})
if __name__=='__main__':main()
