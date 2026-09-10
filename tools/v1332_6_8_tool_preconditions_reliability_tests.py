import sys,tempfile,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.path.insert(0,str(ROOT/'tools'))
from v1332_tool_preconditions_test_support import fixture
from tool_preconditions import load_tool_preconditions
passed=0
def req(x,n):
 global passed
 assert x,n;passed+=1
with tempfile.TemporaryDirectory() as td:
 req('availability_evidenced' in fixture(td,available=False)['tool_preconditions']['blocked_preconditions'],'unavailable_blocks')
 req('boundary_clean' in fixture(td,clean=False)['tool_preconditions']['blocked_preconditions'],'dirty_boundary_blocks')
 req('dependencies_satisfied' in fixture(td,dep='missing')['tool_preconditions']['blocked_preconditions'],'missing_dependency_blocks')
 req('permissions_satisfied' in fixture(td,permission='unknown')['tool_preconditions']['blocked_preconditions'],'unknown_permission_blocks')
 req('expected_artifacts_declared' in fixture(td,artifact=False)['tool_preconditions']['blocked_preconditions'],'missing_artifact_contract_blocks')
print({'ok':True,'suite':'v1332.6-8-tool-preconditions-reliability','passed':passed,'total':5})
