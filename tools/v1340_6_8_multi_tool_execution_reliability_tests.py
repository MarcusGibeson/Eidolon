from __future__ import annotations
import subprocess,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.path.insert(0,str(ROOT/'tools'))
from v1340_multi_tool_execution_test_support import *
from multi_tool_execution import *
import runtime_efficiency_benchmark as reb

def main():
 p=[0]
 def req(x,n):assert x,n;p[0]+=1
 with tempfile.TemporaryDirectory() as td:
  src,runtime,grant,pres,git=source_fixture(Path(td));before=content_manifest(src);r=run_multi_tool_execution(**campaign_args(src,runtime,grant,pres,git,verify_ok=False));row=r['campaign'];req(not r['ok'] and row['failure_stage']=='verification_failed','verification_failure_stops_campaign')
  req(row['workspace_cleaned'] and row['host_recoverable'] and row['orphaned_service_count']==0,'failed_campaign_cleanup')
  req(not row['browser_passed'] and not row['service_ready'],'later_side_effects_not_started')
  req(content_manifest(src)==before and row['selected_source_content_modified'] is False,'failed_campaign_source_immutable')
 with tempfile.TemporaryDirectory() as td:
  src,runtime,grant,pres,git=source_fixture(Path(td));args=campaign_args(src,runtime,grant,pres,git);first=run_multi_tool_execution(**args);second=run_multi_tool_execution(**args);req(first['ok'] and second['status']=='multi_tool_campaign_already_exists' and second['action_executed'] is False,'duplicate_campaign_not_reexecuted')
  req(second['campaign']['tool_retry_executed'] is False and second['campaign']['release_authorized'] is False,'duplicate_no_retry_or_release')
 # The retained runtime benchmark must separate measurement timeout from hardware-sensitive performance judgment.
 seen=[]
 original=reb.run_bounded_command
 class _Result:
  ok=True;elapsed_seconds=0.01
 def _fake(command,*,cwd,env,timeout_seconds):
  seen.append(float(timeout_seconds));return _Result()
 try:
  reb.run_bounded_command=_fake
  measured=reb._subprocess_seconds([sys.executable,'-c','pass'],cwd=ROOT,env={},repeat=1)
 finally:
  reb.run_bounded_command=original
 req(measured['count']==1 and seen==[reb.BENCHMARK_SUBPROCESS_TIMEOUT_SECONDS] and seen[0]>=30.0,'hardware_sensitive_benchmark_has_measurement_headroom')
 print({'ok':True,'suite':'v1340.6-8-multi-tool-execution-reliability','passed':p[0],'total':7})
if __name__=='__main__':main()
