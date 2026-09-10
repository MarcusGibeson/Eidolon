from __future__ import annotations
import sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.path.insert(0,str(ROOT/'tools'))
from v1345_windows_automation_test_support import *
from windows_automation import *
def main():
 p=[0]
 def req(x,n):assert x,n;p[0]+=1
 req(quote_powershell_literal("O'Brien")=="'O''Brien'",'ps_quote')
 req(windows_path_within(r'C:\Work\Project',r'c:\work\project\src\app.ps1') and not windows_path_within(r'C:\Work\Project',r'C:\Work\Elsewhere\x.ps1'),'path_case_boundary')
 req(not windows_path_within(r'C:\Work',r'\\?\C:\Work\x') and not windows_path_within(r'C:\Work',r'C:\Work\x.txt:secret'),'device_ads')
 req(build_windows_service_argv('stop','EidolonSvc')==['sc.exe','stop','EidolonSvc'] and build_windows_process_tree_stop_argv(42)==['taskkill.exe','/PID','42','/T','/F'],'service_tree_argv')
 req(classify_installer_argv(['msiexec.exe','/i','app.msi'])['installer_detected'] and not classify_installer_argv(['tool.exe'])['installer_detected'],'installer_classification')
 with tempfile.TemporaryDirectory() as td:
  src,*_=source_fixture(Path(td));r=inspect_windows_automation_project(src);req(r['powershell_file_count']==2 and not r['native_windows_execution_validated'] and r['invalid_script_count']==0,'inspection')
 print({'ok':True,'suite':'v1345.0-2-windows-automation-foundations','passed':p[0],'total':6})
if __name__=='__main__':main()
