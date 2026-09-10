from __future__ import annotations
import sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.dont_write_bytecode=True
checks=[]
def req(v,n):checks.append(n);assert v,n
from authority_profiles import *
p=create_authority_profile(name='bounded_autonomous',workspace_digest='c'*64,max_minutes=99999,max_commands=-1);req(p['limits']['max_minutes']==1440,'time_cap');req(p['limits']['max_commands']==0,'command_floor');bad=dict(p);bad['workspace_digest']='d'*64;req(not validate_authority_profile(bad)['ok'],'tamper');req(all(not profile_allows(p,x) for x in PROTECTED_ACTIONS),'protected_all')
print(json.dumps({'suite':'v1301.6-8-authority-profiles','ok':True,'passed':len(checks),'failed':0,'checks':checks},sort_keys=True))
