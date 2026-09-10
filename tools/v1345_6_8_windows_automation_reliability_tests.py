from __future__ import annotations
import sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.path.insert(0,str(ROOT/'tools'))
from v1345_windows_automation_test_support import *
from windows_automation import *
def main():
 p=[0]
 def req(x,n):assert x,n;p[0]+=1
 with tempfile.TemporaryDirectory() as td:
  src,runtime,grant,pres,git=source_fixture(Path(td));before=manifest(src);pa=patches(src,new='$Greeting = "Hello, $Name"\nif ($true) {');r=run_windows_automation_implementation(**args(src,runtime,grant,pres,git,patches_=pa));req(not r['ok'] and r['windows_automation']['failure_stage']=='powershell_portable_syntax_invalid' and manifest(src)==before,'unbalanced_blocked')
 with tempfile.TemporaryDirectory() as td:
  src,runtime,grant,pres,git=source_fixture(Path(td));pa=patches(src,new='$Greeting = "Hello, $Name"\nStart-Process msiexec.exe -ArgumentList "/i app.msi"');r=run_windows_automation_implementation(**args(src,runtime,grant,pres,git,patches_=pa));req(not r['ok'] and r['windows_automation']['failure_stage']=='undeclared_installer_behavior','installer_blocked')
 with tempfile.TemporaryDirectory() as td:
  src,runtime,grant,pres,git=source_fixture(Path(td));pa=patches(src,new='$Greeting = "Hello, $Name"\nStart-Service EidolonSvc');r=run_windows_automation_implementation(**args(src,runtime,grant,pres,git,patches_=pa));req(not r['ok'] and r['windows_automation']['failure_stage']=='undeclared_service_behavior','service_blocked')
 with tempfile.TemporaryDirectory() as td:
  src,runtime,grant,pres,git=source_fixture(Path(td));pa=patches(src,new='$Greeting = "Hello, $Name"\nStart-Process powershell -Verb RunAs');r=run_windows_automation_implementation(**args(src,runtime,grant,pres,git,patches_=pa));req(not r['ok'] and r['windows_automation']['failure_stage']=='undeclared_elevation_behavior','elevation_blocked')
 with tempfile.TemporaryDirectory() as td:
  src,runtime,grant,pres,git=source_fixture(Path(td));pa=patches(src,new='$Greeting = "Hello, $Name"\nRemove-Item C:\\Temp -Recurse -Force');r=run_windows_automation_implementation(**args(src,runtime,grant,pres,git,patches_=pa));req(not r['ok'] and r['windows_automation']['failure_stage']=='destructive_windows_system_behavior_rejected','destructive_blocked')
 try:build_windows_service_argv('delete','Svc');raise AssertionError('bad service action')
 except ValueError:req(True,'service_action')
 try:build_windows_service_argv('stop','bad name!');raise AssertionError('bad service name')
 except ValueError:req(True,'service_name')
 try:build_windows_process_tree_stop_argv(0);raise AssertionError('bad pid')
 except ValueError:req(True,'pid')
 req(all(not WINDOWS_AUTOMATION_DENIED_AUTHORITY[k] for k in ('installer_execution_authorized','service_mutation_authorized','elevation_authorized','source_application_authorized','release_authorized')),'authority')
 print({'ok':True,'suite':'v1345.6-8-windows-automation-reliability','passed':p[0],'total':9})
if __name__=='__main__':main()
