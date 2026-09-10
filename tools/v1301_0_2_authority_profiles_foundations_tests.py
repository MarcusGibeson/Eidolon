from __future__ import annotations
import sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.dont_write_bytecode=True
checks=[]
def req(v,n):checks.append(n);assert v,n
from authority_profiles import *
p=create_authority_profile(name='bounded_autonomous',workspace_digest='a'*64,command_classes=['python']);req(validate_authority_profile(p)['ok'],'valid');req(PROFILE_NAMES==('observe','propose','supervised_execute','bounded_autonomous'),'names');req(profile_allows(p,'file_write'),'write');req(profile_allows(p,'command'),'command');req(not profile_allows(p,'external_publish'),'protected');req(not p['profile_is_authority_grant'] and not p['standing_session_active'],'ceiling')
print(json.dumps({'suite':'v1301.0-2-authority-profiles','ok':True,'passed':len(checks),'failed':0,'checks':checks},sort_keys=True))
