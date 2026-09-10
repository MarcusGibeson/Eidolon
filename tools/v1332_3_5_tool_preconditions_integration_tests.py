import sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.path.insert(0,str(ROOT/'tools'))
from v1332_tool_preconditions_test_support import fixture
from ordinary_chat_development_campaign import process_ordinary_chat_development_turn
from tool_capability_registry import build_tool_capability_registry
passed=0
def req(x,n):
 global passed
 assert x,n;passed+=1
with tempfile.TemporaryDirectory() as td:
 reg=build_tool_capability_registry(availability_evidence={'file_patch':{'available':True,'evidence_digests':['ev-tool']}},runtime_root=td)['tool_capability_registry']
 ps={'tool_capability_registry':reg,'tool_code':'file_patch','workspace_evidence':{'workspace_digest':'w','cwd_digest':'c','cwd_within_workspace':True,'boundary_clean':True,'workspace_mode':'candidate_workspace','evidence_digests':['we']},'dependency_requirements':['python'],'dependency_evidence':{'python':{'state':'present','evidence_digests':['de']}},'tool_permission_evidence':{'state':'permitted','evidence_digests':['pe']},'expected_artifacts':[{'artifact_code':'result','contract_digest':'ad'}]}
 r=process_ordinary_chat_development_turn('show tool preconditions',project_state=ps,runtime_root=td)
 req(r.get('active') is True and r.get('ok') is True,'ordinary_chat_route')
 req(r['tool_preconditions']['preconditions_satisfied'] is True,'ordinary_result')
 req(r['tool_execution_authorized'] is False,'chat_does_not_authorize')
 req(process_ordinary_chat_development_turn('hello there',project_state=ps,runtime_root=td).get('active') is not True,'unrelated_chat_not_claimed')
print({'ok':True,'suite':'v1332.3-5-tool-preconditions-integration','passed':passed,'total':4})
