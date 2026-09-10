from __future__ import annotations
import sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.path.insert(0,str(ROOT/'tools'))
from v1333_workspace_isolation_test_support import *
from workspace_isolation import *
passed=0
def req(x,n):
 global passed
 assert x,n;passed+=1
p=plan_workspace_isolation(source_workspace_digest=WS,mode='filesystem_copy');req(p['ok'] and not p['active_grant_currently_satisfies_operation'],'plan_without_grant')
req(p['required_tool_code']=='file_patch' and p['workspace_created'] is False,'copy_contract')
q=plan_workspace_isolation(source_workspace_digest=WS,mode='git_branch_worktree');req(q['required_tool_code']=='git','git_contract')
req(not plan_workspace_isolation(source_workspace_digest=WS,mode='telepathy')['ok'],'invalid_mode_blocked')
req(p['project_mutation_authorized'] is False and p['tool_execution_authorized'] is False,'plan_no_authority')
print({'ok':True,'suite':'v1333.0-2-workspace-isolation-foundations','passed':passed,'total':5})
