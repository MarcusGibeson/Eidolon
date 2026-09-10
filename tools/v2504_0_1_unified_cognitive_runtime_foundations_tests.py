from __future__ import annotations
import json,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for p in (ROOT,):
    if str(p) not in sys.path:sys.path.insert(0,str(p))
sys.dont_write_bytecode=True
from conscious_agent.unified_cognitive_state_frame import build_unified_cognitive_state_frame
from conscious_agent.cognitive_operation_registry import build_cognitive_operation_registry,get_cognitive_operation,verify_cognitive_operation_registry
checks=[]
def req(v,n): checks.append(n); assert v,n
with tempfile.TemporaryDirectory(prefix='eidolon-v2504-0-1-') as td:
    root=Path(td)
    frame=build_unified_cognitive_state_frame(root,trigger_type='manual_review',trigger_ref='private user text not retained')
    req(frame['ok'],'frame_ok');req(frame['contract_version']=='v2504.0','frame_contract')
    req(frame['read_only'],'frame_read_only');req(not frame['provider_contacted'],'frame_no_provider')
    req(not frame['external_action_executed'],'frame_no_action');req(not frame['source_mutated'],'frame_no_source_mutation')
    req('private user text' not in json.dumps(frame),'trigger_digest_only')
    req(set(frame['projection'])=={'trigger','homeostasis','demands','beliefs','planning','continuity','initiative'},'stable_projection_domains')
    req(frame['frame_id'].startswith('cognitive-frame-') and len(frame['frame_digest'])==64,'frame_digest')
    registry=build_cognitive_operation_registry();req(verify_cognitive_operation_registry(registry),'registry_valid')
    req(registry['operation_count']>=10,'registry_broad_enough');req(registry['default_operation']=='REST','rest_default')
    req(get_cognitive_operation('reflect')['operation']=='REFLECT','lookup_normalized')
    req(not registry['authority_boundary']['operation_can_execute_action'],'registry_no_execution')
print(json.dumps({'ok':True,'contract':'v2504.0-v2504.1','passed':len(checks),'checks':checks},sort_keys=True))
