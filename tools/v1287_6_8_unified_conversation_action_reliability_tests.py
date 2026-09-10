from __future__ import annotations
import json,os,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.dont_write_bytecode=True;os.environ['PYTHONDONTWRITEBYTECODE']='1';sys.path[:0]=[str(ROOT/'conscious_agent'),str(ROOT)]
from unified_conversation_action_reliability import inspect_unified_conversation_action_sequence,inspect_unified_conversation_action_health
C=[]
def req(v,l):
 if not v: raise AssertionError(l)
 C.append(l)
turns=[
 {'user_text':'Hi, how are you?'},
 {'user_text':'How does this work?'},
 {'user_text':'Build me a calculator webpage.','action_projection':{'status':'proposal_only'}},
 {'user_text':"What's the status?",'operator_snapshot':{'current':{'session_state':'paused','campaign_phase':'implementation'},'progress':{'event_count_total':4,'failure_count_total':0},'verification':{}}},
 {'user_text':'Actually, make it dark mode instead.'},
 {'user_text':'Cancel that development proposal.'},
 {'user_text':'Go ahead.'},
 {'user_text':'Thanks.'},
]
r=inspect_unified_conversation_action_sequence(turns)
req(r['ok'],'sequence_ok')
req(r['turn_count']==len(turns),'turn_count')
req(r['mode_transition_count']>=5,'mode_transitions')
req(r['no_hidden_execution'],'no_hidden_execution')
req(r['no_authority_expansion'],'no_authority_expansion')
req(r['no_parallel_system'],'no_parallel')
req(r['foreground_conversation_preserved'],'foreground_preserved')
req('progress_request' in r['turn_modes'] and 'development_request' in r['turn_modes'],'work_and_progress')
health=inspect_unified_conversation_action_health(source_root=ROOT)
req(health['ok'],'health')
req(all(health['checks'].values()),'health_checks')
req(health['native_windows_validation']=='desktop_review_required','windows_handoff')
req(health['provider_contacted'] is False and health['commands_executed'] is False and health['project_modified'] is False,'health_nonexecuting')
print(json.dumps({'ok':True,'suite':'v1287.6-v1287.8-unified-conversation-action-reliability','passed':len(C),'failed':0},sort_keys=True))
