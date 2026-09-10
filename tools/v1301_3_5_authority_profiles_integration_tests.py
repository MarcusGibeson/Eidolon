from __future__ import annotations
import sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.dont_write_bytecode=True
checks=[]
def req(v,n):checks.append(n);assert v,n
from authority_profiles import *
for name in PROFILE_NAMES:
 p=create_authority_profile(name=name,workspace_digest='b'*64);req(validate_authority_profile(p)['ok'],name)
req(not profile_allows(create_authority_profile(name='observe',workspace_digest='b'*64),'file_write'),'observe_no_write');req(profile_allows(create_authority_profile(name='propose',workspace_digest='b'*64),'propose'),'propose_read')
print(json.dumps({'suite':'v1301.3-5-authority-profiles','ok':True,'passed':len(checks),'failed':0,'checks':checks},sort_keys=True))
