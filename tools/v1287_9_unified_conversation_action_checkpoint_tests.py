from __future__ import annotations
import json,os,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.dont_write_bytecode=True;os.environ['PYTHONDONTWRITEBYTECODE']='1';sys.path[:0]=[str(ROOT/'conscious_agent'),str(ROOT)]
from unified_conversation_action_checkpoint import build_unified_conversation_action_checkpoint
C=[]
def req(v,l):
 if not v: raise AssertionError(l)
 C.append(l)
r=build_unified_conversation_action_checkpoint(source_root=ROOT)
req(r['ok'],'checkpoint')
req(r['checkpoint_version']=='1287.9','version')
req(all(r['checks'].values()),'checks')
d=r['details']
req(d['next_bounded_unit']=='v1288 Provider-Aware Performance','next')
req(d['v1288_started'] is False,'unstarted')
req(d['companionship_discussion_questions_actions_progress_corrections_cancellation_supported'],'modes')
req(d['ordinary_chat_and_supervised_development_reused'],'reuse')
req(d['generic_authorization_never_exact'] and d['progress_reporting_read_only'],'authority_progress')
req(d['parallel_conversation_system_created'] is False and d['parallel_execution_engine_created'] is False,'no_parallel')
req(not d['provider_contacted'] and not d['commands_executed'] and not d['project_modified'],'readonly')
print(json.dumps({'ok':True,'suite':'v1287.9-unified-conversation-action-checkpoint','passed':len(C),'failed':0},sort_keys=True))
