from __future__ import annotations
import sys,tempfile,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.path.insert(0,str(ROOT/'tools'))
from v1342_javascript_typescript_test_support import *
from javascript_typescript_implementation import *
def main():
 p=[0]
 def req(x,n):assert x,n;p[0]+=1
 with tempfile.TemporaryDirectory() as td:
  src,runtime,grant,pres,git=source_fixture(Path(td));before=manifest(src);r=run_javascript_typescript_implementation(**args(src,runtime,grant,pres,git,patches=[{'type':'replace_text','old':'normalize(value)','new':'normalize(value, mode = "trim")','expected_occurrences':1}]));req(not r['ok'] and r['javascript_typescript_implementation']['failure_stage']=='undeclared_export_contract_change','export_signature_change_blocked');req(manifest(src)==before,'failed_export_change_source_immutable')
 with tempfile.TemporaryDirectory() as td:
  src,runtime,grant,pres,git=source_fixture(Path(td));r=run_javascript_typescript_implementation(**args(src,runtime,grant,pres,git,patches=[{'type':'replace_text','old':'export async function normalize','new':'export function normalize','expected_occurrences':1}]));req(not r['ok'] and r['javascript_typescript_implementation']['failure_stage']=='undeclared_export_contract_change','async_export_change_blocked')
 with tempfile.TemporaryDirectory() as td:
  src,runtime,grant,pres,git=source_fixture(Path(td));patch=[{'type':'replace_text','old':'export async function normalize','new':'import leftPad from "left-pad";\nexport async function normalize','expected_occurrences':1}];r=run_javascript_typescript_implementation(**args(src,runtime,grant,pres,git,patches=patch));req(not r['ok'] and r['javascript_typescript_implementation']['failure_stage']=='undeclared_external_dependency','external_dependency_change_blocked')
 with tempfile.TemporaryDirectory() as td:
  src,runtime,grant,pres,git=source_fixture(Path(td));patch=[{'type':'replace_text','old':'export async function normalize(value) {','new':'module.exports.normalize = async function(value) {','expected_occurrences':1}];r=run_javascript_typescript_implementation(**args(src,runtime,grant,pres,git,patches=patch,allow_export_change=True));req(not r['ok'] and r['javascript_typescript_implementation']['failure_stage']=='undeclared_module_system_change','module_system_change_blocked')
 with tempfile.TemporaryDirectory() as td:
  src,runtime,grant,pres,git=source_fixture(Path(td));r=run_javascript_typescript_implementation(**args(src,runtime,grant,pres,git,patches=[{'type':'replace_text','old':'  return state.get("value").trim();','new':'  return (','expected_occurrences':1}]));req(not r['ok'] and r['javascript_typescript_implementation']['failure_stage']=='javascript_typescript_check_failed','javascript_syntax_failure_blocked')
 with tempfile.TemporaryDirectory() as td:
  src,runtime,grant,pres,git=source_fixture(Path(td));r=run_javascript_typescript_implementation(**args(src,runtime,grant,pres,git,relative_path='src/math.ts',patches=[{'type':'replace_text','old':'  return a + b;','new':'  return "bad";','expected_occurrences':1}]));req(not r['ok'] and r['javascript_typescript_implementation']['failure_stage']=='javascript_typescript_check_failed','typescript_type_failure_blocked')
 with tempfile.TemporaryDirectory() as td:
  src,runtime,grant,pres,git=source_fixture(Path(td));r=run_javascript_typescript_implementation(**args(src,runtime,grant,pres,git,test_argv=[shutil.which('node'),'-e','process.exit(9)']));row=r['javascript_typescript_implementation'];req(not r['ok'] and row['failure_stage']=='javascript_typescript_tests_failed' and row['workspace_cleaned'],'focused_test_failure_cleans')
 req(not JS_TS_DENIED_AUTHORITY['dependency_installation_authorized'] and not JS_TS_DENIED_AUTHORITY['network_authorized'] and not JS_TS_DENIED_AUTHORITY['release_authorized'],'no_dependency_network_release_authority')
 print({'ok':True,'suite':'v1342.6-8-javascript-typescript-reliability','passed':p[0],'total':9})
if __name__=='__main__':main()
