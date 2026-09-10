import sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'conscious_agent'))
from tool_capability_registry import build_tool_capability_registry
from tool_preconditions import evaluate_tool_preconditions,load_tool_preconditions

def fixture(root, tool='file_patch', *, available=True, mode='candidate_workspace', permission='permitted', clean=True, dep='present', artifact=True):
    reg=build_tool_capability_registry(availability_evidence={tool:{'available':available,'evidence_digests':['ev-tool']}},runtime_root=root)['tool_capability_registry']
    return evaluate_tool_preconditions(registry=reg,tool_code=tool,workspace_evidence={'workspace_digest':'w1','cwd_digest':'c1','cwd_within_workspace':True,'boundary_clean':clean,'workspace_mode':mode,'evidence_digests':['ev-work']},dependency_requirements=['python'],dependency_evidence={'python':{'state':dep,'evidence_digests':['ev-dep']}},permission_evidence={'state':permission,'evidence_digests':['ev-perm']},expected_artifacts=([{'artifact_code':'result','contract_digest':'artifact-digest'}] if artifact else []),runtime_root=root)
