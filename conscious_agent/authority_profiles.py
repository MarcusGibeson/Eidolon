from __future__ import annotations
"""v1301 authority-profile contracts. Profiles are ceilings, never grants by themselves."""
from typing import Any,Mapping
from cognitive_coding_foundations import DENIED_AUTHORITY,digest
CONTRACT_VERSION='v1301.8'
PROFILE_NAMES=('observe','propose','supervised_execute','bounded_autonomous')
PROTECTED_ACTIONS=frozenset({'external_publish','destructive_system','secret_access','model_install','model_delete','account_change','financial_action','workspace_expand','release_promote'})
PRESETS={
 'observe':{'read':True,'write':False,'commands':False,'network':False,'commit':False},
 'propose':{'read':True,'write':False,'commands':False,'network':False,'commit':False},
 'supervised_execute':{'read':True,'write':True,'commands':True,'network':False,'commit':False},
 'bounded_autonomous':{'read':True,'write':True,'commands':True,'network':False,'commit':True},
}
def create_authority_profile(*,name:str,workspace_digest:str,command_classes=(),network_endpoints=(),max_minutes:int=60,max_commands:int=100,max_files_changed:int=32,max_disk_mb:int=512)->dict[str,Any]:
 n=str(name or '').strip().lower();
 if n not in PROFILE_NAMES:raise ValueError('authority_profile_name_invalid')
 ws=str(workspace_digest or '').lower();
 if len(ws)!=64:raise ValueError('workspace_digest_required')
 row={'contract_version':CONTRACT_VERSION,'name':n,'workspace_digest':ws,'capabilities':dict(PRESETS[n]),'command_classes':sorted({str(x) for x in command_classes})[:32],'network_endpoints':sorted({str(x) for x in network_endpoints})[:32],'limits':{'max_minutes':max(1,min(24*60,int(max_minutes))),'max_commands':max(0,min(10000,int(max_commands))),'max_files_changed':max(0,min(10000,int(max_files_changed))),'max_disk_mb':max(1,min(1024*1024,int(max_disk_mb)))},'protected_actions':sorted(PROTECTED_ACTIONS),'profile_is_authority_grant':False,'standing_session_active':False,**DENIED_AUTHORITY};row['profile_digest']=digest(row);return row
def validate_authority_profile(row:Mapping[str,Any])->dict[str,Any]:
 body=dict(row);sup=body.pop('profile_digest','');n=str(row.get('name') or '');checks={'digest':sup==digest(body),'name':n in PROFILE_NAMES,'workspace':len(str(row.get('workspace_digest') or ''))==64,'ceiling_only':row.get('profile_is_authority_grant') is False and row.get('standing_session_active') is False,'protected':PROTECTED_ACTIONS.issubset(set(row.get('protected_actions') or [])),'authority':not any(bool(row.get(k)) for k in DENIED_AUTHORITY)};return {'ok':all(checks.values()),'checks':checks}
def profile_allows(profile:Mapping[str,Any],action_class:str)->bool:
 if not validate_authority_profile(profile).get('ok') or action_class in PROTECTED_ACTIONS:return False
 caps=profile.get('capabilities') or {};mapping={'read':'read','propose':'read','file_write':'write','command':'commands','test':'commands','git_commit':'commit','network':'network'};key=mapping.get(str(action_class));return bool(key and caps.get(key))
__all__=['CONTRACT_VERSION','PROFILE_NAMES','PROTECTED_ACTIONS','create_authority_profile','validate_authority_profile','profile_allows']
