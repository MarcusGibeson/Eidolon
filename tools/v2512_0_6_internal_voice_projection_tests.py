from __future__ import annotations
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for p in (ROOT,ROOT/'conscious_agent'):
    if str(p) not in sys.path:sys.path.insert(0,str(p))
sys.dont_write_bytecode=True
from conscious_agent.live_cognitive_activity_v2510 import project_live_activity
from conscious_agent.internal_voice_projection_v2512 import project_activity_internal_voice,project_cognitive_internal_voice
checks=[]
def req(v,n):checks.append(n);assert v,n
for source in [
 {'event':'accepted','message':'private request'},
 {'event':'meta','prompt':'private prompt'},
 {'event':'status','stage':'governed_action','message':'raw state'},
 {'event':'conversation_complete','result':{'success':True,'response':'private output'}},
 {'event':'saved','turn':{'user_message':'private'}},
]:
 a=project_live_activity(source,operation_id='op')
 v=project_activity_internal_voice(a)
 req(v is not None,'activity_voice')
 req(v['representation_kind']=='state_grounded_internal_voice_projection','representation_labeled')
 req(not v['provider_contacted'],'provider_free')
 req(not v['hidden_reasoning_exposed'] and not v['claims_literal_thought_transcript'],'not_chain_of_thought')
 req('private' not in str(v).lower() and 'raw state' not in str(v).lower(),'private_input_absent')
for op in ['REFLECT','CONTINUE_THOUGHT','RECONSIDER_BELIEF','REVIEW_GOAL','PLAN','REPLAN','INTEGRATE_EXPERIENCE','REVIEW_SELF_MODEL','RESOLVE_CONFLICT','REST']:
 v=project_cognitive_internal_voice({'selected_operation':op,'frame_digest':'a'*64,'subject_ref':'secret subject'})
 req(v is not None,f'cognitive_voice_{op}')
 req('secret subject' not in str(v),f'no_subject_leak_{op}')
req(project_activity_internal_voice({'event':'delta','text':'secret'}) is None,'delta_rejected')
req(project_cognitive_internal_voice({'selected_operation':'UNKNOWN'}) is None,'unknown_operation_silent')
print({'ok':True,'passed':len(checks),'total':len(checks),'checks':checks})
