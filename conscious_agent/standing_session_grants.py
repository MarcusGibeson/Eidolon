from __future__ import annotations
"""v1302 time-bounded standing-session grants sealed to the full reviewed profile."""
import time,secrets
from typing import Any,Mapping
from authority_profiles import validate_authority_profile,profile_allows,PROTECTED_ACTIONS
from cognitive_coding_foundations import DENIED_AUTHORITY,digest
CONTRACT_VERSION='v1302.8'
def prepare_standing_session(profile:Mapping[str,Any],*,now_unix:int|None=None,duration_minutes:int|None=None)->dict[str,Any]:
 if not validate_authority_profile(profile).get('ok'):raise ValueError('valid_profile_required')
 now=int(time.time() if now_unix is None else now_unix);duration=max(1,min(int(duration_minutes or (profile.get('limits') or {}).get('max_minutes') or 60),int((profile.get('limits') or {}).get('max_minutes') or 60)));nonce=secrets.token_hex(8);gid='ssg_'+digest({'profile':profile['profile_digest'],'now':now,'nonce':nonce})[:24];phrase=f'AUTHORIZE STANDING SESSION {gid} {nonce}';row={'contract_version':CONTRACT_VERSION,'grant_id':gid,'profile_snapshot':dict(profile),'profile_digest':profile['profile_digest'],'workspace_digest':profile['workspace_digest'],'prepared_unix':now,'expires_unix':now+duration*60,'authorization_phrase_digest':digest(phrase),'activation_consumed':False,'state':'prepared','pause_count':0,'revoked':False,'standing_session_active':False,**DENIED_AUTHORITY};row['grant_digest']=digest(row);return {'grant':row,'exact_authorization_phrase':phrase}
def activate_standing_session(grant:Mapping[str,Any],phrase:str,*,now_unix:int|None=None)->dict[str,Any]:
 now=int(time.time() if now_unix is None else now_unix);g=dict(grant);valid=g.get('state')=='prepared' and not g.get('activation_consumed') and now<=int(g.get('expires_unix') or 0) and digest(str(phrase or ''))==g.get('authorization_phrase_digest') and validate_authority_profile(g.get('profile_snapshot') or {}).get('ok') and (g.get('profile_snapshot') or {}).get('profile_digest')==g.get('profile_digest')
 if not valid:return {'ok':False,'status':'exact_standing_session_authorization_required','grant':g,'standing_session_active':False,**DENIED_AUTHORITY}
 g['activation_consumed']=True;g['state']='active';g['standing_session_active']=True;g['grant_digest']=digest({k:v for k,v in g.items() if k!='grant_digest'});return {'ok':True,'status':'standing_session_active','grant':g,'standing_session_active':True,**{k:v for k,v in DENIED_AUTHORITY.items() if k!='standing_authority_granted'},'standing_authority_granted':True}
def transition_standing_session(grant:Mapping[str,Any],action:str,*,now_unix:int|None=None)->dict[str,Any]:
 now=int(time.time() if now_unix is None else now_unix);g=dict(grant);a=str(action);state=str(g.get('state'))
 if now>int(g.get('expires_unix') or 0):g['state']='expired';g['standing_session_active']=False
 elif a=='pause' and state=='active':g['state']='paused';g['standing_session_active']=False;g['pause_count']=int(g.get('pause_count') or 0)+1
 elif a=='resume' and state=='paused':g['state']='active';g['standing_session_active']=True
 elif a=='revoke' and state in {'active','paused','prepared'}:g['state']='revoked';g['revoked']=True;g['standing_session_active']=False
 else:return {'ok':False,'status':'standing_session_transition_blocked','grant':g,**DENIED_AUTHORITY}
 g['grant_digest']=digest({k:v for k,v in g.items() if k!='grant_digest'});return {'ok':True,'status':f"standing_session_{g['state']}",'grant':g,'standing_session_active':g['standing_session_active'],**DENIED_AUTHORITY}
def standing_session_allows(grant:Mapping[str,Any],action_class:str,*,now_unix:int|None=None)->bool:
 now=int(time.time() if now_unix is None else now_unix);return bool(grant.get('state')=='active' and grant.get('standing_session_active') and not grant.get('revoked') and now<=int(grant.get('expires_unix') or 0) and action_class not in PROTECTED_ACTIONS and profile_allows(grant.get('profile_snapshot') or {},action_class))
__all__=['CONTRACT_VERSION','prepare_standing_session','activate_standing_session','transition_standing_session','standing_session_allows']
