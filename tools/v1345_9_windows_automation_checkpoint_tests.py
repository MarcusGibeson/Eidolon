from __future__ import annotations
import os,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.path.insert(0,str(ROOT/'tools'))
from v1345_windows_automation_test_support import *
from windows_automation import *
def main():
 p=[0]
 def req(x,n):assert x,n;p[0]+=1
 with tempfile.TemporaryDirectory() as td:
  src,runtime,grant,pres,git=source_fixture(Path(td));before=manifest(src);r=run_windows_automation_implementation(**args(src,runtime,grant,pres,git));row=r['windows_automation'];req(r['ok'] and row['implementation_state']=='completed' and row['portable_validation_passed'],'campaign');req(row['workspace_cleaned'] and row['host_recoverable'] and manifest(src)==before,'recovery');req(not row['raw_script_exposed'] and not row['native_windows_execution_validated'],'evidence_truth');req((row['native_windows_host'] is True)==(os.name=='nt'),'host_truth')
 req(all(not WINDOWS_AUTOMATION_DENIED_AUTHORITY[k] for k in ('installer_execution_authorized','service_mutation_authorized','elevation_authorized','installation_authorized','release_authorized','independent_authority_granted')),'authority')
 print({'ok':True,'suite':'v1345.9-windows-automation-checkpoint','passed':p[0],'total':5})
if __name__=='__main__':main()
