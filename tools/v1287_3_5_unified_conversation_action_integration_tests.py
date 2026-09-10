from __future__ import annotations
import json,os,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.dont_write_bytecode=True;os.environ['PYTHONDONTWRITEBYTECODE']='1';sys.path[:0]=[str(ROOT/'conscious_agent'),str(ROOT)]
from conversational_command_integration import build_conversational_command_integration
from unified_conversation_action import build_unified_conversation_action_projection,unified_conversation_action_prompt,public_unified_conversation_action_projection
C=[]
def req(v,l):
 if not v: raise AssertionError(l)
 C.append(l)
with tempfile.TemporaryDirectory(prefix='eidolon-v1287-') as td:
 runtime=Path(td)
 info=build_conversational_command_integration("What's the status?",runtime_root=runtime)
 operator={'current':{'session_state':'running','campaign_phase':'verification'},'progress':{'event_count_total':7,'failure_count_total':1,'retry_count_total':1,'recent_events':[{'event_code':'verify_started'}]},'verification':{'tests_executed':True,'passed':False}}
 p=build_unified_conversation_action_projection("What's the status?",conversational_command_integration=info,action_projection={'status':'waiting'},development_lifecycle={'status':'campaign_active'},operator_snapshot=operator)
 req(p['turn_mode']=='progress_request','progress_mode')
 req(p['status']=='progress_projection_ready','progress_ready')
 req(p['progress']['session_state']=='running' and p['progress']['campaign_phase']=='verification','operator_progress')
 req(p['progress']['failure_count']==1 and p['progress']['unknown_is_not_failure'] is True,'failure_truth')
 req(p['technical_execution']['state']=='not_inferred_from_user_language','execution_not_inferred')
 req(p['technical_execution']['observation_is_not_authorization'] is True,'observation_not_authority')
 prompt=unified_conversation_action_prompt(p)
 req('mode=progress_request' in prompt and 'Generic approval is never an exact authorization' in prompt,'prompt_contract')
 generic=build_unified_conversation_action_projection('Go ahead.',conversational_command_integration=build_conversational_command_integration('Go ahead.',runtime_root=runtime))
 req(generic['turn_mode']=='authorization_control','generic_auth_mode')
 req(generic['status']=='generic_authorization_blocked','generic_auth_blocked')
 req(generic['generic_authorization_is_exact_authorization'] is False,'generic_not_exact')
 exact_text='Approve development proposal devc_0123456789abcdef01234567 revision 2.'
 exact=build_unified_conversation_action_projection(exact_text,conversational_command_integration=build_conversational_command_integration(exact_text,runtime_root=runtime))
 req(exact['turn_mode']=='authorization_control' and exact['status']=='exact_authorization_passthrough','exact_passthrough')
 action=build_unified_conversation_action_projection('Build me a calculator webpage.',conversational_command_integration=build_conversational_command_integration('Build me a calculator webpage.',runtime_root=runtime),action_projection={'status':'proposal_only'},development_lifecycle={'event':'proposal_created','execution_invoked':False,'provider_contacted':False,'source_modified':False},developer_campaign_projection={'campaign_connected_to_conversation':True})
 req(action['turn_mode']=='development_request','development_mode')
 req(action['route_owner']=='existing_ordinary_chat_action_and_development_pipeline','existing_pipeline')
 req(action['parallel_conversation_system_created'] is False and action['parallel_execution_engine_created'] is False,'no_parallel_system')
 public=public_unified_conversation_action_projection(action)
 req(public['raw_turn_text_exposed'] is False and public['raw_operator_content_exposed'] is False,'public_minimized')
 req(action['provider_contacted'] is False and action['commands_executed'] is False and action['project_modified'] is False,'projection_nonexecuting')
print(json.dumps({'ok':True,'suite':'v1287.3-v1287.5-unified-conversation-action-integration','passed':len(C),'failed':0},sort_keys=True))
