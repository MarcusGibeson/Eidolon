from __future__ import annotations
import sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.dont_write_bytecode=True
checks=[]
def req(v,n):checks.append(n);assert v,n
from authority_profiles import *
p=create_authority_profile(name='bounded_autonomous',workspace_digest='d'*64);req(CONTRACT_VERSION=='v1301.8','contract');req(validate_authority_profile(p)['ok'],'profile');req(not p['standing_authority_granted'],'no_standing');req(not p['release_authorized'],'no_release');req(not profile_allows(p,'workspace_expand'),'workspace_bound')
print(json.dumps({'suite':'v1301.9-authority-profiles-checkpoint','ok':True,'passed':len(checks),'failed':0,'checks':checks},sort_keys=True))
