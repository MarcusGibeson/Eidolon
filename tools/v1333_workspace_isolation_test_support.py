from __future__ import annotations
import hashlib, shutil, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'conscious_agent'))
from authority_profiles import create_authority_profile
from standing_session_grants import prepare_standing_session, activate_standing_session
from tool_capability_registry import build_tool_capability_registry
from tool_preconditions import evaluate_tool_preconditions

WS='b'*64

def make_source(base:Path)->Path:
    src=base/'source';src.mkdir();(src/'app.py').write_text('print("hello")\n',encoding='utf-8');(src/'README.md').write_text('# fixture\n',encoding='utf-8');return src

def active_grant(*,ws=WS,commands=('git_worktree',),now=100):
    profile=create_authority_profile(name='bounded_autonomous',workspace_digest=ws,command_classes=commands,max_minutes=30,max_disk_mb=64)
    prepared=prepare_standing_session(profile,now_unix=now,duration_minutes=20)
    return activate_standing_session(prepared['grant'],prepared['exact_authorization_phrase'],now_unix=now)['grant']

def precondition(runtime:Path, tool='file_patch', *, available=True):
    reg=build_tool_capability_registry(availability_evidence={tool:{'available':available,'evidence_digests':['tool-evidence']}},runtime_root=runtime)['tool_capability_registry']
    result=evaluate_tool_preconditions(registry=reg,tool_code=tool,workspace_evidence={'workspace_digest':'owned-runtime','cwd_digest':'cwd','cwd_within_workspace':True,'boundary_clean':True,'workspace_mode':'owned_workspace','evidence_digests':['workspace-evidence']},permission_evidence={'state':'permitted','evidence_digests':['permission-evidence']},expected_artifacts=[{'artifact_code':'candidate_workspace','contract_digest':'artifact-contract'}],runtime_root=runtime)
    return result['tool_preconditions']['precondition_record_id']

def init_git(source:Path)->str|None:
    git=shutil.which('git')
    if not git:return None
    subprocess.run([git,'init'],cwd=source,check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    subprocess.run([git,'config','user.email','fixture@example.invalid'],cwd=source,check=True)
    subprocess.run([git,'config','user.name','Fixture'],cwd=source,check=True)
    subprocess.run([git,'add','app.py','README.md'],cwd=source,check=True)
    subprocess.run([git,'commit','-m','fixture'],cwd=source,check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    return git
