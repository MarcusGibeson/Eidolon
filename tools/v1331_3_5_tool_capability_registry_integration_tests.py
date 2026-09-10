from __future__ import annotations
import json,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.dont_write_bytecode=True
from tool_capability_registry import *
from ordinary_chat_development_campaign import process_ordinary_chat_development_turn
checks=[]
def req(v,n):checks.append(n);assert v,n
with tempfile.TemporaryDirectory() as td:
 r=build_tool_capability_registry(availability_evidence={'git':{'available':True,'evidence_digests':['e']}},runtime_root=td)['tool_capability_registry'];git=next(x for x in r['capabilities'] if x['tool_code']=='git');req(git['availability_state']=='evidence_available' and git['availability_evidence_count']==1,'evidence_state');req(not git['tool_invoked'],'evidence_not_probe')
 i=inspect_tool_capability(r,'file_patch');req(i['ok'] and i['tool_capability']['authority_class']=='workspace_mutation','inspect')
 chat=process_ordinary_chat_development_turn('show tool capability registry',project_state={},runtime_root=td);req(chat.get('active') and chat['tool_capability_registry']['capability_count']==9,'ordinary_route')
print(json.dumps({'suite':'v1331.3-5-tool-capability-registry','ok':True,'passed':len(checks),'checks':checks},sort_keys=True))
