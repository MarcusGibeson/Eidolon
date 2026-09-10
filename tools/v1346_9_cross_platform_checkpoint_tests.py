from __future__ import annotations
import os,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'conscious_agent'),str(ROOT/'tools')]
from cross_platform_automation import *
from v1346_cross_platform_automation_test_support import *
def main():
 p=0
 def req(v):
  nonlocal p;assert v;p+=1
 with tempfile.TemporaryDirectory() as td:
  src,runtime,grant,pres,git=source_fixture(Path(td));before=manifest(src);r=run_cross_platform_automation(**args(src,runtime,grant,pres,git));row=r['cross_platform_automation'];req(r['ok'] and row['native_execution_validated']==(os.name!='nt'));req(row['workspace_cleaned'] and row['host_recoverable'] and manifest(src)==before);req(not row['raw_script_exposed'] and not row['raw_command_exposed']);req(not row['selected_source_content_modified']);req(all(not CROSS_PLATFORM_DENIED_AUTHORITY[k] for k in ('network_authorized','installation_authorized','release_authorized','independent_authority_granted')))
 print({'ok':True,'suite':'v1346.9-cross-platform-checkpoint','passed':p,'total':5})
if __name__=='__main__':main()
