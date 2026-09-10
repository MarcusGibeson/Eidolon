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
  src,runtime,grant,pres,git=source_fixture(Path(td));before=manifest(src);r=run_framework_adaptation(**args(src,runtime,grant,pres,git));row=r['framework_adaptation'];req(r['ok']);req(row['project_convention_digest'] and row['evaluation_digest']);req(row['workspace_cleaned'] and row['host_recoverable'] and manifest(src)==before);req(not row['raw_source_exposed'] and not row['raw_test_command_exposed']);req(all(not FRAMEWORK_DENIED_AUTHORITY[k] for k in ('dependency_installation_authorized','network_authorized','release_authorized','independent_authority_granted')))
 print({'ok':True,'suite':'v1347.9-framework-adaptation-checkpoint','passed':p,'total':5})
if __name__=='__main__':main()
