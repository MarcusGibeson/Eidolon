from __future__ import annotations
import hashlib,json,os,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.dont_write_bytecode=True;os.environ['PYTHONDONTWRITEBYTECODE']='1'
sys.path[:0]=[str(ROOT/'conscious_agent'),str(ROOT)]
from unified_conversation_action_foundations import TURN_MODES,classify_unified_conversation_action_turn
from conversational_command_integration_foundations import DENIED_AUTHORITY
C=[]
def req(v,l):
 if not v: raise AssertionError(l)
 C.append(l)
def sig():
 rows=[]
 for p in sorted(ROOT.rglob('*')):
  if p.is_file():
   rel=p.relative_to(ROOT).as_posix()
   if '__pycache__' in rel or rel.endswith(('.pyc','.pyo')) or rel.startswith('data/'): continue
   rows.append((rel,hashlib.sha256(p.read_bytes()).hexdigest()))
 return hashlib.sha256(json.dumps(rows,separators=(',',':')).encode()).hexdigest()
before=sig()
fixtures=[
 ('Hi, how are you?','companionship','ordinary_conversation_generation'),
 ('I was thinking about how software tools shape habits.','discussion','ordinary_conversation_generation'),
 ('How does the development campaign work?','question','ordinary_conversation_generation'),
 ('Help me plan how to build a calculator app.','planning','ordinary_conversation_generation'),
 ('Build me a calculator webpage.','development_request','existing_ordinary_chat_action_and_development_pipeline'),
 ("What's the status?",'progress_request','existing_operator_and_action_progress_projection'),
 ('Actually, make it dark mode instead.','correction','existing_conversational_command_integration'),
 ('Cancel that development proposal.','cancellation','existing_conversational_command_integration'),
 ('Go ahead.','authorization_control','exact_authorization_required'),
 ('Approve development proposal devc_0123456789abcdef01234567 revision 2.','authorization_control','existing_exact_authorization_owner'),
 ('Build me a webpage. Delete my Python utility.','ambiguous_action','clarification_only'),
]
for text,mode,owner in fixtures:
 r=classify_unified_conversation_action_turn(text)
 req(r['turn_mode']==mode,f'mode:{mode}')
 req(r['route_owner']==owner,f'owner:{mode}')
 req(r['turn_mode_supported'] is True,f'supported:{mode}')
 req(r['foreground_conversation_preserved'] is True,f'foreground:{mode}')
 req(r['parallel_execution_engine_created'] is False,f'parallel:{mode}')
 req(r['provider_contacted'] is False and r['commands_executed'] is False and r['project_modified'] is False,f'nonexecuting:{mode}')
 req(bool(r['turn_digest']) and len(r['turn_digest'])==64,f'digest:{mode}')
for text in ('What remains?','How far did you get?','Did that finish?','Why did that fail?'):
 req(classify_unified_conversation_action_turn(text)['turn_mode']=='progress_request',f'progress:{text}')
q=classify_unified_conversation_action_turn('Could you explain how to build a calculator webpage?')
req(q['turn_mode']=='question' and q['question_creates_work'] is False,'question_not_action')
p=classify_unified_conversation_action_turn('What should we do next?')
req(p['turn_mode'] in {'question','planning'},'question_or_planning_safe')
g=classify_unified_conversation_action_turn('Yes, do it.')
req(g['turn_mode']=='authorization_control' and g['generic_authorization_shape'] is True and g['exact_control_shape'] is False,'generic_auth_not_exact')
e=classify_unified_conversation_action_turn('Approve development proposal devc_0123456789abcdef01234567 revision 2.')
req(e['exact_control_shape'] is True,'exact_shape_preserved')
a=classify_unified_conversation_action_turn('Build me a webpage. Delete my Python utility.')
req(a['requires_clarification'] is True,'ambiguity_fails_closed')
req(set(TURN_MODES)=={'companionship','discussion','question','planning','development_request','progress_request','correction','cancellation','authorization_control','ambiguous_action'},'mode_contract')
for key,expected in DENIED_AUTHORITY.items(): req(g[key] is expected,f'denied:{key}')
req(sig()==before,'source_immutable')
print(json.dumps({'ok':True,'suite':'v1287.0-v1287.2-unified-conversation-action-foundations','passed':len(C),'failed':0},sort_keys=True))
