from __future__ import annotations
import sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.path.insert(0,str(ROOT/'tools'))
from v1341_python_implementation_test_support import *
from python_implementation import *

def main():
 p=[0]
 def req(x,n): assert x,n; p[0]+=1
 with tempfile.TemporaryDirectory() as td:
  src,runtime,grant,pres,git=source_fixture(Path(td));before=content_manifest(src)
  r=run_python_implementation(**implementation_args(src,runtime,grant,pres,git,patches=[{'type':'replace_text','old':'def add','new':'def _add','expected_occurrences':1}]));req(not r['ok'] and r['python_implementation']['failure_stage']=='undeclared_public_api_change' and r['python_implementation']['workspace_cleaned'],'undeclared_public_api_change_blocked')
  req(content_manifest(src)==before,'failed_api_change_source_immutable')
 with tempfile.TemporaryDirectory() as td:
  src,runtime,grant,pres,git=source_fixture(Path(td));r=run_python_implementation(**implementation_args(src,runtime,grant,pres,git,patches=[{'type':'replace_text','old':'def add(a: int, b: int) -> int:','new':'def add(a: int, b: int, c: int = 0) -> int:','expected_occurrences':1}]));req(not r['ok'] and r['python_implementation']['failure_stage']=='undeclared_public_api_change' and r['python_implementation']['compatibility_summary']['public_signature_change_count']==1,'public_signature_change_requires_declaration')
 with tempfile.TemporaryDirectory() as td:
  src,runtime,grant,pres,git=source_fixture(Path(td));r=run_python_implementation(**implementation_args(src,runtime,grant,pres,git,patches=[{'type':'replace_text','old':'async def scale','new':'def scale','expected_occurrences':1}]));req(not r['ok'] and r['python_implementation']['failure_stage']=='undeclared_public_api_change','sync_async_contract_change_blocked')
 with tempfile.TemporaryDirectory() as td:
  src,runtime,grant,pres,git=source_fixture(Path(td));patch=[{'type':'replace_text','old':'from __future__ import annotations','new':'from __future__ import annotations\nfrom pathlib import Path','expected_occurrences':1},{'type':'replace_text','old':'    return a + b','new':'    Path("state.txt").write_text("x")\n    return a + b','expected_occurrences':1}];r=run_python_implementation(**implementation_args(src,runtime,grant,pres,git,patches=patch));req(not r['ok'] and r['python_implementation']['failure_stage']=='undeclared_persistence_side_effect','persistence_side_effect_requires_declaration')
 with tempfile.TemporaryDirectory() as td:
  src,runtime,grant,pres,git=source_fixture(Path(td));r=run_python_implementation(**implementation_args(src,runtime,grant,pres,git,relative_path='app/__init__.py',patches=[{'type':'replace_text','old':'__all__ = ["add", "scale"]','new':'__all__ = ["add", "scale"]\nPACKAGE_REVISION = 1','expected_occurrences':1}]));req(not r['ok'] and r['python_implementation']['failure_stage']=='undeclared_package_boundary_change','package_boundary_change_requires_declaration')
 with tempfile.TemporaryDirectory() as td:
  src,runtime,grant,pres,git=source_fixture(Path(td));r=run_python_implementation(**implementation_args(src,runtime,grant,pres,git,patches=[{'type':'replace_text','old':'    return a + b','new':'    return (','expected_occurrences':1}]));req(not r['ok'] and r['python_implementation']['failure_stage']=='python_syntax_invalid','syntax_failure_stops_before_tests')
 with tempfile.TemporaryDirectory() as td:
  src,runtime,grant,pres,git=source_fixture(Path(td));r=run_python_implementation(**implementation_args(src,runtime,grant,pres,git,test_argv=[sys.executable,'-c','raise SystemExit(7)']));row=r['python_implementation'];req(not r['ok'] and row['failure_stage']=='python_tests_failed' and row['compile_passed'] and not row['tests_passed'] and row['workspace_cleaned'],'test_failure_cleans_candidate')
 req(PYTHON_DENIED_AUTHORITY['dependency_installation_authorized'] is False and PYTHON_DENIED_AUTHORITY['release_authorized'] is False,'python_skill_does_not_expand_authority')
 print({'ok':True,'suite':'v1341.6-8-python-implementation-reliability','passed':p[0],'total':9})
if __name__=='__main__': main()
