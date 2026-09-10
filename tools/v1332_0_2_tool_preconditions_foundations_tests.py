import sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.path.insert(0,str(ROOT/'tools'))
from v1332_tool_preconditions_test_support import fixture
from tool_preconditions import PRECONDITION_CODES
passed=0
def req(x,n):
 global passed
 assert x,n;passed+=1
with tempfile.TemporaryDirectory() as td:
 r=fixture(td)
 req(r['ok'] and r['status'].endswith('unauthorized'),'complete_evidence_satisfies_only_preconditions')
 p=r['tool_preconditions'];req(tuple(p['checks'])==PRECONDITION_CODES,'exact_check_contract')
 req(p['tool_invoked'] is False and p['action_executed'] is False,'no_invocation')
 req(p['tool_execution_authorized'] is False and p['project_mutation_authorized'] is False,'no_authority')
 req(not p['blocked_preconditions'],'no_blocks')
print({'ok':True,'suite':'v1332.0-2-tool-preconditions-foundations','passed':passed,'total':5})
